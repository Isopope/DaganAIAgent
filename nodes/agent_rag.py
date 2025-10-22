"""
Node AGENT_RAG - Agent ReAct avec tools (vector_search + web_search)
Remplace l'ancien workflow CRAG linéaire par un agent intelligent
Utilise initialize_agent (stable et compatible)
"""

import os
from typing import Dict, List, Optional, Any
from langchain.llms.base import LLM
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks.manager import CallbackManagerForLLMRun
from openai import OpenAI

# Import tools
from tools import vector_search_tool, web_search_tool

# Import du prompt centralisé
from prompt import SYSTEM_PROMPT_TEMPLATE


# Wrapper LLM personnalisé pour éviter langchain_openai
class OpenAILLM(LLM):
    """Wrapper OpenAI LLM compatible avec LangChain agents"""
    
    client: Any = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.7):
        super().__init__()
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
    
    @property
    def _llm_type(self) -> str:
        return "openai"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            stop=stop
        )
        return response.choices[0].message.content


def agent_rag(state: Dict) -> Dict:
    """
    Node AGENT_RAG - Agent ReAct qui utilise les tools pour répondre
    Modifie l'état MessagesState en ajoutant un AIMessage avec la réponse
    
    Args:
        state: Dict avec 'messages' (MessagesState), 'is_valid_domain', etc.
    
    Returns:
        Dict avec l'état mis à jour (messages + AIMessage)
    """
    
    print("\n→ Entrée dans agent_rag node")
    
    messages = state.get("messages", [])
    is_valid_domain = state.get("is_valid_domain", True)
    
    #extraire la dernière question utilisateur
    from langchain_core.messages import HumanMessage as LangchainHumanMessage
    user_messages = [msg for msg in messages if isinstance(msg, LangchainHumanMessage)]
    
    if not user_messages:
        error_message = AIMessage(content="Aucune question détectée dans les messages")
        return {"messages": [error_message]}
    
    question = user_messages[-1].content
    print(f" Question extraite: '{question}'")
    
    if not is_valid_domain:
        # Ajouter un message d'erreur aux messages existants
        error_message = AIMessage(content="Domaine non validé - impossible de traiter la question")
        return {"messages": [error_message]}
    
    # Configuration LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_message = AIMessage(content="Erreur: OPENAI_API_KEY non configuré")
        return {"messages": [error_message]}
    
    print(" Initialisation de l'agent ReAct avec tools...")
    
    # Créer LLM wrapper
    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini", temperature=0.7)
    
    # Créer les tools
    tools = [
        vector_search_tool,
        web_search_tool
    ]
    
    print(f"🛠️  Tools disponibles: {[t.name for t in tools]}")
    
    # Adapter le prompt système pour l'agent ReAct
    # Le prompt SYSTEM_PROMPT_TEMPLATE est conçu pour un RAG classique avec contexte
    # On l'adapte pour un agent qui utilise des tools
    agent_system_prompt = """Tu es **Dagan**, assistant virtuel pour les citoyens togolais 🇹🇬

**TA MISSION :**
Aider les citoyens avec des informations précises sur les procédures administratives et services publics togolais.

**RÈGLE ABSOLUE - Priorité des sources :**
1. **BASE DE CONNAISSANCES** (via vector_search_tool) = SOURCE PRINCIPALE
2. **Recherche web** (via web_search_tool sur sites .gouv.tg) = Complément si nécessaire
3. **JAMAIS** d'informations sans vérification

**GESTION DES QUESTIONS VAGUES :**
Si la question manque de précisions (ex: "quelles pièces?", "comment faire?"), tu DOIS:
- Identifier le contexte probable (passeport, carte d'identité, etc.)
- Si possible, fournir une réponse générale pour les cas les plus courants
- Suggérer de préciser pour une réponse plus adaptée

**WORKFLOW OBLIGATOIRE :**
1. TOUJOURS commencer par vector_search_tool avec des mots-clés pertinents
2. Si aucun document pertinent (seuil 0.8), utiliser web_search_tool
3. Analyser les résultats et synthétiser une réponse complète
4. Si la question est trop vague et aucun résultat, demander des précisions dans la Final Answer

**STRUCTURE DE RÉPONSE POUR PROCÉDURES :**
📋 Description | 📌 Conditions | 📄 Pièces nécessaires (LISTE COMPLÈTE, pas de "etc.")
🔢 Étapes numérotées | 💰 Coût exact en F CFA | ⏱️ Délais
📅 Validité | 🌐 Modalités (en ligne/sur place avec coordonnées)
**Sources** : Toujours citer les URLs

**TON :** Amical, accessible (tutoiement), émojis 😊, quand t'on te remercie du reponds aussi de facon amicale sans rien ajouter d'autre sinon proposer a l'utilisateur s'il a d'autres question

Tu as accès à ces outils :"""
    
    agent_kwargs = {
        "prefix": agent_system_prompt,
        "suffix": """Commence maintenant !

Question: {input}
Thought: {agent_scratchpad}""",
        "format_instructions": """Utilise EXACTEMENT ce format ReAct (respecte chaque mot-clé):

Question: la question posée
Thought: je dois rechercher dans la base de connaissances d'abord
Action: vector_search_tool
Action Input: "mots-clés de recherche"
Observation: résultat de la recherche
... (répète Thought/Action/Observation si besoin d'utiliser web_search_tool)
Thought: J'ai maintenant toutes les informations nécessaires pour répondre
Final Answer: [Ta réponse complète structurée ici]

⚠️ IMPORTANT: Tu DOIS commencer ta réponse finale par exactement "Final Answer:" suivi de ta réponse formatée."""
    }
    
    # Fonction de gestion personnalisée des erreurs de parsing
    def handle_parsing_error(error) -> str:
        """Extrait la réponse de l'agent même si le format ReAct n'est pas parfait"""
        print(f"  Erreur de parsing détectée, tentative de récupération...")
        error_str = str(error)
        
        # Chercher la réponse générée dans l'erreur
        if "Could not parse LLM output:" in error_str:
            # Extraire le texte après "Could not parse LLM output: `"
            try:
                start_idx = error_str.find("Could not parse LLM output: `") + len("Could not parse LLM output: `")
                end_idx = error_str.rfind("`")
                if start_idx > 0 and end_idx > start_idx:
                    response = error_str[start_idx:end_idx]
                    print(f" Réponse extraite avec succès ({len(response)} caractères)")
                    return f"Final Answer: {response}"
            except Exception as e:
                print(f" Échec de l'extraction: {e}")
        
        return "Final Answer: Je n'ai pas pu générer une réponse correctement formatée. Peux-tu reformuler ta question ?"
    
    # Créer l'agent avec initialize_agent + prompt personnalisé
    agent_executor = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=5,  
        handle_parsing_errors=handle_parsing_error, 
        agent_kwargs=agent_kwargs,
        early_stopping_method="generate",  # forcer une réponse même si max_iterations atteint
        return_intermediate_steps=True  # important pour extraire les sources
    )
    
    try:
        print(f" Exécution de l'agent avec question: '{question[:50]}...'")
        
        # construire le contexte conversationnel pour les questions de suivi
        conversation_context = ""
        if len(user_messages) > 1:
            # Il y a des messages précédents - construire le contexte
            print(f" Détection de {len(user_messages)} messages utilisateur - contexte conversationnel activé")
            conversation_context = "\n\n**CONTEXTE DE LA CONVERSATION :**\n"
            for i, msg in enumerate(user_messages[:-1], 1):  
                conversation_context += f"Message {i}: {msg.content}\n"
            conversation_context += f"\nQuestion actuelle (suite de la conversation) : {question}\n"
            
            # enrichir la question avec le contexte
            enriched_question = f"{conversation_context}\nRéponds à la question actuelle en tenant compte du contexte de la conversation."
        else:
            print(" Premier message - pas de contexte conversationnel")
            enriched_question = question
        
        # exécuter l'agent avec invoke (méthode recommandée)
        result = agent_executor.invoke({"input": enriched_question})
        
        # Extraire la réponse (invoke retourne un dict avec 'output')
        answer = result.get("output", "") if isinstance(result, dict) else str(result)
        
        # Extraire les sources des intermediate_steps (outils appelés par l'agent)
        sources = []
        intermediate_steps = result.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            # Chaque step est un tuple (AgentAction, observation)
            if len(step) >= 2:
                action, observation = step[0], step[1]
                
                # Si l'observation est un dict avec des sources
                if isinstance(observation, dict):
                    tool_sources = observation.get("sources", [])
                    if tool_sources:
                        sources.extend(tool_sources)
        
        print(f"✅ Agent terminé - Réponse: {len(answer)} caractères, Sources: {len(sources)}")
        
        # créer un AIMessage avec la réponse ET les sources en metadata
        ai_message = AIMessage(
            content=answer,
            additional_kwargs={"sources": sources}  # Stocker les sources dans les metadata
        )
        
        # Retourner l'état mis à jour avec le nouveau message
        return {"messages": [ai_message]}
        
    except Exception as e:
        print(f" Erreur dans l'agent: {str(e)}")
        import traceback
        traceback.print_exc()
        # en cas d'erreur
        error_message = AIMessage(content=f"Erreur dans l'agent: {str(e)}")
        return {"messages": [error_message]}
