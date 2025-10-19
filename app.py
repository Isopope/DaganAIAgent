import logging
import os
import sys
import asyncio
from pathlib import Path

# Fix pour Windows: utiliser SelectorEventLoop au lieu de ProactorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables FIRST, before any imports that depend on them
from dotenv import load_dotenv
load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.ERROR, format="%(message)s")
import json
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain.schema import Document, HumanMessage
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel
from tavily import TavilyClient
from supabase import create_client, Client

from crag_graph import get_crag_graph

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
postgres_connection_string = os.getenv("POSTGRES_CONNECTION_STRING")

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)


# Fonction pour enregistrer une conversation dans la table conversations
async def save_conversation_message(
    thread_id: str,
    user_message: str,
    assistant_message: str,
    user_name: str = None,
    metadata: dict = None
):
    """
    Enregistre un échange utilisateur-assistant dans la table conversations
    """
    try:
        # Récupérer le dernier message_order pour ce thread
        response = supabase.table("conversations").select("message_order").eq("thread_id", thread_id).order("message_order", desc=True).limit(1).execute()
        
        # Calculer le prochain message_order
        if response.data:
            next_order = response.data[0]["message_order"] + 1
        else:
            next_order = 1
        
        # Insérer la conversation
        conversation_data = {
            "thread_id": thread_id,
            "user_name": user_name,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "message_order": next_order,
            "metadata": metadata or {}
        }
        
        result = supabase.table("conversations").insert(conversation_data).execute()
        message_id = result.data[0]["id"] if result.data else None
        logging.info(f"✅ Conversation sauvegardée pour thread_id={thread_id}, order={next_order}, message_id={message_id}")
        
        return message_id
    except Exception as e:
        logging.error(f"❌ Erreur lors de la sauvegarde de la conversation: {e}")
        return None


async def save_information_source(
    thread_id: str,
    message_id: str,
    source_type: str,
    source_title: str,
    source_url: str = None,
    source_content: str = None,
    relevance_score: float = None,
    metadata: dict = None
):
    """
    Enregistre une source d'information utilisée par Dagan
    Types: 'web', 'document', 'vectorstore', 'memory'
    """
    try:
        response = supabase.rpc(
            "add_information_source",
            {
                "p_thread_id": thread_id,
                "p_message_id": message_id,
                "p_source_type": source_type,
                "p_source_title": source_title,
                "p_source_url": source_url,
                "p_source_content": source_content,
                "p_relevance_score": relevance_score,
                "p_metadata": metadata or {}
            }
        ).execute()
        
        source_id = response.data if response.data else None
        logging.info(f"✅ Source enregistrée: {source_type} - {source_title} (message_id={message_id})")
        return source_id
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'enregistrement de la source: {e}")
        return None


app = FastAPI(title="Dagan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "everything is ok"}


def get_agent():
    return {
        "agent": app.state.agent,
    }


class DeleteVectorStoreRequest(BaseModel):
    thread_id: str


class AgentRequest(BaseModel):
    input: str
    thread_id: str


class VectorizeRequest(BaseModel):
    url: str
    # Pas de thread_id nécessaire : documents publics partagés


class CragQueryRequest(BaseModel):
    question: str
    conversation_id: str = None  # Optional, sera généré si non fourni


@app.get("/")
async def ping():
    return {"message": "Alive"}

@app.post("/vectorize")
async def vectorize_url(
    body: VectorizeRequest,
):
    """
    Vectorize a URL by crawling it and creating embeddings in PostgreSQL
    This endpoint reads the Tavily API key from the environment variable `TAVILY_API_KEY`.
    """
    try:
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        tavily_client = TavilyClient(api_key=tavily_api_key)
        crawl_result = tavily_client.crawl(
            url=body.url, format="text", include_favicon=True,limit=4
        )

        documents = []
        for result in crawl_result["results"]:
            raw_content = result.get("raw_content")
            if not raw_content:  # Skip if None, empty string, or falsy
                continue
            
            doc = Document(
                page_content=raw_content,
                metadata={
                    "url": result.get("url", ""),
                    "favicon": result.get("favicon", ""),
                },
            )
            documents.append(doc)

        if not documents:
            raise HTTPException(status_code=400, detail="No content found to vectorize")

        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=2000,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Use PGVector for PostgreSQL/Supabase
        collection_name = os.getenv("DOCUMENTS_COLLECTION", "crawled_documents")
        
        vector_store = PGVector(
            connection=postgres_connection_string,
            embeddings=embeddings,
            collection_name=collection_name,
            use_jsonb=True
        )
        
        # Add documents with their IDs
        uuids = [str(uuid4()) for _ in range(len(documents))]
        vector_store.add_documents(documents, ids=uuids)

        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully vectorized {len(documents)} documents from {body.url}",
                "documents_count": len(documents),
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error vectorizing URL: {str(e)}")


@app.post("/delete_vector_store")
async def delete_vector_store(body: DeleteVectorStoreRequest):
    """
    Delete conversation history (checkpoints) for a specific thread_id.
    Note: Ne supprime PAS les documents vectorisés (base de connaissance publique partagée)
    """
    try:
        # Delete checkpoints (historique conversationnel)
        checkpoints_table = "langgraph_checkpoints"
        result_checkpoints = supabase.table(checkpoints_table) \
            .delete() \
            .eq("thread_id", body.thread_id) \
            .execute()
        
        # Delete checkpoint writes
        checkpoint_writes_table = "langgraph_checkpoint_writes"
        try:
            result_writes = supabase.table(checkpoint_writes_table) \
                .delete() \
                .eq("thread_id", body.thread_id) \
                .execute()
            writes_count = len(result_writes.data) if result_writes.data else 0
        except Exception as e:
            print(f"Warning: Could not delete from checkpoint_writes: {e}")
            writes_count = 0

        checkpoints_count = len(result_checkpoints.data) if result_checkpoints.data else 0

        return JSONResponse(
            content={
                "success": True,
                "message": f"Deleted conversation history for thread_id '{body.thread_id}'",
                "deleted_counts": {
                    "checkpoints": checkpoints_count,
                    "checkpoint_writes": writes_count,
                },
            }
        )

    except Exception as e:
        print(f"Error in delete_vector_store: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting vector store: {str(e)}"
        )


@app.post("/crag/query")
async def crag_query(
    body: CragQueryRequest,
    fastapi_request: Request,
):
    """
    Endpoint pour tester le workflow CRAG complet avec mémoire conversationnelle
    
    Le workflow CRAG:
    1. RETRIEVE: Recherche documents pertinents dans MongoDB
    2. GRADE: Évalue la pertinence des documents
    3. DECIDE: Route vers génération ou web search
    4. GENERATE: Génère la réponse avec historique conversationnel
       OU
    4a. TRANSFORM: Réécrit la question pour web search (avec contexte conversationnel)
    4b. WEB_SEARCH: Recherche web avec Tavily
    4c. GENERATE: Génère la réponse avec les résultats web
    
    Args:
        body: CragQueryRequest avec question et conversation_id optionnel
        
    Returns:
        JSON avec la réponse générée et des métadonnées du workflow
    """
    try:
        # Générer un conversation_id si non fourni (utiliser thread_id pour LangGraph)
        thread_id = body.conversation_id or str(uuid4())
        
        print(f"\n{'='*60}")
        print(f"CRAG Query Request")
        print(f"{'='*60}")
        print(f"Question: {body.question}")
        print(f"Thread ID: {thread_id}")
        print(f"{'='*60}\n")
        
        # Récupérer le graph CRAG (avec InMemorySaver intégré)
        crag_graph = get_crag_graph()
        
        # Préparer l'état initial avec MessagesState
        # On crée un HumanMessage avec la question
        initial_state = {
            "messages": [HumanMessage(content=body.question)],
            "documents": [],
            "generation": "",
            "transformed_question": ""
        }
        
        # Configuration pour le checkpointer (thread_id pour la mémoire)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Exécuter le workflow CRAG avec persistance de la mémoire (SYNC avec InMemorySaver)
        final_state = crag_graph.invoke(initial_state, config)
        
        print(f"\n{'='*60}")
        print(f"CRAG Workflow Completed")
        print(f"{'='*60}")
        print(f"Documents récupérés: {len(final_state.get('documents', []))}")
        print(f"Réponse générée: {len(final_state.get('generation', ''))} caractères")
        print(f"{'='*60}\n")
        
        # Construire la réponse avec métadonnées (url et favicon)
        documents = final_state.get("documents", [])
        sources = []
        
        for doc in documents:
            source_metadata = {
                "url": doc.metadata.get("url", ""),
                "favicon": doc.metadata.get("favicon", ""),
                "is_official": doc.metadata.get("is_official", False),
                "reliability_score": doc.metadata.get("reliability_score", 0.0)
            }
            sources.append(source_metadata)
        
        response_data = {
            "success": True,
            "conversation_id": thread_id,
            "question": body.question,
            "answer": final_state.get("generation", ""),
            "metadata": {
                "documents_count": len(documents),
                "sources": sources
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Erreur dans CRAG workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error in CRAG workflow: {str(e)}"
        )


@app.post("/crag/stream")
async def crag_stream(
    body: CragQueryRequest,
    fastapi_request: Request,
):
    """
    Endpoint CRAG avec streaming en temps réel (Server-Sent Events).
    
    Version streaming de /crag/query qui permet de suivre l'exécution
    du workflow node par node et de recevoir la réponse token par token.
    
    Le workflow CRAG:
    1. RETRIEVE: Recherche documents pertinents dans MongoDB
    2. GRADE: Évalue la pertinence des documents
    3. DECIDE: Route vers génération ou web search
    4. GENERATE: Génère la réponse avec historique conversationnel (streaming)
       OU
    4a. TRANSFORM: Réécrit la question pour web search (avec contexte)
    4b. WEB_SEARCH: Recherche web avec Tavily
    4c. GENERATE: Génère la réponse avec résultats web (streaming)
    
    Args:
        body: CragQueryRequest avec question et conversation_id optionnel
        
    Returns:
        StreamingResponse avec events SSE (Server-Sent Events)
        
    Format des events:
        - {"type": "node_start", "node": "retrieve"}
        - {"type": "node_end", "node": "retrieve", "documents_count": 5}
        - {"type": "message_chunk", "content": "...", "node": "generate"}
        - {"type": "complete", "conversation_id": "...", "answer": "..."}
    """
    # No Authorization header required for streaming endpoint
    
    async def event_generator():
        """Génère les events SSE pour le streaming."""
        try:
            # Générer un conversation_id si non fourni
            thread_id = body.conversation_id or str(uuid4())
            
            print(f"\n{'='*60}")
            print(f"🌊 CRAG Stream Request")
            print(f"{'='*60}")
            print(f"Question: {body.question}")
            print(f"Thread ID: {thread_id}")
            print(f"{'='*60}\n")
            
            # Récupérer le graph CRAG
            crag_graph = get_crag_graph()
            
            # Préparer l'état initial
            initial_state = {
                "messages": [HumanMessage(content=body.question)],
                "documents": [],
                "generation": "",
                "transformed_question": ""
            }
            
            # Configuration pour le checkpointer
            config = {"configurable": {"thread_id": thread_id}}
            
            # Variables pour accumuler la réponse et les sources
            accumulated_answer = ""
            final_documents_count = 0
            collected_sources = []  # Pour stocker les sources CRAG
            
            # Streamer le workflow CRAG
            async for event in crag_graph.astream(initial_state, config):
                # event est un dict avec une clé = nom du node
                # et valeur = état retourné par ce node
                
                for node_name, node_output in event.items():
                    print(f"📊 Node: {node_name}")
                    
                    # ─────────────────────────────────────────────────
                    # VALIDATE_DOMAIN node
                    # ─────────────────────────────────────────────────
                    if node_name == "validate_domain":
                        is_valid = node_output.get("is_valid_domain", True)
                        
                        if not is_valid:
                            yield (
                                json.dumps({
                                    "type": "node_end",
                                    "node": "validate_domain",
                                    "message": "❌ Question hors-sujet administratif"
                                }) + "\n"
                            )
                        else:
                            yield (
                                json.dumps({
                                    "type": "node_end",
                                    "node": "validate_domain",
                                    "message": "✅ Question validée (domaine administratif)"
                                }) + "\n"
                            )
                    
                    # ─────────────────────────────────────────────────
                    # RETRIEVE node
                    # ─────────────────────────────────────────────────
                    elif node_name == "retrieve":
                        docs_count = len(node_output.get("documents", []))
                        final_documents_count = docs_count
                        
                        # Capturer les sources des documents récupérés - MÊME FORMAT que crag/query
                        for doc in node_output.get("documents", []):
                            collected_sources.append({
                                "url": doc.metadata.get("url", ""),
                                "favicon": doc.metadata.get("favicon", ""),
                                "is_official": doc.metadata.get("is_official", False),
                                "reliability_score": doc.metadata.get("reliability_score", 0.0)
                            })
                        
                        yield (
                            json.dumps({
                                "type": "node_start",
                                "node": "retrieve",
                                "message": f"🔍 Recherche de documents pertinents..."
                            }) + "\n"
                        )
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "retrieve",
                                "documents_count": docs_count,
                                "message": f"✅ {docs_count} documents trouvés"
                            }) + "\n"
                        )
                    
                    # ─────────────────────────────────────────────────
                    # GRADE_DOCUMENTS node
                    # ─────────────────────────────────────────────────
                    elif node_name == "grade_documents":
                        docs_count = len(node_output.get("documents", []))
                        final_documents_count = docs_count
                        
                        yield (
                            json.dumps({
                                "type": "node_start",
                                "node": "grade_documents",
                                "message": "📝 Évaluation de la pertinence..."
                            }) + "\n"
                        )
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "grade_documents",
                                "documents_count": docs_count,
                                "message": f"✅ {docs_count} documents pertinents"
                            }) + "\n"
                        )
                    
                    # ─────────────────────────────────────────────────
                    # DECIDE_TO_GENERATE node
                    # ─────────────────────────────────────────────────
                    elif node_name == "decide_to_generate":
                        docs_count = len(node_output.get("documents", []))
                        decision = "generate" if docs_count > 0 else "web_search"
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "decide_to_generate",
                                "decision": decision,
                                "message": f"🎯 Route: {'Génération directe' if docs_count > 0 else 'Recherche web'}"
                            }) + "\n"
                        )
                    
                    # ─────────────────────────────────────────────────
                    # TRANSFORM_QUERY node
                    # ─────────────────────────────────────────────────
                    elif node_name == "transform_query":
                        transformed = node_output.get("transformed_question", "")
                        
                        yield (
                            json.dumps({
                                "type": "node_start",
                                "node": "transform_query",
                                "message": "🔄 Reformulation de la question..."
                            }) + "\n"
                        )
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "transform_query",
                                "transformed_question": transformed,
                                "message": f"✅ Question reformulée"
                            }) + "\n"
                        )
                    
                    # ─────────────────────────────────────────────────
                    # WEB_SEARCH node
                    # ─────────────────────────────────────────────────
                    elif node_name == "web_search":
                        docs_count = len(node_output.get("documents", []))
                        final_documents_count = docs_count
                        
                        # Capturer les sources web (Tavily) - MÊME FORMAT que crag/query
                        for doc in node_output.get("documents", []):
                            collected_sources.append({
                                "url": doc.metadata.get("url", ""),
                                "favicon": doc.metadata.get("favicon", ""),
                                "is_official": doc.metadata.get("is_official", False),
                                "reliability_score": doc.metadata.get("reliability_score", 0.0)
                            })
                        
                        yield (
                            json.dumps({
                                "type": "node_start",
                                "node": "web_search",
                                "message": "🌐 Recherche web Tavily..."
                            }) + "\n"
                        )
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "web_search",
                                "documents_count": docs_count,
                                "message": f"✅ {docs_count} résultats trouvés"
                            }) + "\n"
                        )
                    
                    # ─────────────────────────────────────────────────
                    # GENERATE node - STREAMING TOKEN PAR TOKEN
                    # ─────────────────────────────────────────────────
                    elif node_name == "generate":
                        yield (
                            json.dumps({
                                "type": "node_start",
                                "node": "generate",
                                "message": "💬 Génération de la réponse..."
                            }) + "\n"
                        )
                        
                        # Le node generate retourne déjà la réponse complète
                        # Pour du vrai streaming, il faudrait modifier le node generate
                        # Pour l'instant, on envoie la réponse complète
                        generation = node_output.get("generation", "")
                        accumulated_answer = generation
                        
                        # Simuler un streaming en envoyant par chunks
                        chunk_size = 50  # Caractères par chunk
                        for i in range(0, len(generation), chunk_size):
                            chunk = generation[i:i+chunk_size]
                            yield (
                                json.dumps({
                                    "type": "message_chunk",
                                    "content": chunk,
                                    "node": "generate"
                                }) + "\n"
                            )
                        
                        yield (
                            json.dumps({
                                "type": "node_end",
                                "node": "generate",
                                "message": "✅ Réponse générée"
                            }) + "\n"
                        )
            
            # ─────────────────────────────────────────────────────────
            # EVENT FINAL - Workflow complet
            # ─────────────────────────────────────────────────────────
            print(f"\n{'='*60}")
            print(f"✅ CRAG Stream Completed")
            print(f"{'='*60}")
            print(f"Documents: {final_documents_count}")
            print(f"Réponse: {len(accumulated_answer)} caractères")
            print(f"Sources: {len(collected_sources)}")
            print(f"{'='*60}\n")
            
            # Sauvegarder la conversation et les sources
            if accumulated_answer:
                message_id = await save_conversation_message(
                    thread_id=thread_id,
                    user_message=body.question,
                    assistant_message=accumulated_answer,
                    metadata={
                        "api_endpoint": "crag_stream",
                        "documents_count": final_documents_count,
                        "sources_count": len(collected_sources)
                    }
                )
                
                # Sauvegarder les sources
                if message_id and collected_sources:
                    for source in collected_sources:
                        # Adapter les champs disponibles pour la sauvegarde
                        # Les sources ont maintenant: url, favicon, is_official, reliability_score
                        source_type = "web" if source.get("url", "").startswith("http") else "document"
                        source_title = source.get("url", "").split("/")[-1] if source.get("url") else "Source"
                        
                        await save_information_source(
                            thread_id=thread_id,
                            message_id=message_id,
                            source_type=source_type,
                            source_title=source_title,
                            source_url=source.get("url"),
                            relevance_score=source.get("reliability_score"),
                            metadata={
                                "is_official": source.get("is_official", False),
                                "favicon": source.get("favicon", "")
                            }
                        )
            
            yield (
                json.dumps({
                    "type": "complete",
                    "conversation_id": thread_id,
                    "question": body.question,
                    "answer": accumulated_answer,
                    "metadata": {
                        "documents_count": final_documents_count,
                        "sources_count": len(collected_sources)
                    }
                }) + "\n"
            )
            
        except Exception as e:
            print(f"❌ Erreur dans CRAG stream: {str(e)}")
            import traceback
            traceback.print_exc()
            
            yield (
                json.dumps({
                    "type": "error",
                    "error": str(e),
                    "message": f"Erreur: {str(e)}"
                }) + "\n"
            )
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Désactive le buffering nginx
        }
    )


@app.get("/conversations/{thread_id}")
async def get_conversation(thread_id: str):
    """
    Récupère l'historique complet d'une conversation par thread_id
    """
    try:
        response = supabase.rpc(
            "get_conversation_history",
            {"p_thread_id": thread_id}
        ).execute()
        
        return {
            "thread_id": thread_id,
            "message_count": len(response.data),
            "messages": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/conversations/user/{user_name}")
async def get_user_conversations(user_name: str, limit: int = 50):
    """
    Récupère toutes les conversations d'un utilisateur
    """
    try:
        response = supabase.rpc(
            "get_user_conversations",
            {"p_user_name": user_name, "p_limit": limit}
        ).execute()
        
        return {
            "user_name": user_name,
            "conversation_count": len(response.data),
            "conversations": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/conversations")
async def list_all_conversations(limit: int = 100):
    """
    Liste toutes les conversations récentes (tous utilisateurs)
    """
    try:
        response = supabase.table("conversations").select("*").order("created_at", desc=True).limit(limit).execute()
        
        # Grouper par thread_id
        conversations_by_thread = {}
        for msg in response.data:
            thread_id = msg["thread_id"]
            if thread_id not in conversations_by_thread:
                conversations_by_thread[thread_id] = []
            conversations_by_thread[thread_id].append(msg)
        
        return {
            "total_messages": len(response.data),
            "thread_count": len(conversations_by_thread),
            "conversations": conversations_by_thread
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.delete("/conversations/{thread_id}")
async def delete_conversation(thread_id: str):
    """
    Supprime une conversation complète
    """
    try:
        response = supabase.rpc(
            "delete_conversation",
            {"p_thread_id": thread_id}
        ).execute()
        
        deleted_count = response.data if response.data else 0
        
        return {
            "message": f"Conversation supprimée",
            "thread_id": thread_id,
            "deleted_messages": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/sources/message/{message_id}")
async def get_message_sources(message_id: str):
    """
    Récupère toutes les sources utilisées pour un message spécifique
    """
    try:
        response = supabase.rpc(
            "get_message_sources",
            {"p_message_id": message_id}
        ).execute()
        
        return {
            "message_id": message_id,
            "source_count": len(response.data),
            "sources": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/sources/thread/{thread_id}")
async def get_thread_sources(thread_id: str, limit: int = 50):
    """
    Récupère toutes les sources utilisées dans un thread
    """
    try:
        response = supabase.rpc(
            "get_thread_sources",
            {"p_thread_id": thread_id, "p_limit": limit}
        ).execute()
        
        return {
            "thread_id": thread_id,
            "source_count": len(response.data),
            "sources": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/conversations/{thread_id}/with-sources")
async def get_conversation_with_sources(thread_id: str):
    """
    Récupère une conversation complète avec toutes ses sources
    Format enrichi similaire à ChatGPT
    """
    try:
        # Récupérer la conversation
        conv_response = supabase.rpc(
            "get_conversation_history",
            {"p_thread_id": thread_id}
        ).execute()
        
        # Pour chaque message, récupérer ses sources
        enriched_messages = []
        for msg in conv_response.data:
            sources_response = supabase.rpc(
                "get_message_sources",
                {"p_message_id": msg["id"]}
            ).execute()
            
            enriched_messages.append({
                **msg,
                "sources": sources_response.data
            })
        
        return {
            "thread_id": thread_id,
            "message_count": len(enriched_messages),
            "messages": enriched_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)