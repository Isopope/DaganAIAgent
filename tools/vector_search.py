import os
import json
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from typing import List
from langchain.tools import tool
from openai import OpenAI
from tools.reranker import rerank_documents

# Configuration
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Chercher dans TOUTES les collections (pas juste une seule)
DOCUMENTS_COLLECTION = None  # None = chercher dans toutes les collections
CRAG_TOP_K = int(os.getenv("CRAG_TOP_K", "20"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
ENABLE_RERANKING = os.getenv("ENABLE_RERANKING", "true").lower() in ("true", "1", "yes")


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs numpy
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    denom = np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np)
    if denom == 0:
        return 0.0
    return float(np.dot(vec1_np, vec2_np) / denom)


def adaptive_threshold(similarities: List[float], alpha: float = 0.1) -> float:
    """
    Seuil fixe conservateur pour garantir la pertinence des résultats
    Augmenté à 0.70 pour éviter les faux positifs
    """
    return 0.70  # Seuil fixe : garder uniquement les documents avec similarité >= 70%


@tool
def vector_search_tool(question: str) -> dict:
    """
    Recherche de documents pertinents dans la base vectorielle (pgvector)
    avec reranking hybride (cosine + LLM).
    """
    try:
        #  Génération de l'embedding de la question
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=question,
            dimensions=2000
        )
        question_embedding = response.data[0].embedding

        # Connexion PostgreSQL (pgvector)
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        register_vector(conn)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Recherche vectorielle brute dans TOUTES les collections
        # NOTE: ORDER BY sur la similarité calculée (DESC) au lieu de l'opérateur de distance
        cursor.execute(
            """
            SELECT 
                document,
                cmetadata,
                embedding,
                collection_id,
                1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM langchain_pg_embedding
            ORDER BY 1 - (embedding <=> %s::vector) DESC
            LIMIT %s
            """,
            (question_embedding, question_embedding, CRAG_TOP_K)
        )

        rows = cursor.fetchall()
        
        # DEBUG: Afficher les résultats bruts
        print(f"\n{'='*60}")
        print(f"VECTOR SEARCH DEBUG")
        print(f"{'='*60}")
        print(f"Query: {question}")
        print(f"DOCUMENTS_COLLECTION: {DOCUMENTS_COLLECTION}")
        print(f"CRAG_TOP_K (limite SQL): {CRAG_TOP_K}")
        print(f"Documents récupérés (brut SQL): {len(rows)}")
        if rows:
            print(f"\nTop 5 similarités brutes:")
            for i, r in enumerate(rows[:5], 1):
                print(f"  {i}. {r['cosine_similarity']:.4f} - Collection: {r.get('collection_id', 'N/A')}")
            print(f"\nCollections trouvées: {set(r.get('collection_id', 'unknown') for r in rows)}")
        print(f"{'='*60}\n")
        
        cursor.close()
        conn.close()

        if not rows:
            return {
                "status": "no_results",
                "summary": "Aucun document trouvé dans la base vectorielle.",
                "sources": []
            }

        # Filtrage adaptatif selon la distribution des similarités
        similarities = [r["cosine_similarity"] for r in rows]
        threshold = adaptive_threshold(similarities)
        filtered_docs = [r for r in rows if r["cosine_similarity"] >= threshold]

        print(f"📊 FILTRAGE ADAPTATIF:")
        print(f"   Seuil calculé: {threshold:.4f}")
        print(f"   Documents après filtrage: {len(filtered_docs)}/{len(rows)}")

        if not filtered_docs:
            return {
                "status": "no_relevant_documents",
                "summary": f"Aucun document au-dessus du seuil adaptatif ({threshold:.2f}).",
                "threshold": threshold,
                "sources": [],
                
            }

        #  Préparation des documents
        relevant_docs = []
        for row in filtered_docs:
            meta = row.get("cmetadata") or {}
            relevant_docs.append({
                "content": row["document"],
                "url": meta.get("url", ""),
                "favicon": meta.get("favicon", ""),
                "similarity_score": round(row["cosine_similarity"], 4),
                "metadata": {
                    "chunk_index": meta.get("chunk_index", 0),
                    "chunk_count": meta.get("chunk_count", 1),
                    "is_official": meta.get("is_official", False)
                }
            })

        # Reranking LLM (optionnel, contrôlé par ENABLE_RERANKING)
        if ENABLE_RERANKING and len(relevant_docs) > 5:
            print(f"🔄 RERANKING: {len(relevant_docs)} documents → Top 5")
            reranked_docs = rerank_documents(question, relevant_docs, top_k=5)
        else:
            if not ENABLE_RERANKING:
                print(f"⏭️ RERANKING DÉSACTIVÉ (ENABLE_RERANKING=false)")
            else:
                print(f"⏭️ RERANKING SKIP: {len(relevant_docs)} documents (≤5)")
            reranked_docs = relevant_docs

        #  Score hybride
        for doc in reranked_docs:
            rerank_score = doc.get("rerank_score", 0.0)
            sim_score = doc.get("similarity_score", 0.0)
            # Si le reranking est désactivé, utiliser uniquement similarity_score
            if ENABLE_RERANKING and rerank_score > 0:
                doc["final_score"] = round(0.7 * sim_score + 0.3 * rerank_score, 4)
            else:
                doc["final_score"] = round(sim_score, 4)

        print(f"✅ DOCUMENTS FINAUX: {len(reranked_docs)}\n")

        reranked_docs.sort(key=lambda x: x["final_score"], reverse=True)

        #  Résumé de sortie
        return {
            "status": "success",
            "count": len(reranked_docs),
            "threshold": round(threshold, 3),
            "sources": reranked_docs,
            "summary": f"{len(reranked_docs)} document(s) retenu(s) avec reranking hybride (seuil adaptatif: {threshold:.2f})."
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "summary": f"Erreur lors de la recherche vectorielle : {str(e)}",
            "sources": []
        }
