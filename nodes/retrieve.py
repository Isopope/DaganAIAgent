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

def retrieve(state:Dict)->Dict:
    """Retrieve documents based on the input state using vector search.
    Args:
        state (Dict): The current state containing input data, that would be used for the retrieval process.
    Returns:
        Dict with documents key, containing the list of retrieved documents.

    """
    print("Debut recuperation des documents... ")

    #recuperer la derniere question de lhistorique des messages utilisateur
    messages= state.get("messages", [])
    if not messages:
        print("Aucun message trouvé.")
        return {"documents": []}

    last_user_message = messages[-1]
    question= last_user_message.content if hasattr(last_user_message, 'content') else str(last_user_message)
    print(f"Dernier message utilisateur: {last_user_message}")
    print(f"100 premieres caracteres de la question extraite: {question[:100]}")

    #env configuration pour : top k documents a recuperer et embedding a utiliser
    top_k= int(os.getenv("CRAG_TOP_K","5"))
    embedding_model=os.getenv("EMBEDDING_MODEL","text-embedding-3-large")
    postgres_connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
    collection_name = os.getenv("DOCUMENTS_COLLECTION", "crawled_documents")
    print(f"Recuperation des {top_k} documents avec le modele dembedding {embedding_model}... ")

    #initialisation llm embedding
    embeddings= OpenAIEmbeddings(model=embedding_model, dimensions=2000, openai_api_key=os.getenv("OPENAI_API_KEY"))
    
    #initialisation vectordb postgres/supabase
    vector_db= PGVector(
        connection_string=postgres_connection_string,
        embedding=embeddings,
        collection_name=collection_name,
        use_jsonb=True
    )

    #recherche vectorielle
    retrieved_docs= vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k}
    )

    try:
        documents= retrieved_docs.invoke(question)
        print(f"---RETRIEVED {len(documents)} DOCUMENTS---")
        return {"documents": documents}
    except Exception as e:
        print(f"Erreur lors de la récupération des documents: {str(e)}")
        return {"documents": []}

