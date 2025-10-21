# """
# Node TRANSFORM_QUERY - le LLM reformule la question pour recherche web optimisée
# """

# """
# Node TRANSFORM_QUERY - The LLM reformulates the question for optimized web search
# """
# import os
# import logging
# from typing import Dict

# from langchain_openai import ChatOpenAI
# def transform_query(state:Dict)->Dict:
#     """Transform the query for web search using the LLM.
#     rewrite the user question based on the conversational context
#     Args:
#         state (Dict): The current state containing input data that would be used for the transformation process.
#     Returns:
#         Dict with key "messages" containing the transformed query message.
#     """
#     print("Transform node : reformulation de la requete pour une websearch")
#      # extraction message
#     messages= state.get("messages", [])
#     if not messages:
#         print("Aucun message trouvé.")
#         return {}
    
#     last_user_message = messages[-1]
#     original_question= last_user_message.content if hasattr(last_user_message, 'content') else str(last_user_message)
#     # llm configuration
#     llm_model=os.getenv("LLM_MODEL","gpt-4.1-nano")
#     temperature=float(os.getenv("LLM_TEMPERATURE_GRADING", "0"))
#     llm= ChatOpenAI(
#         model=llm_model,
#         temperature=temperature,
#         openai_api_key=os.getenv("OPENAI_API_KEY")
#     )

#     #contexte de conversation constitue des 5 derniers messages
#     context=""
#     if len(messages)>1:
#         conversation_history= messages[-6:-1] if len(messages)>=6 else messages[:-1]
#         context= "\n".join(
#             f"{'User:' if i%2==0 else 'Assistant:'} {msg.content if hasattr(msg, 'content') else str(msg)}"
#             for i, msg in enumerate(conversation_history)
#         )
    
#     #prompt with context
#     if context:
#         prompt = f"""Contexte de la conversation:
# {context}

# Question actuelle: {original_question}

# Reformule cette question pour qu'elle soit autonome et optimisée pour une recherche web.
# Intègre le contexte conversationnel si la question y fait référence (par exemple "ses avantages" → "les avantages de X").
# Rends-la claire, précise et adaptée aux moteurs de recherche.

# Question reformulée:"""
#     else:
#         prompt = f"""Reformule cette question pour optimiser une recherche web.
# Rends-la plus claire, précise et adaptée aux moteurs de recherche.
# Garde le sens original mais améliore la formulation.

# Question originale: {original_question}

# Question améliorée:"""
    
#     try:
#         # reecrire la question
#         response = llm.invoke(prompt)
#         better_question = response.content.strip()
#         print(f"---ORIGINAL: {original_question}---")
#         print(f"---IMPROVED: {better_question}---")
        
#         # stocker la question transformée dans un champ séparé pour web_search
#         return {"transformed_question": better_question}
    
#     except Exception as e:
#         print(f"---TRANSFORM ERROR: {str(e)}---")
#         # en cas d'erreur, utiliser la question originale
#         return {"transformed_question": original_question}
