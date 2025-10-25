"""
Node ROUTE_QUESTION - Routeur intelligent entre conversations casual et questions administratives
"""

import os
from typing import Dict, Literal
from openai import OpenAI

def route_question(state: Dict) -> Dict:
    """
    Route la question vers casual_convo ou agent_rag selon le type de question.

    Args:
        state (Dict): État contenant les messages

    Returns:
        Dict avec clé "question_type" ("casual" ou "admin")
    """

    # Extraire la dernière question utilisateur
    messages = state.get("messages", [])
    if not messages:
        return {"question_type": "casual"}

    last_message = messages[-1]
    question = last_message.content if hasattr(last_message, 'content') else str(last_message)

    print(f"🔀 Routing question: '{question[:50]}...'")

    # Configuration LLM
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    llm_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    # Prompt de classification
    routing_prompt = f"""Tu es un routeur intelligent pour Dagan, assistant togolais spécialisé dans les procédures administratives.

Classifie cette question en "casual" ou "admin" :

**CASUAL** (réponds "casual") - Conversations informelles :
- Salutations : "bonjour", "salut", "ça va ?", "comment allez-vous ?"
- Questions générales : météo, actualités, sport, divertissement
- Conversation personnelle : "tu es qui ?", "que fais-tu ?", "parle-moi de toi"
- Questions fermées simples : "oui", "non", "peut-être", réponses courtes
- Questions de politesse : "merci", "au revoir", "à bientôt"

**ADMIN** (réponds "admin") - Questions administratives togolaises :
- Documents officiels : passeport, carte d'identité, acte de naissance
- Éducation : inscription scolaire, bourses, diplômes
- Emploi : recherche d'emploi, sécurité sociale, retraite
- Santé : assurance maladie, soins médicaux
- Fiscalité : impôts, taxes, déclarations
- Entreprises : création société, permis d'exploitation
- Logement : permis construire, propriété foncière
- Transport : permis conduire, immatriculation véhicule
- Justice : procédures judiciaires, tribunaux
- Télécommunications : abonnement internet, téléphone
- Agriculture : subventions, certifications
- Sécurité : police, gendarmerie, protection civile

Question : "{question}"

Réponds UNIQUEMENT par "casual" ou "admin"."""

    try:
        response = client.chat.completions.create(
            model=llm_model,
            temperature=0,
            messages=[{"role": "user", "content": routing_prompt}]
        )

        result = response.choices[0].message.content.strip().lower()

        if "casual" in result:
            print("🎯 Routed to: CASUAL_CONVO")
            return {"question_type": "casual"}
        else:
            print("🎯 Routed to: AGENT_RAG")
            return {"question_type": "admin"}

    except Exception as e:
        print(f"⚠️ Erreur routing, défaut vers admin: {e}")
        return {"question_type": "admin"}