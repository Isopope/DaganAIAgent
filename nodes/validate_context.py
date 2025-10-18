"""
Node VALIDATE_CONTEXT - Valide que la question concerne les procédures administratives togolaises
"""

"""
Node VALIDATE_CONTEXT - Validates that the question concerns Togolese administrative procedures
"""

import os
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

def validate_context(state:Dict)->Dict:
    """Validate if the question is about Togolese administrative procedures using the LLM.
    This node checks if the user's question is relevant to administrative procedures in Togo.
    Args:
        state (Dict): The current state containing messages from user
    Returns:
        Dict with key "is_valid_domain" (bool) and "domain_check_message" (str).
    """

    # Extraire la dernière question utilisateur
    messages = state.get("messages", [])
    if not messages:
        return {"is_valid_domain": True}
    
    last_message = messages[-1]
    question = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Configuration LLM
    llm_model = os.getenv("LLM_MODEL", "gpt-4.1-nano")
    
    llm = ChatOpenAI(
        model=llm_model,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Prompt de validation du domaine
    validation_prompt = f"""Tu es un système de validation pour un assistant togolais sur les procédures administratives.

Détermine si cette question concerne les procédures administratives, documents officiels, ou services publics au Togo.

Question: {question}

**Sujets VALIDES** (réponds "oui"):
- Documents officiels (passeport, carte d'identité, acte de naissance, visa, etc.)
- Procédures administratives (mariage, divorce, création d'entreprise, etc.)
- Services publics togolais (impôts, santé, éducation, etc.)
- Droits et obligations citoyens au Togo
- Institutions gouvernementales togolaises

**Sujets INVALIDES** (réponds "non"):
- Questions générales sans rapport avec l'administration
- Conversations générales (météo, sport, actualités non-administratives)
- Questions techniques (programmation, sciences, etc.)
- Sujets personnels sans lien administratif
- Demandes de conseils non-administratifs

Réponds UNIQUEMENT par "oui" si la question est valide, "non" si hors-sujet."""

    try:
        response = llm.invoke(validation_prompt)
        answer = response.content.strip().lower()
        
        is_valid = any(word in answer for word in ["oui", "yes", "valide", "valid"])
        
        if is_valid:
            print(f"✅ Question VALIDE (domaine administratif)")
            return {"is_valid_domain": True}
        else:
            print(f"❌ Question HORS-SUJET (domaine: {answer})")
            
            # Message poli de refus
            refusal_message = """Désolé, je suis **Dagan**, assistant spécialisé dans les **procédures administratives togolaises** 🇹🇬

Je peux t'aider avec :
- 📄 Documents officiels (passeport, carte d'identité, acte de naissance...)
- 🏛️ Procédures administratives (mariage, création d'entreprise...)
- 🏥 Services publics (santé, éducation, impôts...)
- ⚖️ Droits et obligations citoyens

Ta question ne semble pas concerner ces domaines. Peux-tu reformuler avec une question administrative ? 😊"""
            
            return {
                "is_valid_domain": False,
                "domain_check_message": refusal_message
            }
    
    except Exception as e:
        print(f"⚠️ Erreur validation domaine: {e}")
        # En cas d'erreur, on laisse passer pour éviter de bloquer
        return {"is_valid_domain": True}
