"""
Node RETRIEVE - Récupération de documents via recherche vectorielle PostgreSQL/Supabase
"""

"""
Node RETRIEVE - Document retrieval via PostgreSQL/Supabase vector search
"""
import os
import logging
from typing import Dict, List

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

# Configuration du logger
logger = logging.getLogger(__name__)

def retrieve(state:Dict)->Dict:
    """Retrieve documents based on the input state using vector search.
    
    Fusion intelligente:
    - Récupère initialement plus de documents (CRAG_TOP_K_INITIAL, défaut 20)
    - Filtre optionnellement par thread_id si présent dans state
    - Retourne les N meilleurs documents (CRAG_TOP_K, défaut 10)
    
    Args:
        state (Dict): The current state containing input data, that would be used for the retrieval process.
                     Peut contenir thread_id pour isolation conversationnelle
    Returns:
        Dict with documents key, containing the list of retrieved documents.

    """
    logger.info("\n--- NODE: RETRIEVE (Vector Search) ---")

    #recuperer la derniere question de lhistorique des messages utilisateur
    messages= state.get("messages", [])
    if not messages:
        logger.warning("Aucun message trouvé dans l'état.")
        return {"documents": []}

    last_user_message = messages[-1]
    question= last_user_message.content if hasattr(last_user_message, 'content') else str(last_user_message)
    logger.info(f"Question extraite: {question[:100]}...")

    # Récupérer thread_id optionnel pour filtrage conversationnel
    thread_id = state.get("thread_id", None)
    if thread_id:
        logger.info(f"Thread ID détecté: {thread_id} (filtrage conversationnel activé)")

    #env configuration pour : top k documents a recuperer et embedding a utiliser
    top_k_initial = int(os.getenv("CRAG_TOP_K_INITIAL", "20"))  # Récupération initiale large
    top_k_final = int(os.getenv("CRAG_TOP_K", "10"))  # Nombre final après filtrage
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    postgres_connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
    collection_name = os.getenv("DOCUMENTS_COLLECTION", "crawled_documents")
    
    logger.info(f"Configuration: initial_k={top_k_initial}, final_k={top_k_final}, model={embedding_model}")

    #initialisation llm embedding
    embeddings= OpenAIEmbeddings(
        model=embedding_model, 
        dimensions=2000, 
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    #initialisation vectordb postgres/supabase
    vector_db= PGVector(
        connection=postgres_connection_string,
        embeddings=embeddings,
        collection_name=collection_name,
        use_jsonb=True
    )

    try:
        # Recherche vectorielle avec k initial plus large
        logger.info(f"Lancement recherche vectorielle (k={top_k_initial})...")
        all_results = vector_db.similarity_search(question, k=top_k_initial)
        
        logger.info(f"Récupéré {len(all_results)} documents initiaux")

        # Filtrage optionnel par thread_id
        if thread_id:
            filtered_results = [
                doc for doc in all_results
                if doc.metadata.get("thread_id") == thread_id
            ]
            logger.info(f"Après filtrage thread_id: {len(filtered_results)} documents")
            documents = filtered_results[:top_k_final]
        else:
            documents = all_results[:top_k_final]

        logger.info(f"Documents finaux retournés: {len(documents)}")
        
        # Log des métadonnées pour debug
        for i, doc in enumerate(documents[:3]):  # Log les 3 premiers
            logger.debug(f"  Doc {i+1}: url={doc.metadata.get('url', 'N/A')}, favicon={doc.metadata.get('favicon', 'N/A')}")
        
        logger.info("--- END NODE: RETRIEVE ---\n")
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des documents: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"documents": []}

