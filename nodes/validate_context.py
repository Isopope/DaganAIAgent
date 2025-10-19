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
    validation_prompt = f"""Tu es un système de validation pour un assistant togolais sur les procédures administratives et services publics.

Détermine si cette question concerne les procédures administratives, documents officiels, ou services publics au Togo.

Question: {question}

**Sujets VALIDES** (réponds "oui") - Domaines couverts:

📚 **Éducation & Formation**
- Inscription scolaire, bourses d'études, diplômes, équivalences
- Formation professionnelle, apprentissage

💼 **Emploi & Sécurité sociale**
- Recherche d'emploi, contrats de travail, droits des travailleurs
- Sécurité sociale, retraite, allocations

📄 **Papiers & Citoyenneté**
- Documents d'identité (passeport, carte d'identité, acte de naissance, visa)
- Nationalité, naturalisation, état civil
- Mariage, divorce, adoption

💰 **Fiscalité, Foncier & Douanes**
- Impôts, taxes, déclarations fiscales
- Propriété foncière, cadastre, permis de construire
- Procédures douanières, import/export

🌾 **Agriculture, Élevage & Industrie**
- Subventions agricoles, certifications
- Permis d'exploitation, normes industrielles
- Création et gestion d'entreprise

🏥 **Santé & Protection sociale**
- Accès aux soins, assurance maladie
- Aide sociale, allocations familiales
- Hygiène et santé publique

📡 **Télécommunication, Communication et Culture**
- Services télécom, internet
- Médias, presse, liberté d'expression
- Patrimoine culturel, événements culturels

🏘️ **Habitat & Transport**
- Logement social, aide au logement
- Permis de conduire, immatriculation de véhicules
- Transport public, infrastructures

⚖️ **Justice**
- Procédures judiciaires, tribunaux
- Droits et obligations juridiques
- Médiation, arbitrage

🛡️ **Sécurité & Sûreté**
- Forces de l'ordre, police, gendarmerie
- Protection civile, pompiers
- Sécurité des biens et personnes

**Sujets INVALIDES** (réponds "non"):
- Questions générales sans rapport avec l'administration ou les services publics
- Conversations générales (météo, sport, divertissement)
- Questions techniques hors contexte administratif (programmation, sciences pures)
- Sujets personnels sans lien administratif
- Demandes de conseils médicaux/juridiques personnalisés (orientations uniquement)

Réponds UNIQUEMENT par "oui" si la question est valide, "non" si hors-sujet."""

    try:
        response = llm.invoke(validation_prompt)
        answer = response.content.strip().lower()
        
        is_valid = any(word in answer for word in ["oui", "yes", "valide", "valid"])
        
        if is_valid:
            print(f" Question VALIDE (domaine administratif)")
            return {"is_valid_domain": True}
        else:
            print(f" Question HORS-SUJET (domaine: {answer})")
            
            # Message poli de refus
            refusal_message = """Désolé, je suis **Dagan**, assistant spécialisé dans les **procédures administratives et services publics togolais** 🇹🇬

Je peux t'aider dans ces domaines :

📚 **Éducation & Formation** | � **Emploi & Sécurité sociale**
📄 **Papiers & Citoyenneté** | 💰 **Fiscalité, Foncier & Douanes**
🌾 **Agriculture, Élevage & Industrie** | 🏥 **Santé & Protection sociale**
📡 **Télécommunication, Communication et Culture** | �️ **Habitat & Transport**
⚖️ **Justice** | 🛡️ **Sécurité & Sûreté**

**Exemples de questions que je peux traiter :**
- Comment obtenir un passeport ?
- Quelles sont les étapes pour créer une entreprise ?
- Comment faire une demande de bourse scolaire ?
- Où déclarer mes impôts ?
- Comment obtenir un permis de construire ?

Ta question ne semble pas concerner ces domaines administratifs. Peux-tu reformuler ? 😊"""
            
            return {
                "is_valid_domain": False,
                "domain_check_message": refusal_message
            }
    
    except Exception as e:
        print(f" Erreur validation domaine: {e}")
        # En cas d'erreur, on laisse passer pour éviter de bloquer
        return {"is_valid_domain": True}
