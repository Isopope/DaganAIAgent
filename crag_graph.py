"""
🤖 AGENTIC RAG Graph Implementation (Legacy name: "CRAG")
Architecture: START → VALIDATE_DOMAIN → AGENT_RAG → END

⚠️ NOTE IMPORTANTE : Ce système est un **Agentic RAG** (Agent-based RAG), PAS un CRAG.
Le nom "CRAG" dans le code est historique/legacy et conservé pour compatibilité.

DIFFÉRENCES vs CRAG traditionnel :
- ❌ Pas de pipeline fixe RETRIEVE → GRADE → DECIDE
- ❌ Pas de correction conditionnelle binaire (if/else)
- ✅ Agent ReAct autonome qui décide de sa stratégie
- ✅ Tools à disposition (pas nodes obligatoires)
- ✅ Reasoning loop adaptatif et non déterministe

L'agent ReAct utilise deux tools :
- vector_search_tool : Recherche vectorielle avec cosine similarity (threshold=0.8) + reranking LLM
- web_search_tool : Recherche web Tavily avec focus Togo + reranking LLM

L'agent décide lui-même quand utiliser chaque tool via ReAct loop.
"""
import os
import logging
from typing import List, Literal
from typing_extensions import TypedDict

from langchain.schema import Document
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

# Import du node de validation de domaine (inchangé)
from nodes.validate_context import validate_context as validate_domain

# Import du nouveau node agent
from nodes.agent_rag import agent_rag

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- GraphState Definition ---
class GraphState(MessagesState):
    """
    État du graph Agent RAG - hérite de MessagesState pour la gestion automatique de l'historique
    
    Attributes:
        messages: Historique des messages (géré automatiquement par MessagesState)
        is_valid_domain: Indicateur si la question concerne le domaine administratif togolais
        domain_check_message: Message de refus si question hors-sujet (optionnel)
    """
    is_valid_domain: bool
    domain_check_message: str


# --- Build Agent RAG Graph ---
def build_agent_graph(checkpointer=None):
    """
    Construit et compile le workflow Agent RAG avec architecture pure :
    START → VALIDATE_DOMAIN → AGENT_RAG → END
    
    L'agent décide lui-même quand utiliser vector_search ou web_search via ReAct loop.
       
    Args:
        checkpointer: Checkpointer InMemory pour la mémoire conversationnelle
        
    Returns:
        Compiled StateGraph prêt à être invoqué
    """
    print("\n=== Construction du Agent RAG Graph ===")
    
    # Initialiser le graph avec GraphState (hérite de MessagesState)
    workflow = StateGraph(GraphState)
    
    # Ajouter les nodes (architecture simplifiée)
    workflow.add_node("validate_domain", validate_domain)
    workflow.add_node("agent_rag", agent_rag)
    
    print("✓ Nodes ajoutés: validate_domain, agent_rag")
    
    # Fonction pour décider après validation du domaine
    def route_after_domain_check(state: GraphState) -> Literal["agent_rag", "__end__"]:
        """
        Route vers agent_rag si la question est valide, sinon termine directement.
        Le message de refus est déjà ajouté par validate_domain dans les messages.
        """
        if state.get("is_valid_domain", True):
            return "agent_rag"
        else:
            # Si hors-sujet, on termine (le message de refus est déjà dans state["messages"])
            return "__end__"
    
    # Définir les edges (architecture linéaire simple)
    # START → validate_domain
    workflow.add_edge(START, "validate_domain")
    
    # validate_domain → [agent_rag OU END]
    workflow.add_conditional_edges(
        "validate_domain",
        route_after_domain_check,
        {
            "agent_rag": "agent_rag",
            "__end__": END
        }
    )
    
    # agent_rag → END
    workflow.add_edge("agent_rag", END)
    
    print("✓ Edges configurés : START → validate_domain → agent_rag → END")
    
    # Compiler le graph avec ou sans checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        print("✓ Graph compilé avec InMemorySaver checkpointer unifié")
    else:
        app = workflow.compile()
        print("✓ Graph compilé sans checkpointer (pas de mémoire)")
    
    print("=== Agent RAG Graph prêt ===\n")
    
    return app


# --- Graph instance globale avec InMemorySaver unifié ---
_agent_graph = None
_unified_checkpointer = None

def get_crag_graph():
    """
    Récupère l'instance du graph Agent RAG avec InMemorySaver unifié (singleton pattern).
    
    ⚠️ LEGACY NAME : Le nom "get_crag_graph" est conservé pour compatibilité,
    mais ce système est en réalité un **Agentic RAG** (Agent-based RAG), pas un CRAG.
    
    Architecture actuelle : Agent ReAct autonome qui décide lui-même de sa stratégie
    (pas de pipeline RETRIEVE → GRADE → DECIDE fixe comme dans CRAG classique)
    
    Returns:
        Compiled Agent RAG graph avec checkpointer InMemory unifié
    """
    global _agent_graph, _unified_checkpointer
    
    if _agent_graph is None:
        # Créer un checkpointer InMemory UNIFIÉ pour tout le système
        # (graph + agent interne partagent le même checkpointer)
        _unified_checkpointer = InMemorySaver()
        _agent_graph = build_agent_graph(checkpointer=_unified_checkpointer)
        print("✓ Checkpointer InMemory unifié créé (partagé graph + agent)")
    
    return _agent_graph

