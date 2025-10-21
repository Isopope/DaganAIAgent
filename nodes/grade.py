# """
# Node GRADE_DOCUMENTS - Évaluation de la pertinence des documents du node RETRIEVE en demandant au LLM
# """

# """
# Node GRADE_DOCUMENTS - Evaluation of the relevance of documents from the RETRIEVE node by querying the LLM
# """

# import os
# from typing import Dict, List

# from langchain.schema import Document
# from langchain_openai import ChatOpenAI

# def grade_documents(state:Dict)->Dict:
#     """Grade the relevance of retrieved documents using the LLM.
#     for each document retrieved from the vector database,we ask the llm to evaluate its relevance
#     and respond by a binary response (oui or non)
#     Args:
#         state (Dict): The current state containing input documents that would be used for the grading process.
#     Returns:
#         Dict with documents key, containing the list of documents graded with "oui".

#     """
#     print("Grade node : evaluation de la pertinence des documents recuperes")
#     messages= state.get("documents", [])
#     if not messages:
#         print("Aucun document trouvé pour évaluation.")
#         return {"documents": []}
    
#     last_message=messages[-1]
#     question= last_message.content if hasattr(last_message, 'content') else str(last_message)
#     documents=state["documents"]
    
#     # llm configuration
#     llm_model=os.getenv("LLM_MODEL","gpt-4.1-nano")
#     temperature=float(os.getenv("LLM_TEMPERATURE_GRADING", "0"))
#     llm= ChatOpenAI(
#         model=llm_model,
#         temperature=temperature,
#         openai_api_key=os.getenv("OPENAI_API_KEY")
#     )
#     filtered_docs= []
#     for i, doc in enumerate(messages):
#         content= doc.page_content
#         prompt = f"""Évalue si ce document contient des informations utiles pour répondre à la question.

# Question de l'utilisateur: {question}

# Contenu du document:
# {doc.page_content[:800]}

# Le document est PERTINENT si :
# - Il contient des informations directement liées à la question
# - Il mentionne les concepts clés de la question
# - Il peut aider à construire une réponse, même partiellement

# Réponds UNIQUEMENT par 'oui' si le document est pertinent, 'non' sinon."""
#         try:
#             # Appel au LLM
#             response = llm.invoke(prompt)
#             answer = response.content.strip().lower()
            
#             # Parser la réponse (oui/yes = pertinent, non/no = non pertinent)
#             # Inclure aussi "pertinent" et "relevant" comme réponses positives
#             if any(word in answer for word in ["oui", "yes", "pertinent", "relevant"]):
#                 print(f"---GRADE: DOCUMENT {i+1} RELEVANT---")
#                 filtered_docs.append(doc)
#             else:
#                 print(f"---GRADE: DOCUMENT {i+1} NOT RELEVANT (réponse: {answer})---")
            
#         except Exception as e:
#             print(f"---GRADE ERROR for document {i+1}: {str(e)}---")
#             # En cas d'erreur, on garde le document par sécurite
#             filtered_docs.append(doc)
    
#     print(f"---FILTERED {len(filtered_docs)}/{len(documents)} DOCUMENTS---")
    
#     return {"documents": filtered_docs}