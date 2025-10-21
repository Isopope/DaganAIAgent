"""
Tool pour recherche web avec Tavily + reranking LLM
Remplace le node web_search avec wrapping en LangChain tool
"""

import os
from typing import List, Dict, Any
from langchain.tools import tool
from tavily import TavilyClient
from tools.reranker import rerank_web_results


# Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def calculate_reliability_score(url: str, trusted_sources: List[str]) -> float:
    """
    Calcule un score de fiabilité basé sur la source
    
    Args:
        url: URL de la source
        trusted_sources: Liste des domaines de confiance
        
    Returns:
        Score entre 0 et 1 (1 = source officielle)
    """
    # Sources officielles togolaises de confiance
    official_sources = [
        "gouv.tg",
        "republiquetogolaise.com",
        "presidence.gouv.tg",
        "assemblee-nationale.tg",
        "primature.gouv.tg"
    ]
    
    # Vérifier si l'URL contient un domaine officiel
    for source in official_sources:
        if source in url.lower():
            return 1.0
    
    # Sources internationales fiables
    reliable_sources = [
        "wikipedia.org",
        "un.org",
        "afdb.org",
        "worldbank.org"
    ]
    
    for source in reliable_sources:
        if source in url.lower():
            return 0.8
    
    # Par défaut, score moyen
    return 0.5


@tool
def web_search_tool(query: str) -> dict:
    """
    Recherche web avec Tavily pour trouver des informations récentes sur les procédures administratives togolaises.
    Optimisé pour le Togo avec scoring de fiabilité des sources.
    
    Args:
        query: La requête de recherche
        
    Returns:
        Dictionnaire structuré avec résultats et sources complètes
    """
    
    try:
        # 1. Initialize Tavily client
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # 2. Perform advanced search with Togo focus (augmenter max_results pour le reranking)
        search_results = tavily_client.search(
            query=query,
            max_results=10,  # Augmenté de 3 à 10 pour avoir plus de candidats au reranking
            search_depth="advanced",
            country="togo",
            include_favicon=True,
            #include_answer="advanced",
            include_raw_content="text",
            chunks_per_source=2,
            include_domains=[]
        )
        
        # 3. Process results and calculate reliability scores
        processed_results = []
        
        for result in search_results.get("results", []):
            url = result.get("url", "")
            content = result.get("content", "")
            
            # Skip empty results
            if not content or not url:
                continue
            
            # Calculate reliability score
            reliability_score = calculate_reliability_score(url, [])
            is_official = reliability_score >= 0.9
            
            # Get favicon if available (from Tavily crawl endpoint)
            # Note: favicon n'est pas toujours disponible dans search, seulement dans crawl
            favicon = ""
            
            processed_results.append({
                "content": content,
                "url": url,
                "favicon": favicon,
                "is_official": is_official,
                "reliability_score": round(reliability_score, 2),
                "title": result.get("title", "")
            })
        
        # 4. RERANKING avec LLM pour améliorer la pertinence et prioriser sources officielles
        if len(processed_results) > 5:
            print(f"Reranking de {len(processed_results)} résultats web...")
            processed_results = rerank_web_results(query, processed_results, top_k=5)
        else:
            # Si peu de résultats, juste trier par reliability score
            processed_results.sort(key=lambda x: x["reliability_score"], reverse=True)
        
        # 5. Return structured dict with sources
        if processed_results:
            return {
                "status": "success",
                "query": query,
                "result_count": len(processed_results),
                "answer": search_results.get("answer", ""),
                "reranked": True if len(processed_results) > 0 and "rerank_score" in processed_results[0] else False,
                "sources": processed_results,  # Liste complète des sources avec URLs (reranked)
                "summary": f" Trouvé {len(processed_results)} résultat(s) web pertinent(s) pour '{query}' (reranked)"
            }
        else:
            return {
                "status": "no_results",
                "query": query,
                "result_count": 0,
                "sources": [],
                "summary": f" Aucun résultat web trouvé pour '{query}'"
            }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "sources": [],
            "summary": f" Erreur lors de la recherche web: {str(e)}"
        }

