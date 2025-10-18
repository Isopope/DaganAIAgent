"""
CRAG (Corrective RAG) Implementation
Architecture: RETRIEVE → GRADE → DECIDE → (GENERATE | TRANSFORM → WEB_SEARCH → GENERATE)
"""
import os
import logging
from typing import List, Literal, Annotated
from typing_extensions import TypedDict
from datetime import datetime

from langchain.schema import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

# Import des nodes CRAG (on n'a plus besoin de contextualize_question)
from nodes import (
    retrieve,
    grade_documents,
    decide_to_generate,
    transform_query,
    web_search,
    generate
)
from nodes.validate_context import validate_domain

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- GraphState Definition ---
class GraphState(MessagesState):
    """
    État du graph CRAG - hérite de MessagesState pour la gestion automatique de l'historique
    
    Attributes:
        messages: Historique des messages (géré automatiquement par MessagesState)
        documents: Liste de documents récupérés (filtrée par gradeDocuments, enrichie par webSearch)
        generation: Réponse finale du LLM (optionnel, pour compatibilité)
        transformed_question: Question reformulée par transform_query (pour web_search)
        is_valid_domain: Indicateur si la question concerne le domaine administratif togolais
        domain_check_message: Message de refus si question hors-sujet
    """
    documents: List[Document]
    generation: str
    transformed_question: str
    is_valid_domain: bool
    domain_check_message: str


# --- Build CRAG Graph ---
def build_crag_graph(checkpointer=None):
    """
    Construit et compile le workflow CRAG complet avec support du checkpointer
       
    Args:
        checkpointer: Checkpointer MongoDB pour la persistance de la mémoire
        
    Returns:
        Compiled StateGraph prêt à être invoqué
    """
    print("\n=== Construction du CRAG Graph ===")
    
    # Initialiser le graph avec MessagesState
    workflow = StateGraph(GraphState)
    
    # Ajouter les nodes (avec validate_domain en premier)
    workflow.add_node("validate_domain", validate_domain)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("web_search", web_search)
    workflow.add_node("generate", generate)
    
    print("✓ Nodes ajoutés: validate_domain, retrieve, grade_documents, transform_query, web_search, generate")
    
    # Fonction pour décider après validation du domaine
    def route_after_domain_check(state: GraphState) -> Literal["retrieve", "generate"]:
        """Route vers retrieve si valide, sinon vers generate pour message de refus"""
        if state.get("is_valid_domain", True):
            return "retrieve"
        else:
            return "generate"
    
    # Définir les edges
    # START → validate_domain
    workflow.add_edge(START, "validate_domain")
    
    # validate_domain → [retrieve OU generate]
    workflow.add_conditional_edges(
        "validate_domain",
        route_after_domain_check,
        {
            "retrieve": "retrieve",
            "generate": "generate"
        }
    )
    
    # retrieve → grade_documents
    workflow.add_edge("retrieve", "grade_documents")
    
    # grade_documents → decide (conditional routing)
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "transformQuery": "transform_query"
        }
    )
    
    # transform_query → web_search
    workflow.add_edge("transform_query", "web_search")
    
    # web_search → generate
    workflow.add_edge("web_search", "generate")
    
    # generate → END
    workflow.add_edge("generate", END)
    
    print("✓ Edges configurés avec routing conditionnel + validation domaine")
    
    # Compiler le graph avec ou sans checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        print("✓ Graph compilé avec InMemorySaver checkpointer")
    else:
        app = workflow.compile()
        print("✓ Graph compilé sans checkpointer (pas de mémoire persistante)")
    
    print("=== CRAG Graph prêt ===\n")
    
    return app


# --- Graph instance globale avec InMemorySaver ---
_crag_graph = None
_crag_checkpointer = None

def get_crag_graph():
    """
    Récupère l'instance du graph CRAG avec InMemorySaver (singleton pattern)
    
    Returns:
        Compiled CRAG graph avec checkpointer InMemory
    """
    global _crag_graph, _crag_checkpointer
    
    if _crag_graph is None:
        # Créer un checkpointer InMemory pour la mémoire short-term
        _crag_checkpointer = InMemorySaver()
        _crag_graph = build_crag_graph(checkpointer=_crag_checkpointer)
    
    return _crag_graph

