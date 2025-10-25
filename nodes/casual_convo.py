"""
Node CASUAL_CONVO - Gestion des conversations informelles et réponses amicales
"""

import os
from typing import Dict
from openai import OpenAI
from langchain_core.messages import AIMessage

def casual_convo(state: Dict) -> Dict:
    """
    Génère une réponse amicale et conversationnelle pour les questions informelles.

    Args:
        state (Dict): État contenant les messages

    Returns:
        Dict avec la réponse ajoutée aux messages
    """

    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="Bonjour ! Je suis Dagan, votre assistant. Comment puis-je vous aider ?")]}

    last_message = messages[-1]
    question = last_message.content if hasattr(last_message, 'content') else str(last_message)

    print(f"💬 Casual conversation: '{question[:50]}...'")

    # Configuration LLM
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Prompt pour réponses casual
    casual_prompt = f"""Tu es Dagan, un assistant IA amical et sympathique spécialisé dans l'aide administrative togolaise.

L'utilisateur te pose une question informelle : "{question}"

Réponds de manière :
- Amicale et sympathique 😊
- Concise mais engageante
- En français
- En gardant le contexte togolais quand approprié
- En invitant à poser des questions administratives si l'occasion se présente

Si c'est une salutation, réponds chaleureusement.
Si c'est une question personnelle sur toi, présente-toi brièvement.
Si c'est une conversation générale, sois engageant mais redirige vers ton domaine d'expertise.

Réponse :"""

    try:
        response = client.chat.completions.create(
            model=llm_model,
            temperature=0.7,  
            max_tokens=150,
            messages=[{"role": "user", "content": casual_prompt}]
        )

        answer = response.choices[0].message.content.strip()

        print(f"💬 Casual response: '{answer[:50]}...'")

        # Ajouter la réponse aux messages
        new_messages = messages + [AIMessage(content=answer)]

        return {"messages": new_messages}

    except Exception as e:
        print(f"⚠️ Erreur casual response: {e}")
        fallback = "Désolé, je n'ai pas bien compris. Je suis Dagan, votre assistant pour les démarches administratives au Togo. Comment puis-je vous aider ?"
        return {"messages": messages + [AIMessage(content=fallback)]}