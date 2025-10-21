# """
# Fonction de décision CRAG - Détermine le prochain node
# """

# """
# CRAG Decision Function - Determines the next node
# """

# from typing import Dict, Literal
# def decide_to_generate(state:Dict)->Literal["generate", "transformQuery"]:
#     """Decide whether to proceed to the 'generate' node or the 'transformQuery' node  for a websearch, based on the input state.
#     if we have at leas one relevant document from our state, we proceed to generate, otherwise we rewrite the query for websearch.
#     Args:
#         state (Dict): The current state containing input retrieve documents that would be used for decision making.
#     Returns:
#         Literal["generate", "transformQuery"]: The next node to proceed to.
#     """

#     print("decision node: evaluation des documents recuperes")
#     filtered_docs= state["documents"]
#     if len(filtered_docs)== 0:
#         print("Aucun document pertinent trouvé, redirection vers le node TRANSFORM_QUERY pour reformuler la question.")
#         return "transformQuery"   

#     print(f"{len(filtered_docs)} documents pertinents trouvés, redirection vers le node GENERATE pour générer la réponse.")
#     return "generate"    