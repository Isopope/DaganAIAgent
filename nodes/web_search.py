"""
Node WEB_SEARCH - Recherche web via Tavily (fallback CRAG) - Sources fiables prioritaires
"""

"""
Node WEB_SEARCH - Web search via Tavily (CRAG fallback) - Reliable sources prioritized
"""
import os
from typing import Dict

from langchain.schema import Document
from tavily import TavilyClient
from trusted_sources import (
    TRUSTED_DOMAINS,
    get_search_query,
    is_trusted_source,
    get_source_reliability_score,
)



def web_search(state:Dict)->Dict:
    """Perform a web search using Tavily based on the transformed query field.
    Activated only if we don't have sufficient relevant document from our vector database after the retrieve node, the decision to use this node is made by the decision node
    Args:
        state (Dict): The current state containing input field transformed_question that would be used for the web search process, 
                      note that it can contain just the reformulated question without context if the context is not available.
    Returns:
        Dict with documents key, containing the list of retrieved web documents.

    """
    print("Web Search node : recherche web via Tavily")
    # Utiliser la question transformée si disponible, sinon extraire des messages
    question = state.get("transformed_question")
    if not question:
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            question = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            print("---NO QUESTION FOR WEB SEARCH---")
            return {"documents": state.get("documents", [])}
    
    existing_docs = state.get("documents", [])
    
    # Configuration 
    max_results = int(os.getenv("CRAG_WEB_SEARCH_MAX_RESULTS", "3"))
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not tavily_api_key:
        print("---WEB SEARCH ERROR: No API key---")
        return {"documents": existing_docs}
    
    # Client Tavily
    tavily_client = TavilyClient(api_key=tavily_api_key)
    
    try:

        optimized_query = get_search_query(question, priority_domain="service-public.gouv.tg")
        
        print(f"---SEARCHING WEB (sources officielles): {question[:50]}...---")

        search_response = tavily_client.search(
            query=optimized_query,
            max_results=max_results,
            search_depth="advanced",
            country="togo",
            include_domains=TRUSTED_DOMAINS[:5] 
        )
        results = search_response.get("results", [])
        
        web_docs = []
        for result in results:
            content = result.get("content", "")
            url = result.get("url", "Unknown URL")
            
            if content and is_trusted_source(url):
                # Calculer le score de fiabilité
                reliability_score = get_source_reliability_score(url)
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "url": url,
                        "source": "tavily_web_search",
                        "reliability_score": reliability_score,
                        "is_official": True
                    }
                )
                web_docs.append(doc)
            elif content:
                # Garder les sources non officielles avec score bas
                doc = Document(
                    page_content=content,
                    metadata={
                        "url": url,
                        "source": "tavily_web_search",
                        "reliability_score": 0.3,
                        "is_official": False
                    }
                )
                web_docs.append(doc)
        
        # Trier par score de fiabilité (sources officielles en premier)
        web_docs.sort(key=lambda doc: doc.metadata.get("reliability_score", 0), reverse=True)
        
        print(f"---FOUND {len(web_docs)} WEB RESULTS ({sum(1 for d in web_docs if d.metadata.get('is_official'))} sources officielles)---")
        
        # Ajouter aux documents existants (pour contexte de génération)
        all_documents = existing_docs + web_docs
        
        return {"documents": all_documents}
    
    except Exception as e:
        print(f"---WEB SEARCH ERROR: {str(e)}---")
        # En cas d'erreur, garder les documents existants
        return {"documents": existing_docs}

