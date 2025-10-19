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
            include_favicon=True,
            include_answer="basic",
            include_raw_content="markdown",
            chunks_per_source=2,
            include_domains=TRUSTED_DOMAINS[:5]
        )
        results = search_response.get("results", [])
        
        web_docs = []
        
        # Ajouter la réponse globale LLM si disponible
        global_answer = search_response.get("answer")
        if global_answer:
            doc = Document(
                page_content=global_answer,
                metadata={
                    "url": "",
                    "favicon": "",
                    "source": "tavily_web_search_global_answer",
                    "reliability_score": 0.8,  # Score élevé pour la réponse globale
                    "is_official": False
                }
            )
            web_docs.append(doc)
        
        for result in results:
            content = result.get("content", "")
            url = result.get("url", "")
            favicon = result.get("favicon", "")
            
            if not content or not url:
                continue
            
            is_official = is_trusted_source(url)
            reliability_score = get_source_reliability_score(url) if is_official else 0.3
            
            # Créer les métadonnées avec url et favicon
            doc = Document(
                page_content=content,
                metadata={
                    "url": url,
                    "favicon": favicon,
                    "source": "tavily_web_search",
                    "reliability_score": reliability_score,
                    "is_official": is_official
                }
            )
            web_docs.append(doc)
        
        # Trier par score de fiabilité (sources officielles en premier)
        web_docs.sort(key=lambda doc: doc.metadata.get("reliability_score", 0), reverse=True)
        
        print(f"---FOUND {len(web_docs)} WEB RESULTS ({sum(1 for d in web_docs if d.metadata.get('is_official'))} sources officielles)---")
        if global_answer:
            print(f"---GLOBAL ANSWER INCLUDED: {global_answer[:100]}...---")
        
        # Ajouter aux documents existants (pour contexte de génération)
        all_documents = existing_docs + web_docs
        
        return {"documents": all_documents}
    
    except Exception as e:
        print(f"---WEB SEARCH ERROR: {str(e)}---")
        # En cas d'erreur, garder les documents existants
        return {"documents": existing_docs}

