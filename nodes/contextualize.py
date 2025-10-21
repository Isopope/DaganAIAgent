# """
# Node CONTEXTUALIZE - Reformulation de la question avec contexte conversationnel
# """

# """
# Node CONTEXTUALIZE - Reformulation of the question with conversational context
# """

# # import os
# # from typing import Any
# # from langchain_openai import ChatOpenAI
# # from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# # from datetime import datetime

# # def contextualize_question(state: dict[str, Any]) -> dict[str, Any]:
# #     """
# #     Reformule la question en tenant compte de l'historique conversationnel.
# #     Cela permet de rendre les questions de suivi autonomes (standalone).
    
# #     Par exemple:
# #     - Historique: "Qu'est-ce que le RAG?"
# #     - Question actuelle: "Quels sont ses avantages?"
# #     - Question reformulée: "Quels sont les avantages du RAG?"
    
# #     Args:
# #         state: GraphState contenant conversation_id, question
        
# #     Returns:
# #         dict avec question (reformulée si nécessaire)
# #     """
# #     print("\n--- NODE: CONTEXTUALIZE_QUESTION ---")
    
# #     conversation_id = state.get("conversation_id")
# #     question = state["question"]
    
# #     print(f"Question originale: {question}")
# #     print(f"Conversation ID: {conversation_id}")
    
# #     # Configuration
# #     llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
# #     llm_temperature = float(os.getenv("LLM_TEMPERATURE_GRADING", "0"))
# #     max_history = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
# #     conversations_collection_name = os.getenv("CONVERSATIONS_COLLECTION", "conversations")
    
# #     # Si pas de conversation_id, retourner la question telle quelle
# #     if not conversation_id:
# #         print("✓ Pas de conversation_id, question non modifiée")
# #         print("--- FIN NODE: CONTEXTUALIZE_QUESTION ---\n")
# #         return {"question": question}
    
# #     # Connexion MongoDB pour récupérer l'historique
# #     mongo_uri = os.getenv("MONGODB_URI")
# #     if not mongo_uri:
# #         print(" MONGODB_URI non configuré, question non modifiée")
# #         print("--- FIN NODE: CONTEXTUALIZE_QUESTION ---\n")
# #         return {"question": question}
    
# #     try:
# #         mongo_client = MongoClient(mongo_uri)
# #         db = mongo_client.get_default_database()
# #         conversations_collection = db[conversations_collection_name]
        
# #         # Récupérer l'historique conversationnel
# #         conversation_doc = conversations_collection.find_one({"conversation_id": conversation_id})
        
# #         if not conversation_doc or not conversation_doc.get("messages"):
# #             print("✓ Pas d'historique, question non modifiée")
# #             mongo_client.close()
# #             print("--- FIN NODE: CONTEXTUALIZE_QUESTION ---\n")
# #             return {"question": question}
        
# #         # Limiter l'historique aux N derniers messages
# #         all_messages = conversation_doc["messages"]
# #         conversation_history = all_messages[-max_history:] if len(all_messages) > max_history else all_messages
        
# #         print(f"✓ Historique récupéré: {len(conversation_history)} messages")
        
# #         # Construire le prompt pour reformuler la question
# #         messages = []
        
# #         # System message
# #         system_message = SystemMessage(content="""Tu es un assistant qui reformule les questions de suivi pour les rendre autonomes et compréhensibles sans contexte.

# # Instructions:
# # - Si la question fait référence à un élément de la conversation précédente (par exemple "ses avantages", "plus d'informations", "et ensuite?"), reformule-la pour qu'elle soit claire et autonome
# # - Si la question est déjà autonome et claire, retourne-la telle quelle
# # - Retourne UNIQUEMENT la question reformulée, sans explication ni texte supplémentaire
# # - Conserve le sens et l'intention de la question originale

# # Exemples:
# # Historique: "Qu'est-ce que le RAG?"
# # Question: "Quels sont ses avantages?"
# # → "Quels sont les avantages du RAG?"

# # Historique: "Parle-moi de Python"
# # Question: "Comment l'installer?"
# # → "Comment installer Python?"

# # Historique: "Qu'est-ce que FastAPI?"
# # Question: "Qu'est-ce que Django?"
# # → "Qu'est-ce que Django?" (déjà autonome)""")
# #         messages.append(system_message)
        
# #         # Ajouter l'historique conversationnel
# #         for msg in conversation_history:
# #             role = msg.get("role")
# #             content = msg.get("content")
# #             if role == "user":
# #                 messages.append(HumanMessage(content=content))
# #             elif role == "assistant":
# #                 messages.append(AIMessage(content=content))
        
# #         # Ajouter la question actuelle
# #         user_message = f"""Question actuelle à reformuler si nécessaire: {question}

# # Question reformulée:"""
# #         messages.append(HumanMessage(content=user_message))
        
# #         # Initialiser le LLM
# #         llm = ChatOpenAI(
# #             model=llm_model,
# #             temperature=llm_temperature,
# #             api_key=os.getenv("OPENAI_API_KEY")
# #         )
        
# #         # Générer la question reformulée
# #         response = llm.invoke(messages)
# #         contextualized_question = response.content.strip()
        
# #         # Vérifier que la reformulation n'est pas vide
# #         if not contextualized_question:
# #             print(" Reformulation vide, utilisation de la question originale")
# #             contextualized_question = question
        
# #         print(f"✓ Question reformulée: {contextualized_question}")
        
# #         mongo_client.close()
        
# #     except Exception as e:
# #         print(f" Erreur lors de la contextualisation: {e}")
# #         contextualized_question = question
    
# #     print("--- FIN NODE: CONTEXTUALIZE_QUESTION ---\n")
    
# #     return {"question": contextualized_question}
