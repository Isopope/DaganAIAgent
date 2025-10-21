"""
Tool pour recherche vectorielle avec cosine similarity + reranking LLM
Remplace le node retrieve + grade avec embeddings similarity directe
"""

import os
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List
from langchain.tools import tool
from openai import OpenAI
from tools.reranker import rerank_documents

# Configuration
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DOCUMENTS_COLLECTION = os.getenv("DOCUMENTS_COLLECTION", "crawled_documents")
CRAG_TOP_K = int(os.getenv("CRAG_TOP_K", "20"))
SIMILARITY_THRESHOLD = 0.8  # Seuil de cosine similarity


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs
    
    Args:
        vec1: Premier vecteur d'embeddings
        vec2: Deuxième vecteur d'embeddings
        
    Returns:
        Score de similarité entre 0 et 1 (1 = identique)
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm_vec1 = np.linalg.norm(vec1_np)
    norm_vec2 = np.linalg.norm(vec2_np)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return float(dot_product / (norm_vec1 * norm_vec2))


@tool
def vector_search_tool(question: str) -> dict:
    """
    Recherche de documents pertinents dans la base vectorielle sur les procédures administratives togolaises.
    Utilise embeddings OpenAI et cosine similarity avec seuil de 0.8 pour garantir la pertinence.
    
    Args:
        question: La question de l'utilisateur sur les procédures administratives
        
    Returns:
        Dictionnaire structuré avec documents trouvés et leurs sources (URLs)
    """
    try:
        # 1. Générer l'embedding de la question avec OpenAI direct
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=question,
            dimensions=2000
        )
        question_embedding = response.data[0].embedding
        
        # 2. Recherche dans PGVector avec pgvector distance operator
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Recherche directe avec collection_id en TEXT (plus besoin de lookup dans langchain_pg_collection)
        cursor.execute("""
            SELECT 
                document, 
                cmetadata, 
                embedding
            FROM langchain_pg_embedding
            WHERE collection_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (DOCUMENTS_COLLECTION, question_embedding, CRAG_TOP_K))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 3. Filtrer avec cosine similarity threshold
        relevant_docs = []
        for row in results:
            doc_embedding = row['embedding']
            
            # Calculer cosine similarity
            similarity_score = calculate_cosine_similarity(question_embedding, doc_embedding)
            
            # Filtrer par threshold
            if similarity_score >= SIMILARITY_THRESHOLD:
                metadata = row['cmetadata'] or {}
                relevant_docs.append({
                    "content": row['document'],
                    "url": metadata.get("url", ""),
                    "favicon": metadata.get("favicon", ""),
                    "similarity_score": round(similarity_score, 4),
                    "metadata": {
                        "chunk_index": metadata.get("chunk_index", 0),
                        "chunk_count": metadata.get("chunk_count", 1),
                        "is_official": metadata.get("is_official", False)
                    }
                })
        
        # 4. Trier par score décroissant
        relevant_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # 5. RERANKING avec LLM pour améliorer la pertinence
        if len(relevant_docs) > 5:
            print(f"🔄 Reranking de {len(relevant_docs)} documents...")
            relevant_docs = rerank_documents(question, relevant_docs, top_k=5)
        
        # 6. Retourner résultat structuré avec sources
        if relevant_docs:
            return {
                "status": "success",
                "count": len(relevant_docs),
                "threshold": SIMILARITY_THRESHOLD,
                "reranked": True if len(relevant_docs) > 0 and "rerank_score" in relevant_docs[0] else False,
                "sources": relevant_docs,  # Liste complète des documents avec URLs
                "summary": f"✅ {len(relevant_docs)} document(s) pertinent(s) trouvé(s) (seuil: {SIMILARITY_THRESHOLD}, reranked)"
            }
        else:
            return {
                "status": "no_relevant_documents",
                "count": 0,
                "threshold": SIMILARITY_THRESHOLD,
                "sources": [],
                "summary": f"❌ Aucun document pertinent (seuil: {SIMILARITY_THRESHOLD}). Recommandation: utiliser web_search_tool."
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "sources": [],
            "summary": f"❌ Erreur lors de la recherche vectorielle: {str(e)}"
        }
