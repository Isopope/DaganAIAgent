"""
🤖 HYBRID RAG Graph Implementation
Architecture: START → ROUTE_QUESTION → [CASUAL_CONVO | AGENT_RAG] → END

⚠️ NOTE IMPORTANTE : Ce système est un **Hybrid RAG** qui gère à la fois :
- Conversations informelles (casual) : réponses amicales, conversation générale
- Questions administratives : recherche RAG spécialisée Togo

DIFFÉRENCES vs système précédent :
- ❌ Plus de rejet des questions hors-sujet
- ✅ Gestion intelligente des conversations casual
- ✅ Routing automatique entre casual et admin
- ✅ Agent ReAct pour les questions administratives

Le routeur utilise LLM pour classifier :
- CASUAL : salutations, météo, conversation générale, questions personnelles
- ADMIN : procédures administratives, documents, services publics togolais

L'agent ReAct utilise deux tools :
- vector_search_tool : Recherche vectorielle avec cosine similarity (threshold=0.65) + reranking LLM
- web_search_tool : Recherche web Tavily avec focus Togo + reranking LLM
"""
import os
import logging
from typing import List, Literal
from typing_extensions import TypedDict

from langchain.schema import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

# Import du nouveau node routeur
from nodes.route_question import route_question

# Import du node casual conversation
from nodes.casual_convo import casual_convo

# Import du nouveau node agent
from nodes.agent_rag import agent_rag

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- GraphState Definition ---
class GraphState(MessagesState):
    """
    État du graph Hybrid RAG - hérite de MessagesState pour la gestion automatique de l'historique

    Attributes:
        messages: Historique des messages (géré automatiquement par MessagesState)
        question_type: Type de question détecté ("casual" ou "admin")
    """
    question_type: str


# --- Build Hybrid RAG Graph ---
def build_agent_graph(checkpointer=None):
    """
    Construit et compile le workflow Hybrid RAG avec architecture intelligente :
    START → ROUTE_QUESTION → [CASUAL_CONVO | AGENT_RAG] → END

    Le routeur décide automatiquement si c'est une conversation casual ou une question administrative.

    Args:
        checkpointer: Checkpointer InMemory pour la mémoire conversationnelle

    Returns:
        Compiled StateGraph prêt à être invoqué
    """
    print("\n=== Construction du Hybrid RAG Graph ===")

    # Initialiser le graph avec GraphState (hérite de MessagesState)
    workflow = StateGraph(GraphState)

    # Ajouter les nodes (architecture hybride)
    workflow.add_node("route_question", route_question)
    workflow.add_node("casual_convo", casual_convo)
    workflow.add_node("agent_rag", agent_rag)

    print("✓ Nodes ajoutés: route_question, casual_convo, agent_rag")

    # Fonction pour router après classification
    def route_after_question_type(state: GraphState) -> Literal["casual_convo", "agent_rag"]:
        """
        Route vers casual_convo pour conversations informelles,
        vers agent_rag pour questions administratives.
        """
        question_type = state.get("question_type", "admin")
        if question_type == "casual":
            return "casual_convo"
        else:
            return "agent_rag"

    # Définir les edges (architecture en Y)
    # START → route_question
    workflow.add_edge(START, "route_question")

    # route_question → [casual_convo OU agent_rag]
    workflow.add_conditional_edges(
        "route_question",
        route_after_question_type,
        {
            "casual_convo": "casual_convo",
            "agent_rag": "agent_rag"
        }
    )

    # casual_convo → END
    workflow.add_edge("casual_convo", END)

    # agent_rag → END
    workflow.add_edge("agent_rag", END)

    print("✓ Edges configurés : START → route_question → [casual_convo | agent_rag] → END")

    # Compiler le graph avec ou sans checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        print("✓ Graph compilé avec InMemorySaver checkpointer unifié")
    else:
        app = workflow.compile()
        print("✓ Graph compilé sans checkpointer (pas de mémoire)")

    print("=== Hybrid RAG Graph prêt ===\n")

    return app


# --- Graph instance globale avec InMemorySaver unifié ---
_agent_graph = None
_unified_checkpointer = None

def get_crag_graph():
    """
    Récupère l'instance du graph Hybrid RAG avec InMemorySaver unifié (singleton pattern).

    ⚠️ LEGACY NAME : Le nom "get_crag_graph" est conservé pour compatibilité,
    mais ce système est en réalité un **Hybrid RAG** qui gère conversations casual + admin.

    Architecture actuelle : Routeur intelligent → [Casual | Agent RAG]
    - Conversations informelles : réponses amicales et conversationnelles
    - Questions administratives : recherche RAG spécialisée Togo

    Returns:
        Compiled Hybrid RAG graph avec checkpointer InMemory unifié
    """
    global _agent_graph, _unified_checkpointer

    if _agent_graph is None:
        # Créer un checkpointer InMemory UNIFIÉ pour tout le système
        # (graph + agent interne partagent le même checkpointer)
        _unified_checkpointer = InMemorySaver()
        _agent_graph = build_agent_graph(checkpointer=_unified_checkpointer)
        print("✓ Checkpointer InMemory unifié créé (partagé graph + agent)")

    return _agent_graph

