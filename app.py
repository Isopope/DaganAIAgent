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





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)