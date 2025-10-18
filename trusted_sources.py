# 🌐 Sources Officielles Togolaises Fiables

# Sites gouvernementaux officiels
SERVICE_PUBLIC = "service-public.gouv.tg"
GOUVERNEMENT = "gouvernement.tg"
PRESIDENCE = "presidence.gouv.tg"

# Ministères
MINISTERE_JUSTICE = "justice.gouv.tg"
MINISTERE_INTERIEUR = "interieur.gouv.tg"
MINISTERE_AFFAIRES_ETRANGERES = "diplomatie.gouv.tg"

# Services administratifs
PREFECTURE_LOME = "prefecture-lome.gouv.tg"
MAIRIE_LOME = "mairie-lome.tg"

# Liste complète des domaines fiables (ordre de priorité)
TRUSTED_DOMAINS = [
    "service-public.gouv.tg",           # Service public officiel (PRIORITÉ 1)
    "gouvernement.tg",                  # Site du gouvernement
    "presidence.gouv.tg",              # Présidence de la République
    "justice.gouv.tg",                 # Ministère de la Justice
    "interieur.gouv.tg",               # Ministère de l'Intérieur
    "diplomatie.gouv.tg",              # Ministère des Affaires étrangères
    "prefecture-lome.gouv.tg",         # Préfecture de Lomé
    "mairie-lome.tg",                  # Mairie de Lomé
    "agence-nationale-identification.tg", # ANI (identification biométrique)
    "anpe.tg",                         # Agence Nationale Pour l'Emploi
    "cnss.tg",                         # Caisse Nationale de Sécurité Sociale
]

# Requêtes de recherche web optimisées par domaine
def get_search_query(user_question: str, priority_domain: str = None) -> str:
    """
    Génère une requête de recherche web optimisée
    
    Args:
        user_question: Question de l'utilisateur
        priority_domain: Domaine à prioriser (optionnel)
    
    Returns:
        Requête optimisée avec restriction de site
    """
    if priority_domain:
        return f"{user_question} site:{priority_domain}"
    
    # Par défaut, chercher sur service-public.gouv.tg
    return f"{user_question} site:service-public.gouv.tg"


def get_multi_domain_queries(user_question: str, max_domains: int = 3) -> list[str]:
    """
    Génère plusieurs requêtes pour rechercher sur plusieurs domaines fiables
    
    Args:
        user_question: Question de l'utilisateur
        max_domains: Nombre maximum de domaines à interroger
    
    Returns:
        Liste de requêtes optimisées
    """
    queries = []
    for domain in TRUSTED_DOMAINS[:max_domains]:
        queries.append(f"{user_question} site:{domain}")
    return queries


# Configuration pour Tavily
TAVILY_CONFIG = {
    "search_depth": "advanced",  # Recherche approfondie
    "max_results": 5,            # Maximum 5 résultats par requête
    "include_domains": TRUSTED_DOMAINS,  # Limiter aux domaines fiables
    "exclude_domains": [
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        # Exclure les réseaux sociaux et sites non officiels
    ]
}


# Messages d'erreur si aucune source fiable n'est trouvée
NO_RELIABLE_SOURCE_MESSAGE = """
Je n'ai pas trouvé d'informations fiables dans les sources officielles togolaises.

**Sources consultées :**
- ✅ Base de connaissances (documents officiels)
- ✅ service-public.gouv.tg
- ✅ gouvernement.tg
- ✅ Autres sites gouvernementaux

**Recommandations :**
1. Vérifie directement sur https://service-public.gouv.tg
2. Contacte le service administratif concerné
3. Rends-toi physiquement à la mairie ou préfecture

Veux-tu que je reformule ta question pour élargir la recherche ? 🤔
"""


# Validation des sources
def is_trusted_source(url: str) -> bool:
    """
    Vérifie si une URL provient d'une source fiable
    
    Args:
        url: URL à vérifier
    
    Returns:
        True si la source est fiable, False sinon
    """
    if not url:
        return False
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in TRUSTED_DOMAINS)


def get_source_reliability_score(url: str) -> float:
    """
    Calcule un score de fiabilité pour une source
    
    Args:
        url: URL de la source
    
    Returns:
        Score entre 0.0 (non fiable) et 1.0 (très fiable)
    """
    if not url:
        return 0.0
    
    url_lower = url.lower()
    
    # Score par domaine (ordre de priorité)
    for i, domain in enumerate(TRUSTED_DOMAINS):
        if domain in url_lower:
            # Score décroissant selon la position dans la liste
            return 1.0 - (i * 0.05)
    
    # Source inconnue = score faible
    return 0.3
