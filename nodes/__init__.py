"""
Agent RAG Nodes Package
Contient les nodes du workflow Agent RAG

Architecture actuelle : validate_domain → agent_rag
Les anciens nodes CRAG ont été supprimés (commentés dans leurs fichiers respectifs).
"""

# Nodes actifs (architecture Agent RAG)
from .agent_rag import agent_rag

__all__ = [
    "agent_rag"
]
