-- ============================================
-- SUPABASE SETUP SCRIPT - VERSION MINIMALE
-- Dagan Agentic RAG System
-- ============================================
-- 
-- Ce script contient UNIQUEMENT les tables et fonctions
-- réellement utilisées par les endpoints actuels.
-- 
-- Endpoints actifs :
-- - POST /vectorize : Vectorisation de documents
-- - POST /crag/query : Requête Agent RAG (non-streaming)
-- - POST /crag/stream : Requête Agent RAG (streaming SSE)
-- - GET /health : Health check
-- 
-- ============================================

-- ============================================
-- 1. EXTENSION PGVECTOR
-- ============================================
-- Obligatoire pour les opérations de recherche vectorielle
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================
-- 2. TABLE PRINCIPALE : langchain_pg_embedding
-- ============================================
-- Stocke les documents vectorisés avec leurs embeddings
-- 
-- Utilisation :
-- - /vectorize : INSERT des chunks vectorisés
-- - vector_search_tool : SELECT avec similarité cosinus
-- 
-- Note : collection_id est TEXT (pas UUID) depuis migration
CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
    id TEXT PRIMARY KEY,                    -- UUID généré par l'application
    collection_id TEXT NOT NULL,            -- Nom de la collection (e.g., "crawled_documents")
    embedding VECTOR(2000),                 -- OpenAI text-embedding-3-large (2000 dimensions)
    document TEXT NOT NULL,                 -- Contenu textuel du chunk
    cmetadata JSONB                         -- Métadonnées : {url, favicon, chunk_index, chunk_count, is_official, ...}
);


-- ============================================
-- 3. INDEX POUR RECHERCHE VECTORIELLE
-- ============================================
-- Index IVFFlat pour recherche de similarité cosinus
-- Optimal pour datasets de taille moyenne (10K-1M vecteurs)
-- 
-- Utilisation : ORDER BY embedding <=> query_vector
CREATE INDEX IF NOT EXISTS langchain_pg_embedding_embedding_idx 
ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);


-- ============================================
-- 4. INDEX POUR FILTRAGE PAR COLLECTION
-- ============================================
-- Accélère les requêtes filtrées par collection_id
-- 
-- Utilisation : WHERE collection_id = 'crawled_documents'
CREATE INDEX IF NOT EXISTS langchain_pg_embedding_collection_idx 
ON langchain_pg_embedding (collection_id);


-- ============================================
-- 5. INDEX JSONB POUR MÉTADONNÉES
-- ============================================
-- Permet des requêtes rapides sur les métadonnées
-- 
-- Exemples :
-- - WHERE cmetadata->>'url' = 'https://...'
-- - WHERE (cmetadata->>'is_official')::boolean = true
CREATE INDEX IF NOT EXISTS langchain_pg_embedding_cmetadata_idx 
ON langchain_pg_embedding USING gin(cmetadata);


-- ============================================
-- 6. TABLE : conversations (Tracking/Monitoring)
-- ============================================
-- Stocke l'historique des conversations pour monitoring
-- Table unique pour le suivi des interactions utilisateur/IA
-- 
-- Utilisation : Monitoring et analytics uniquement
-- Note : La mémoire runtime utilise InMemorySaver (volatile)
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,                    -- conversation_id (UUID généré par LangGraph)
    user_id TEXT,                           -- Identifiant utilisateur (optionnel)
    question TEXT NOT NULL,                 -- Question de l'utilisateur
    answer TEXT,                            -- Réponse de l'IA
    sources JSONB,                          -- Sources utilisées [{title, url, snippet}]
    tools_used TEXT[],                      -- Outils utilisés ['vector_search', 'web_search', 'reranker']
    vector_searches INTEGER DEFAULT 0,      -- Nombre de recherches vectorielles
    web_searches INTEGER DEFAULT 0,         -- Nombre de recherches web
    duration_ms INTEGER,                    -- Durée totale de traitement (ms)
    tokens_used INTEGER,                    -- Tokens consommés (optionnel)
    status TEXT DEFAULT 'completed',        -- Status: completed, error, timeout
    error_message TEXT,                     -- Message d'erreur si échec
    metadata JSONB,                         -- Métadonnées additionnelles (IP, user agent, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche et analytics
CREATE INDEX IF NOT EXISTS conversations_user_id_idx 
ON conversations (user_id);

CREATE INDEX IF NOT EXISTS conversations_created_at_idx 
ON conversations (created_at DESC);

CREATE INDEX IF NOT EXISTS conversations_status_idx 
ON conversations (status);

-- Trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_updated_at_trigger
BEFORE UPDATE ON conversations
FOR EACH ROW
EXECUTE FUNCTION update_conversations_updated_at();


-- ============================================
-- 7. FONCTION : match_documents
-- ============================================
-- Fonction helper pour recherche de similarité vectorielle
-- 
-- Paramètres :
-- - query_embedding : Vecteur de la question (VECTOR(2000))
-- - collection_name_param : Nom de la collection à interroger
-- - match_threshold : Seuil de similarité minimum (défaut: 0.7)
-- - match_count : Nombre maximum de résultats (défaut: 5)
-- - filter_metadata : Filtre JSONB optionnel (défaut: NULL)
-- 
-- Retour :
-- - id : Identifiant du document
-- - document : Contenu textuel
-- - cmetadata : Métadonnées complètes
-- - similarity : Score de similarité (0-1, plus proche de 1 = plus similaire)
-- 
-- Utilisation optionnelle (actuellement vector_search_tool fait la recherche directement)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(2000),
    collection_name_param TEXT,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id TEXT,
    document TEXT,
    cmetadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.document,
        e.cmetadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM langchain_pg_embedding e
    WHERE 
        e.collection_id = collection_name_param
        AND (filter_metadata IS NULL OR e.cmetadata @> filter_metadata)
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================
-- 8. FONCTION : delete_documents_by_collection
-- ============================================
-- Supprime tous les documents d'une collection
-- 
-- Paramètres :
-- - collection_name_param : Nom de la collection à vider
-- 
-- Retour : Nombre de documents supprimés
-- 
-- Utilisation : Maintenance, nettoyage de données
CREATE OR REPLACE FUNCTION delete_documents_by_collection(
    collection_name_param TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM langchain_pg_embedding
    WHERE collection_id = collection_name_param;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$;


-- ============================================
-- 9. FONCTION : get_collection_stats
-- ============================================
-- Retourne des statistiques sur une collection
-- 
-- Paramètres :
-- - collection_name_param : Nom de la collection
-- 
-- Retour :
-- - collection_id : Nom de la collection
-- - document_count : Nombre de documents
-- - unique_urls : Nombre d'URLs uniques
-- - total_size_bytes : Taille totale approximative (texte)
-- - avg_chunk_size : Taille moyenne des chunks
CREATE OR REPLACE FUNCTION get_collection_stats(
    collection_name_param TEXT
)
RETURNS TABLE (
    collection_id TEXT,
    document_count BIGINT,
    unique_urls BIGINT,
    total_size_bytes BIGINT,
    avg_chunk_size NUMERIC
)
LANGUAGE sql
AS $$
    SELECT
        collection_id,
        COUNT(*) AS document_count,
        COUNT(DISTINCT cmetadata->>'url') AS unique_urls,
        SUM(LENGTH(document)) AS total_size_bytes,
        ROUND(AVG(LENGTH(document))) AS avg_chunk_size
    FROM langchain_pg_embedding
    WHERE collection_id = collection_name_param
    GROUP BY collection_id;
$$;


-- ============================================
-- 10. FONCTION : get_conversation_stats (Monitoring)
-- ============================================
-- Retourne des statistiques globales sur les conversations
-- 
-- Paramètres :
-- - days_back : Nombre de jours en arrière (défaut: 7)
-- 
-- Retour :
-- - total_conversations : Nombre total de conversations
-- - completed_conversations : Conversations terminées avec succès
-- - error_conversations : Conversations en erreur
-- - avg_duration_ms : Durée moyenne de traitement (ms)
-- - total_vector_searches : Nombre total de recherches vectorielles
-- - total_web_searches : Nombre total de recherches web
-- - avg_sources_per_answer : Nombre moyen de sources par réponse
-- - most_used_tools : Outils les plus utilisés
CREATE OR REPLACE FUNCTION get_conversation_stats(
    days_back INT DEFAULT 7
)
RETURNS TABLE (
    total_conversations BIGINT,
    completed_conversations BIGINT,
    error_conversations BIGINT,
    avg_duration_ms NUMERIC,
    total_vector_searches BIGINT,
    total_web_searches BIGINT,
    avg_sources_per_answer NUMERIC,
    most_used_tools TEXT[]
)
LANGUAGE sql
AS $$
    SELECT
        COUNT(*) AS total_conversations,
        COUNT(*) FILTER (WHERE status = 'completed') AS completed_conversations,
        COUNT(*) FILTER (WHERE status = 'error') AS error_conversations,
        ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
        COALESCE(SUM(vector_searches), 0) AS total_vector_searches,
        COALESCE(SUM(web_searches), 0) AS total_web_searches,
        ROUND(AVG(JSONB_ARRAY_LENGTH(COALESCE(sources, '[]'::JSONB))), 2) AS avg_sources_per_answer,
        ARRAY_AGG(DISTINCT tool ORDER BY tool) AS most_used_tools
    FROM conversations,
         LATERAL UNNEST(COALESCE(tools_used, ARRAY[]::TEXT[])) AS tool
    WHERE created_at >= NOW() - (days_back || ' days')::INTERVAL;
$$;


-- ============================================
-- 11. VÉRIFICATION DE L'INSTALLATION
-- ============================================
-- Affiche un résumé de la configuration

-- Extension pgvector
SELECT 
    'Extension pgvector' AS component,
    CASE WHEN COUNT(*) > 0 THEN ' Activée' ELSE ' Manquante' END AS status
FROM pg_extension 
WHERE extname = 'vector';

-- Table langchain_pg_embedding
SELECT 
    'Table langchain_pg_embedding' AS component,
    CASE WHEN COUNT(*) > 0 THEN '✓ Créée' ELSE '✗ Manquante' END AS status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'langchain_pg_embedding';

-- Table conversations
SELECT 
    'Table conversations' AS component,
    CASE WHEN COUNT(*) > 0 THEN '✓ Créée' ELSE '✗ Manquante' END AS status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'conversations';

-- Index créés
SELECT 
    'Index' AS component,
    COUNT(*)::TEXT || ' index créés' AS status
FROM pg_indexes 
WHERE tablename = 'langchain_pg_embedding';

-- Fonctions créées
SELECT 
    'Fonctions' AS component,
    COUNT(*)::TEXT || ' fonctions créées' AS status
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
AND p.proname IN ('match_documents', 'delete_documents_by_collection', 'get_collection_stats', 'get_conversation_stats', 'update_conversations_updated_at');


-- ============================================
-- FIN DU SCRIPT
-- ============================================
-- 
-- Prochaines étapes :
-- 1. Exécuter ce script dans Supabase SQL Editor
-- 2. Vérifier que tous les composants sont marqués ✓
-- 3. Tester avec POST /vectorize pour créer des embeddings
-- 4. Tester avec POST /crag/query pour interroger
-- 
-- Maintenance et monitoring :
-- - Vider une collection : SELECT delete_documents_by_collection('crawled_documents');
-- - Stats collection : SELECT * FROM get_collection_stats('crawled_documents');
-- - Stats conversations : SELECT * FROM get_conversation_stats(7); -- 7 derniers jours
-- - Lister les URLs : SELECT DISTINCT cmetadata->>'url' FROM langchain_pg_embedding WHERE collection_id = 'crawled_documents';
-- - Conversations récentes : SELECT id, question, status, created_at FROM conversations ORDER BY created_at DESC LIMIT 10;
-- - Conversations en erreur : SELECT id, question, error_message, created_at FROM conversations WHERE status = 'error' ORDER BY created_at DESC;
-- 
-- ============================================
