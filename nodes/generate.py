"""
Node GENERATE - Génération de réponse avec historique conversationnel (utilisant MessagesState)
"""

"""
Node GENERATE - Response generation with conversational history (usingMessagesState)
"""
import os
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from prompt import build_system_prompt

def generate(state: dict[str, Any]) -> dict[str, Any]:
    """
    Génère une réponse en utilisant les documents récupérés et l'historique conversationnel.
    Utilise MessagesState pour la gestion automatique de l'historique via le checkpointer.
    
    Processus:
    1. Récupère l'historique conversationnel depuis state["messages"]
    2. Formate le contexte avec les documents
    3. Génère la réponse avec le LLM
    4. Retourne un AIMessage qui sera automatiquement ajouté à l'historique
    
    Args:
        state: GraphState contenant messages et documents
        
    Returns:
        dict avec messages (AIMessage de réponse)
    """
    print("\n--- NODE: GENERATE ---")
    
    messages = state.get("messages", [])
    documents = state.get("documents", [])
    
    #  VÉRIFIER SI QUESTION HORS-SUJET
    is_valid_domain = state.get("is_valid_domain", True)
    domain_check_message = state.get("domain_check_message", "")
    
    if not is_valid_domain and domain_check_message:
        # Retourer directement le message de refus
        print(" Question hors-sujet - Envoi du message de refus")
        ai_message = AIMessage(content=domain_check_message)
        return {
            "messages": [ai_message],
            "generation": domain_check_message
        }
    
    print(f"Historique: {len(messages)} messages")
    print(f"Documents: {len(documents)} documents")
    
    # Configuration
    llm_model = os.getenv("LLM_MODEL", "gpt-4.1-nano")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # Formater le contexte à partir des documents
    if documents:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            source = metadata.get('source', metadata.get('url', 'Unknown'))
            context_parts.append(f"Document {i} (Source: {source}):\n{content}")
        context = "\n\n".join(context_parts)
        print(f" Contexte formaté: {len(context)} caractères")
    else:
        context = "Aucun document disponible."
        print(" Pas de documents pour le contexte")
    
    # Build system prompt via centralized template
    system_prompt_text = build_system_prompt(context)
    system_message = SystemMessage(content=system_prompt_text)
    
    # Construire les messages pour le LLM
    # Historique conversationnel + system message avec contexte
    conversation_messages = [system_message] + list(messages)
    
    print(f" Messages construits: {len(conversation_messages)} au total")
    
    # Initialiser le LLM
    try:
        llm = ChatOpenAI(
            model=llm_model,
            temperature=llm_temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print(f" LLM initialisé: {llm_model} (température: {llm_temperature})")
        
        # Générer la réponse
        response = llm.invoke(conversation_messages)
        generation = response.content
        print(f" Réponse générée: {len(generation)} caractères")
        
        # Retourner un AIMessage qui sera ajouté automatiquement à l'historique
        # par le checkpointer de LangGraph
        ai_message = AIMessage(content=generation)
        
        print("--- FIN NODE: GENERATE ---\n")
        
        # Retourner le message ET stocker dans generation pour compatibilité
        return {
            "messages": [ai_message],
            "generation": generation
        }
        
    except Exception as e:
        print(f" Erreur génération LLM: {e}")
        error_message = AIMessage(content=f"Erreur lors de la génération de la réponse: {str(e)}")
        return {
            "messages": [error_message],
            "generation": f"Erreur: {str(e)}"
        }
