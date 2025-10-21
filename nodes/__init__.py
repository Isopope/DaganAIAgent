"""
Agent RAG Nodes Package
Contient les nodes du workflow Agent RAG

Note : Les anciens nodes CRAG (retrieve, grade, decision, transform, web_search, generate)
sont conservés pour compatibilité mais ne sont plus utilisés dans le nouveau workflow.
Le nouveau workflow utilise uniquement : validate_domain → agent_rag
"""

# Nouveaux nodes (architecture Agent RAG)
from .agent_rag import agent_rag

# Anciens nodes CRAG (conservés pour compatibilité, mais non utilisés)
from .retrieve import retrieve
from .grade import grade_documents
from .decision import decide_to_generate
from .transform import transform_query
from .web_search import web_search
from .generate import generate

__all__ = [
    # Nouveau workflow
    "agent_rag",
    
    # Anciens nodes (compatibilité)
    "retrieve", 
    "grade_documents", 
    "decide_to_generate", 
    "transform_query",
    "web_search",
    "generate"
]
