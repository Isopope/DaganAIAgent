"""
Reranker pour améliorer la pertinence des documents récupérés
Utilise GPT-4o-mini pour évaluer la pertinence sémantique réelle
"""

import os
from typing import List, Dict
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RERANK_TOP_K = 5  # Nombre de documents à garder après reranking


def rerank_documents(question: str, documents: List[Dict], top_k: int = RERANK_TOP_K) -> List[Dict]:
    """
    Rerank les documents en utilisant un LLM pour évaluer la pertinence sémantique
    
    Args:
        question: Question de l'utilisateur
        documents: Liste de documents avec {content, url, similarity_score, ...}
        top_k: Nombre de documents à garder après reranking
        
    Returns:
        Liste des documents rerankés (top_k meilleurs)
    """
    
    if not documents or len(documents) == 0:
        return []
    
    # Si on a moins de documents que top_k, pas besoin de reranker
    if len(documents) <= top_k:
        print(f"Reranking skippé : seulement {len(documents)} documents (≤ {top_k})")
        return documents
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        print(f"Reranking de {len(documents)} documents pour ne garder que les {top_k} meilleurs...")
        
        # Préparer le prompt de reranking
        docs_text = ""
        for i, doc in enumerate(documents):
            content = doc.get("content", "")[:500]  # Limiter à 500 caractères
            docs_text += f"\n[DOC {i+1}]\n{content}\n"
        
        rerank_prompt = f"""Tu es un expert en évaluation de pertinence de documents pour les procédures administratives togolaises.

**Question de l'utilisateur :**
{question}

**Documents candidats :**
{docs_text}

**Ta tâche :**
Évalue la pertinence de chaque document par rapport à la question. Pour chaque document, donne un score de 0 à 10 :
- 10 = Parfaitement pertinent, répond directement à la question
- 7-9 = Très pertinent, contient des informations importantes
- 4-6 = Moyennement pertinent, contient des informations générales
- 1-3 = Peu pertinent, informations tangentielles
- 0 = Non pertinent

**Réponds UNIQUEMENT avec un JSON valide au format :**
{{"rankings": [{{"doc_id": 1, "score": 10, "reason": "..."}}]}}

Ne réponds qu'avec le JSON, rien d'autre."""

        # Appeler GPT-4o-mini pour le reranking
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert en reranking de documents. Tu réponds uniquement avec du JSON valide."},
                {"role": "user", "content": rerank_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # parser la réponse
        import json
        rankings = json.loads(response.choices[0].message.content)
        
        # créer un mapping doc_id → score
        scores = {}
        for rank in rankings.get("rankings", []):
            doc_id = rank.get("doc_id")
            score = rank.get("score", 0)
            if doc_id:
                scores[doc_id - 1] = score  # -1 car doc_id commence à 1
        
        # ajouter le rerank_score aux documents
        for i, doc in enumerate(documents):
            doc["rerank_score"] = scores.get(i, 0)
        
        # on trie par rerank_score décroissant
        reranked = sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        # on garde seulement les top_k
        final_docs = reranked[:top_k]
        
        print(f" Reranking terminé : {len(final_docs)} documents conservés")
        for i, doc in enumerate(final_docs[:3], 1):  # Afficher les 3 meilleurs
            print(f"  {i}. Score: {doc.get('rerank_score', 0)}/10 (similarity: {doc.get('similarity_score', 0):.3f})")
        
        return final_docs
        
    except Exception as e:
        print(f"Erreur lors du reranking: {e}")
        print(f"   Fallback: retour des {top_k} premiers documents sans reranking")
        # Fallback : retourner les top_k premiers documents triés par similarity
        return documents[:top_k]


def rerank_web_results(question: str, web_results: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    Rerank spécifique pour les résultats web de Tavily
    Prend en compte reliability_score et is_official en plus du contenu
    
    Args:
        question: Question de l'utilisateur
        web_results: Liste de résultats web avec {content, url, title, reliability_score, is_official}
        top_k: Nombre de résultats à garder
        
    Returns:
        Liste des résultats rerankés
    """
    
    if not web_results or len(web_results) == 0:
        return []
    
    # si on a moins de résultats que top_k, pas besoin de reranker
    if len(web_results) <= top_k:
        print(f"Reranking web skippé : seulement {len(web_results)} résultats (≤ {top_k})")
        return web_results
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        print(f" Reranking de {len(web_results)} résultats web pour ne garder que les {top_k} meilleurs...")
        
        # preparer le prompt de reranking pour résultats web
        results_text = ""
        for i, result in enumerate(web_results):
            title = result.get("title", "Sans titre")
            content = result.get("content", "")[:400]
            url = result.get("url", "")
            is_official = " OFFICIEL" if result.get("is_official", False) else " Non officiel"
            reliability = result.get("reliability_score", 0.5)
            
            results_text += f"\n[RESULT {i+1}] {is_official} (Fiabilité: {reliability:.2f})\nTitre: {title}\nURL: {url}\nContenu: {content}\n"
        
        rerank_prompt = f"""Tu es un expert en évaluation de pertinence de sources web pour les procédures administratives togolaises.

**Question de l'utilisateur :**
{question}

**Résultats web candidats :**
{results_text}

**Critères d'évaluation :**
1. Pertinence du contenu par rapport à la question (poids: 40%)
2. Source officielle (.gouv.tg) vs non-officielle (poids: 30%)
3. Score de fiabilité Tavily (poids: 20%)
4. Qualité et précision des informations (poids: 10%)

**Ta tâche :**
Évalue chaque résultat et donne un score de 0 à 10. Privilégie FORTEMENT les sources officielles.

**Réponds UNIQUEMENT avec un JSON valide au format :**
{{"rankings": [{{"doc_id": 1, "score": 10, "reason": "..."}}]}}"""

        # Appeler GPT-4o-mini pour le reranking
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert en reranking de sources web. Tu réponds uniquement avec du JSON valide."},
                {"role": "user", "content": rerank_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parser la réponse
        import json
        rankings = json.loads(response.choices[0].message.content)
        
        # Créer un mapping doc_id → score
        scores = {}
        for rank in rankings.get("rankings", []):
            doc_id = rank.get("doc_id")
            score = rank.get("score", 0)
            if doc_id:
                scores[doc_id - 1] = score
        
        # Ajouter le rerank_score aux résultats
        for i, result in enumerate(web_results):
            result["rerank_score"] = scores.get(i, 0)
        
        # Trier par rerank_score décroissant
        reranked = sorted(web_results, key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        # Garder seulement les top_k
        final_results = reranked[:top_k]
        
        print(f" Reranking web terminé : {len(final_results)} résultats conservés")
        for i, result in enumerate(final_results[:3], 1):
            is_official = "🏛️" if result.get("is_official") else "🌐"
            print(f"  {i}. {is_official} Score: {result.get('rerank_score', 0)}/10 - {result.get('title', 'Sans titre')[:50]}")
        
        return final_results
        
    except Exception as e:
        print(f" Erreur lors du reranking web: {e}")
        print(f"   Fallback: retour des {top_k} premiers résultats sans reranking")
        # Fallback : prioriser les sources officielles
        web_results.sort(key=lambda x: (x.get("is_official", False), x.get("reliability_score", 0)), reverse=True)
        return web_results[:top_k]
