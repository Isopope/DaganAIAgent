"""
Node AGENT_RAG - Agent ReAct avec tools (vector_search + web_search)
Remplace l'ancien workflow CRAG linéaire par un agent intelligent
Utilise initialize_agent (stable et compatible)
"""

import os
import json
import requests
import datetime
from typing import Dict, List, Optional, Any
from langchain.llms.base import LLM
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks.manager import CallbackManagerForLLMRun
from openai import OpenAI

# Import tools
from tools import vector_search_tool, web_search_tool, web_crawl_tool, web_search_tool_resident, web_search_tool_diaspora

# Import du prompt centralisé
from prompt import SYSTEM_PROMPT_TEMPLATE


def send_prompt_to_n8n(question: str, user_location: str, thread_id: Optional[str] = None) -> None:
    """
    Envoie le prompt utilisateur à n8n pour l'enregistrer dans Excel.
    N'attend pas de réponse - fire and forget asynchrone.
    
    Args:
        question: Le prompt utilisateur
        user_location: "resident" ou "diaspora"
        thread_id: ID de la conversation (optionnel)
    """
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        # Webhook n8n non configuré - rien à faire, c'est OK
        return
    
    try:
        payload = {
            "question": question,
            "user_location": user_location,
            "thread_id": thread_id or "unknown",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Envoyer le webhook sans attendre de réponse
        # timeout court (2 secondes) pour éviter de bloquer Dagan
        requests.post(webhook_url, json=payload, timeout=2)
        print(f"  ✓ Prompt envoyé à n8n ")
        
    except requests.Timeout:
        # N8n trop lent - c'est OK, on ignore et on continue
        print(f"  ⚠️ n8n webhook timeout (2s)")
        pass
    except Exception as e:
        # Erreur réseau ou autre - c'est OK, on ignore silencieusement
        print(f"  ⚠️ Erreur n8n webhook: {type(e).__name__}")
        pass


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


def reformulate_query_with_location(question: str, user_location: str) -> str:
    """
    Reformule la question utilisateur en 2-5 mots-clés optimisés en tenant compte de la localisation.
    
    **RESIDENT** (au Togo):
    - Ajouter "Togo" ou "site:.gouv.tg"
    - Focus sur procédures sur place
    - Ex: "Comment obtenir une carte?" → "carte nationale biométrique Togo"
    
    **DIASPORA** (à l'étranger):
    - Ajouter le pays de résidence détecté + "consulat" ou "diaspora"
    - Focus sur services consulaires
    - Ex: "Renouveler mon passeport" en France → "passeport renouvellement consulat Togo France"
    
    Args:
        question: Question brute de l'utilisateur
        user_location: "resident" ou "diaspora"
    
    Returns:
        Requête optimisée en 2-5 mots-clés
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"⚠️ Reformulation fallback: pas d'API key")
        return question
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Prompt adapté selon le contexte
        if user_location == "diaspora":
            location_context = """L'utilisateur est en DIASPORA (hors du Togo, à l'étranger).
- Détecte le pays mentionné (France, Belgique, Canada, États-Unis, etc.)
- Ajoute ce pays + "consulat" ou "diaspora" dans les mots-clés
- Focus: services consulaires, ambassades, procédures internationales"""
        else:
            location_context = """L'utilisateur est RESIDENT (AU TOGO).
- Ajoute "Togo" ou "site:.gouv.tg" systématiquement
- Focus: procédures sur place, services publics locaux"""
        
        reformulation_prompt = f"""Tu es un optimiseur de requête pour Tavily Search.
Reformule cette question en mots-clés optimisés (2-5 mots MAX).

{location_context}

**RÈGLES**:
1. 2-5 mots-clés MAXIMUM
2. Mots importants EN PREMIER (document, action, localisation)
3. Ordre de priorité: [action/document] [détails] [localisation]
4. Pas de ponctuation ni articles

**EXEMPLES**:
- Resident: "Comment obtenir une carte d'identité?" → "carte nationale biométrique Togo"
- Resident: "Procédure pour le passeport?" → "passeport ordinaire coût délai site:.gouv.tg"
- Diaspora (France): "Renouveler mon passeport" → "passeport renouvellement consulat Togo France"
- Diaspora (USA): "Je veux un acte de naissance" → "acte naissance diaspora consulat Togo États-Unis"

Question: "{question}"

Réponds UNIQUEMENT par les mots-clés reformulés (rien d'autre)."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[{"role": "user", "content": reformulation_prompt}],
            max_tokens=50
        )
        
        reformulated = response.choices[0].message.content.strip()
        print(f"  🔄 Reformulation: '{question[:40]}...' → '{reformulated}'")
        
        return reformulated
    
    except Exception as e:
        print(f"⚠️ Reformulation LLM failed: {e}, fallback: {question}")
        return question


def re_classify_location_with_context(messages: List, current_user_location: str) -> str:
    """
    RE-CLASSIFIE la localisation en analysant TOUTE la conversation.
    Permet à l'utilisateur d'itérer en changeant de contexte au fil de la discussion.
    
    Logique :
    - Analyse le dernier message utilisateur ET tout l'historique
    - Si mention d'un pays étranger → "diaspora"
    - Si retour à Togo ou pas de mention → garde le contexte actuel ou revient à "resident"
    - Permet des itérations : Q1 "passeport" (resident) → Q2 "et en France?" (diaspora) → Q3 "délais?" (reste diaspora)
    
    Args:
        messages: Liste de tous les messages
        current_user_location: Localisation actuelle ("resident" ou "diaspora")
    
    Returns:
        Nouvelle localisation reclassifiée
    """
    
    from langchain_core.messages import HumanMessage as LangchainHumanMessage
    
    # Extraire tous les messages utilisateur
    user_messages = [msg for msg in messages if isinstance(msg, LangchainHumanMessage)]
    
    if not user_messages:
        return current_user_location
    
    # Combiner tous les messages utilisateur pour analyser le contexte complet
    full_conversation = " ".join([msg.content for msg in user_messages])
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"⚠️ Re-classification fallback: pas d'API key")
        return current_user_location
    
    try:
        client = OpenAI(api_key=api_key)
        
        reclassification_prompt = f"""Tu es un classificateur de contexte géographique pour Dagan.
Analyse TOUTE la conversation pour déterminer si l'utilisateur est ACTUELLEMENT:
- "resident" (habite au Togo) 
- "diaspora" (habite à l'étranger)

**RÈGLES DE RE-CLASSIFICATION** :
1. Si l'utilisateur mentionne EXPLICITEMENT un pays étranger (France, Belgique, Canada, USA, etc.) → "diaspora"
2. Si l'utilisateur dit "et en France?", "pour quelqu'un vivant en..." → bascule à "diaspora"
3. Si l'utilisateur dit "en Togo", "ici", "sur place" → retour à "resident"
4. Si la DERNIÈRE question ne mentionne pas de localisation, ASSUME qu'on continue avec la DERNIÈRE localisation mentionnée
   - Ex: Q1 "passeport resident" → Q2 "et en France?" → Q3 "délais?" = reste diaspora
5. Contexte actuel: {current_user_location}

**CONVERSATION** :
{full_conversation}

Réponds UNIQUEMENT par "resident" ou "diaspora"."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[{"role": "user", "content": reclassification_prompt}],
            max_tokens=20
        )
        
        result = response.choices[0].message.content.strip().lower()
        
        if "diaspora" in result:
            new_location = "diaspora"
        else:
            new_location = "resident"
        
        if new_location != current_user_location:
            print(f"  🔄 Re-classification: {current_user_location.upper()} → {new_location.upper()}")
        else:
            print(f"  ✓ Contexte confirmé: {new_location.upper()}")
        
        return new_location
    
    except Exception as e:
        print(f"⚠️ Re-classification LLM failed: {e}, garde contexte actuel: {current_user_location}")
        return current_user_location


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
    
    # ÉTAPE 1: Re-classifier la localisation en fonction du contexte conversationnel complet
    # Cela permet à l'utilisateur d'itérer : Q1 "resident" → Q2 "et en France?" → Q3 "délais?" (reste diaspora)
    current_user_location = state.get("user_location", "resident")
    user_location = re_classify_location_with_context(messages, current_user_location)
    print(f" Localisation re-classifiée: {user_location}")
    
    # Envoyer le prompt à n8n pour enregistrement
    thread_id = state.get("thread_id", None)
    send_prompt_to_n8n(question, user_location, thread_id)
    
    # ÉTAPE 2: Reformuler la question en tenant compte de la localisation reclassifiée
    reformulated_question = reformulate_query_with_location(question, user_location)
    print(f" Question reformulée: '{reformulated_question}'")
    
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
    
    # Sélectionner les tools selon la localisation RE-CLASSIFIÉE
    # Le web_search_tool est différent selon resident/diaspora (include_domains différents)
    # Le web_crawl_tool reste commun
    if user_location == "diaspora":
        tools = [
            vector_search_tool,
            web_search_tool_diaspora,  # Pour diaspora : include consulats + .gouv.tg
            web_crawl_tool
        ]
        location_context = "\n\n⚠️ **CONTEXTE UTILISATEUR**: L'utilisateur est en diaspora (à l'étranger). Utilise web_search_tool_diaspora qui inclut les domaines des ambassades/consulats."
    else:
        tools = [
            vector_search_tool,
            web_search_tool_resident,  # Pour resident : priorité .gouv.tg local
            web_crawl_tool
        ]
        location_context = "\n\n⚠️ **CONTEXTE UTILISATEUR**: L'utilisateur est resident au Togo. Utilise web_search_tool_resident qui inclut .gouv.tg."
    
    print(f"Tools disponibles: {[t.name for t in tools]}")
    
    # Adapter le prompt système pour l'agent ReAct
    # Le prompt SYSTEM_PROMPT_TEMPLATE est conçu pour un RAG classique avec contexte
    # On l'adapte pour un agent qui utilise des tools
    agent_system_prompt = """Tu es **Dagan**, assistant virtuel pour les citoyens togolais

**TA MISSION :**
Aider les citoyens avec des informations précises sur les procédures administratives et services publics togolais.

**⚠️ CONTEXTE DE LOCALISATION - RÈGLE CRITIQUE :**
La question peut être posée par :
- **RÉSIDENT** : Personne vivant au Togo → Procédures sur place, coordination locale
- **DIASPORA** : Personne vivant à l'ÉTRANGER → Procédures via consulat/ambassade

Tu reçois le contexte dans la question et dans les outils utilisés. 
**OBLIGATION ABSOLUE** : Adapter ENTIÈREMENT ta réponse selon le contexte :
- **RÉSIDENT** : "Au Togo, vous devez vous présenter à..."
- **DIASPORA** : "En tant que citoyen à l'étranger, vous contactez le consulat/ambassade de..."

**SI CHANGEMENT DE CONTEXTE DÉTECTÉ** (ex: "et pour quelqu'un en France?" après une question resident):
1. Tu DOIS reconnaître le changement de contexte
2. Tu DOIS RE-EXÉCUTER COMPLÈTEMENT tous les outils (vector_search → web_search → web_crawl)
   - Les sources pour la diaspora sont DIFFÉRENTES des sources resident
   - Les procédures sont DIFFÉRENTES (via consulat vs sur place)
3. Tu ne dois JAMAIS réutiliser les résultats du contexte précédent
4. Ta réponse DOIT être entièrement adaptée au nouveau contexte

**RÈGLE ABSOLUE - Priorité des sources :**
1. **BASE DE CONNAISSANCES** (via vector_search_tool) = SOURCE PRINCIPALE
2. **Recherche web** (via web_search_tool_resident ou web_search_tool_diaspora selon le contexte) = Trouver des URLs .gouv.tg pertinentes
3. **Crawling web** (via web_crawl_tool sur URLs trouvées) = Extraire le contenu complet
4. **JAMAIS** d'informations sans vérification
5. **NE JAMAIS** inventer des informations administratives

**GESTION DES QUESTIONS VAGUES :**
Si la question manque de précisions (ex: "quelles pièces?", "comment faire?"), tu DOIS:
- Identifier le contexte probable (passeport, carte d'identité, etc.)
- Si possible, fournir une réponse générale pour les cas les plus courants
- **DEMANDER DES CLARIFICATIONS** si vraiment nécessaire pour donner une réponse précise
- Suggérer de préciser pour une réponse plus adaptée
- Tu dois etre rigoureux lorsque tu croises les informations entre les différentes sources par exemple eviter de donner le prix de la creation d'une entreprise dont la demande est faite par une personne physique et le prix d'une demande faite par une personne morale.

**✅ RÉFORMULATION DES RECHERCHES (OBLIGATOIRE) :**
Transformer TOUJOURS la question en requête optimisée avec 2 à 4 mots-clés MAX
- Ajouter systématiquement : "Togo" ou "site:.gouv.tg" pour cibler les sources officielles
- Privilégier :
  • Noms d'administration (ANID, SGAE, DGDN, Ministère...)
  • Nom exact du document ou procédure
  • Mots-clés réglementaires : "conditions", "pièces", "coût", "délais"

Exemples de reformulation :
  ❌ "Comment obtenir une carte d'identité ?"
  ✅ "carte nationale identité biométrique Togo"
  
  ❌ "Procédure pour le passeport"
  ✅ "passeport ordinaire coût pièces site:.gouv.tg"
  
  ❌ "Renouveler mon permis"
  ✅ "permis conduire renouvellement Togo DGDN"
  
  ❌ "Demande attestation ONG"
  ✅ "attestation reconnaissance ONG site:.gouv.tg"

**WORKFLOW OBLIGATOIRE :**
1. TOUJOURS commencer par vector_search_tool avec mots-clés optimisés (2-4 mots MAX + Togo/site:.gouv.tg)
2. ⚠️ VÉRIFIER LA PERTINENCE des résultats vector_search :
   - Si les résultats semblent hors-sujet ou génériques (pas spécifiques à la question)
   - Ou si la similarité est faible (< 70%)
   - Alors passer à l'étape 3
3. Si vector_search retourne "no_results" ou "no_relevant_documents" :
   - Utiliser web_search_tool_resident ou web_search_tool_diaspora (selon le contexte) pour trouver des URLs .gouv.tg pertinentes
   - Puis utiliser web_crawl_tool sur l'URL la plus pertinente trouvée
   - Si web_search ne trouve rien, passer directement à web_crawl_tool avec une URL connue
4. Analyser les résultats et synthétiser une réponse complète
5. Si aucun résultat pertinent après les outils, DEMANDER DES PRÉCISIONS dans la Final Answer

**CAPACITÉ À POSER DES QUESTIONS :**
Tu as le droit et même le devoir de poser des questions si la demande est ambiguë ou manque de contexte. Par exemple:
- "S'agit-il de... ?"
- "Peux-tu préciser... ?"
- "Quelle est exactement ta situation... ?"
Ces questions doivent être claires et aider l'utilisateur à mieux formuler sa demande.

**STRUCTURE DE RÉPONSE POUR PROCÉDURES :**
Description | Conditions | Pièces nécessaires (LISTE COMPLÈTE, pas de "etc.")
Étapes numérotées | Coût exact en F CFA | Délais
Validité | Modalités (en ligne/sur place avec coordonnées)
**Sources** : Toujours citer les URLs

**TON :** Amical, accessible (tutoiement),emojis, quand t'on te remercie du reponds aussi de facon amicale sans rien ajouter d'autre sinon proposer a l'utilisateur s'il a d'autres question

Tu as accès à ces outils :""" + location_context
    
    agent_kwargs = {
        "prefix": agent_system_prompt,
        "suffix": """Commence maintenant !

Question: {input}
""" + location_context + """

Thought: {agent_scratchpad}""",
        "format_instructions": """Utilise EXACTEMENT ce format ReAct (respecte chaque mot-clé):

Question: la question posée
Thought: Je dois reformuler la question en 2-5 mots-clés optimisés EN TENANT COMPTE DE LA LOCALISATION
Action: vector_search_tool
Action Input: "requête reformulée de 2-5 mots-clés"
Observation: résultat de la recherche
Thought: [Si aucun résultat pertinent] je dois chercher sur le web
Action: web_search_tool_resident OU web_search_tool_diaspora (selon contexte)
Action Input: "requête reformulée optimisée pour Tavily (2-5 mots-clés)"
Observation: URLs trouvées
Thought: je vais crawler l'URL la plus pertinente
Action: web_crawl_tool
Action Input: "https://service-public.gouv.tg/..."
Observation: contenu de la page
Thought: J'ai maintenant toutes les informations nécessaires pour répondre
Final Answer: [Ta réponse complète structurée ici - ADAPTÉE AU CONTEXTE UTILISATEUR (RESIDENT ou DIASPORA)]

⚠️ RÈGLES ABSOLUES À RESPECTER: 
1. TOUJOURS reformuler la question en 2-5 mots-clés AVANT d'appeler les tools
2. Pour RESIDENT: utiliser web_search_tool_resident + inclure "Togo" ou "site:.gouv.tg"
3. Pour DIASPORA: utiliser web_search_tool_diaspora + inclure le pays mentionné + "consulat"
4. Ta RÉPONSE FINALE DOIT ÊTRE ADAPTÉE au contexte:
   - resident → "Au Togo, vous devez vous présenter à..."
   - diaspora → "Contactez le consulat/ambassade de..."
5. SI CHANGEMENT DE CONTEXTE DÉTECTÉ (ex: "et en France?" après resident):
   ⚠️ **TU DOIS RE-EXÉCUTER LES OUTILS COMPLÈTEMENT**
   - Appelle vector_search_tool avec la nouvelle requête
   - Appelle web_search_tool_diaspora (et non resident)
   - Appelle web_crawl_tool sur la meilleure URL diaspora
   - NE RÉUTILISE JAMAIS les résultats du contexte précédent
6. Tu DOIS commencer ta réponse finale par exactement "Final Answer:" suivi de ta réponse formatée"""
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
        print(f" → Requête optimisée pour tools: '{reformulated_question}'")
        
        # construire le contexte conversationnel pour les questions de suivi
        conversation_context = ""
        context_changed = False
        
        if len(user_messages) > 1:
            # Il y a des messages précédents - construire le contexte
            print(f" Détection de {len(user_messages)} messages utilisateur - contexte conversationnel activé")
            conversation_context = "\n\n**CONTEXTE DE LA CONVERSATION :**\n"
            for i, msg in enumerate(user_messages[:-1], 1):  
                conversation_context += f"Message {i}: {msg.content}\n"
            conversation_context += f"\nQuestion actuelle (suite de la conversation) : {question}\n"
            
            # Vérifier si le contexte de localisation a changé (resident → diaspora ou inverse)
            # En comparant le contexte actuel avec le contexte de la question précédente
            if len(user_messages) >= 2:
                # Si la question mentionne un pays étranger (France, Belgique, USA, etc.)
                # ET que le contexte précédent était resident → changement de contexte
                diaspora_keywords = ['france', 'belgique', 'canada', 'usa', 'états-unis', 'suisse', 'allemagne', 'italie', 'espagne', 'pays-bas', 'royaume-uni', 'australie', 'japon', 'singapour']
                if any(keyword in question.lower() for keyword in diaspora_keywords) and user_location == "diaspora":
                    context_changed = True
                    print(f" 🔄 CHANGEMENT DE CONTEXTE DÉTECTÉ : resident → diaspora")
            
            # enrichir la question avec le contexte ET forcer la RE-EXÉCUTION des tools
            if context_changed:
                enriched_question = f"""{conversation_context}

⚠️ **CHANGEMENT DE CONTEXTE DÉTECTÉ** : La question précédente concernait un RESIDENT, 
et la question actuelle concerne la DIASPORA (à l'étranger).

**OBLIGATION** : Tu DOIS RE-EXÉCUTER COMPLÈTEMENT les outils (vector_search → web_search → web_crawl) 
avec les paramètres DIASPORA, car les sources et procédures sont DIFFÉRENTES :
- Resident: procédure sur place au Togo
- Diaspora: procédure via consulat/ambassade

**REQUÊTE OPTIMISÉE POUR TOOLS (DIASPORA)**: {reformulated_question}

Exécute TOUS les outils avec cette nouvelle requête diaspora (ne réutilise PAS les résultats précédents)."""
            else:
                enriched_question = f"{conversation_context}\nRéponds à la question actuelle en tenant compte du contexte de la conversation.\n\n**REQUÊTE OPTIMISÉE POUR TOOLS**: {reformulated_question}"
        else:
            print(" Premier message - pas de contexte conversationnel")
            enriched_question = f"**REQUÊTE OPTIMISÉE POUR TOOLS**: {reformulated_question}"
        
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
        
        print(f"Agent terminé - Réponse: {len(answer)} caractères, Sources: {len(sources)}")
        
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
