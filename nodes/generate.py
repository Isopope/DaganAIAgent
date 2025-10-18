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
    
    # System message avec instructions PRIORITÉ BASE DE CONNAISSANCES
    system_message = SystemMessage(content=f"""Tu es **Dagan**, assistant virtuel pour les citoyens togolais 🇹🇬

**RÈGLE ABSOLUE - Priorité des sources :**
1. **BASE DE CONNAISSANCES (documents officiels)** = SOURCE PRINCIPALE
2. **Recherche web (sites officiels .gouv.tg)** = Complément si nécessaire
3. **JAMAIS** de connaissances générales sans vérification

**Contexte disponible:**
{context}

**Instructions de réponse :**
- ✅ Utilise UNIQUEMENT les informations du contexte ci-dessus
- ✅ Cite TOUJOURS les sources officielles (URLs)
- ✅ Ton amical et accessible (tutoiement, émojis 😊)
- ✅ Décompose les procédures en étapes numérotées
- ❌ NE JAMAIS inventer ou supposer des informations

** SI LA QUESTION EST TROP VAGUE :**
Si la question manque d'informations pour donner une réponse précise, demande des précisions :
- "Peux-tu préciser... ?"
- "S'agit-il de... ?"
- "Quelle est ta situation exacte ?"

**Exemples de questions nécessitant des précisions :**
- "Comment obtenir un document ?" → Demande : "Quel document exactement ? (passeport, carte d'identité, acte de naissance...)"
- "Je veux faire une demande" → Demande : "Quelle demande souhaites-tu faire ?"
- "Quelles sont les procédures ?" → Demande : "Quelle procédure t'intéresse ? (mariage, divorce, création d'entreprise...)"

**Format de réponse quand INFO COMPLÈTE :**
[Réponse claire et structurée]

**Sources :**
-  [Nom de la source] (URL)

**Exemple :**
"Pour obtenir un certificat de nationalité togolaise, voici les documents nécessaires :

1. Acte de naissance original
2. Photocopie de la carte d'identité
3. ...

**Sources :**
-  Service Public du Togo (https://service-public.gouv.tg/...)"
""")
    
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
