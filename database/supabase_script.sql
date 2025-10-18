-- ============================================
-- SUPABASE SETUP SCRIPT FOR CRAWL2RAG
-- ============================================

-- 1. Activer l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tables LangChain PGVector standard
-- PGVector crée automatiquement ces tables mais on les définit ici pour être explicite

-- Table des collections (créée automatiquement par PGVector)
CREATE TABLE IF NOT EXISTS langchain_pg_collection (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL UNIQUE,
    cmetadata JSONB
);

-- Table des embeddings (créée automatiquement par PGVector)
CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding VECTOR(2000),  -- OpenAI text-embedding-3-large avec 2000 dimensions
    document TEXT,
    cmetadata JSONB,
    custom_id VARCHAR
);

-- 3. Index pour la recherche vectorielle (cosine similarity)
-- IVFFlat est optimal pour des datasets de taille moyenne
CREATE INDEX IF NOT EXISTS langchain_pg_embedding_embedding_idx 
ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Index pour le filtrage rapide par collection
CREATE INDEX IF NOT EXISTS idx_embedding_collection_id 
ON langchain_pg_embedding(collection_id);

-- 5. Index JSONB pour les métadonnées (thread_id, url, etc.)
CREATE INDEX IF NOT EXISTS idx_embedding_cmetadata 
ON langchain_pg_embedding USING gin(cmetadata);

-- 6. Table pour les checkpoints LangGraph (remplace checkpoints_aio et checkpoint_writes_aio)
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- 7. Index pour les checkpoints
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id 
ON langgraph_checkpoints(thread_id);

CREATE INDEX IF NOT EXISTS idx_checkpoints_parent 
ON langgraph_checkpoints(parent_checkpoint_id);

-- 8. Table pour les writes de checkpoints
CREATE TABLE IF NOT EXISTS langgraph_checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- 9. Index pour les writes
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread 
ON langgraph_checkpoint_writes(thread_id);

-- 10. Fonction helper pour rechercher des documents similaires
-- Adaptée pour le schéma LangChain standard
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(2000),
    collection_name_param TEXT,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document TEXT,
    cmetadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
DECLARE
    collection_uuid UUID;
BEGIN
    -- Récupérer l'UUID de la collection
    SELECT uuid INTO collection_uuid 
    FROM langchain_pg_collection 
    WHERE name = collection_name_param;
    
    IF collection_uuid IS NULL THEN
        RAISE EXCEPTION 'Collection % not found', collection_name_param;
    END IF;
    
    RETURN QUERY
    SELECT
        e.id,
        e.document,
        e.cmetadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM langchain_pg_embedding e
    WHERE 
        e.collection_id = collection_uuid
        AND (filter_metadata IS NULL OR e.cmetadata @> filter_metadata)
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 11. Fonction pour supprimer les documents par thread_id
-- Utilisée par le endpoint /delete_vector_store
CREATE OR REPLACE FUNCTION delete_documents_by_thread(
    collection_name_param TEXT,
    thread_id_param TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    collection_uuid UUID;
    deleted_count INTEGER;
BEGIN
    -- Récupérer l'UUID de la collection
    SELECT uuid INTO collection_uuid 
    FROM langchain_pg_collection 
    WHERE name = collection_name_param;
    
    IF collection_uuid IS NULL THEN
        RETURN 0;  -- Collection n'existe pas, retourner 0
    END IF;
    
    -- Supprimer les documents et compter
    DELETE FROM langchain_pg_embedding
    WHERE collection_id = collection_uuid
    AND cmetadata->>'thread_id' = thread_id_param;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$;

-- ============================================
-- VERIFICATION
-- ============================================
-- Vérifier que tout est bien créé
SELECT 'Tables créées:' AS info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('langchain_pg_collection', 'langchain_pg_embedding', 'langgraph_checkpoints', 'langgraph_checkpoint_writes');

SELECT 'Extension pgvector activée:' AS info;
SELECT * FROM pg_extension WHERE extname = 'vector';

SELECT 'Index créés:' AS info;
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('langchain_pg_embedding', 'langgraph_checkpoints', 'langgraph_checkpoint_writes');

SELECT 'Collections disponibles:' AS info;
SELECT name, uuid FROM langchain_pg_collection;
