-- Career Research Database Schema
-- For storing EVE Online killmail data and fit analysis

-- Enable pgvector for fit embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Killmail metadata table (for deduplication)
CREATE TABLE IF NOT EXISTS killmails (
    killmail_id BIGINT PRIMARY KEY,
    killmail_hash TEXT NOT NULL,
    killmail_time TIMESTAMPTZ NOT NULL,
    solar_system_id INT NOT NULL,
    victim_character_id BIGINT,
    victim_corporation_id BIGINT,
    victim_alliance_id BIGINT,
    victim_ship_id INT NOT NULL,
    is_npc BOOLEAN DEFAULT FALSE,  -- True if killed by NPCs
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fits extracted from killmails (victim ship + fitted modules)
CREATE TABLE IF NOT EXISTS fits (
    id BIGSERIAL PRIMARY KEY,
    killmail_id BIGINT NOT NULL REFERENCES killmails(killmail_id),
    ship_id INT NOT NULL,  -- victim.ship_type_id

    -- Fitted modules by slot
    high_slots INT[] DEFAULT '{}',
    med_slots INT[] DEFAULT '{}',
    low_slots INT[] DEFAULT '{}',
    rig_slots INT[] DEFAULT '{}',
    subsystem_slots INT[] DEFAULT '{}',

    -- Metadata
    region_id INT,
    solar_system_id INT NOT NULL,
    killed_at TIMESTAMPTZ NOT NULL,

    -- For clustering (to be populated later)
    fit_vector vector(1536),  -- OpenAI embedding size, or choose your own
    cluster_id INT,

    imported_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one fit per killmail
    UNIQUE(killmail_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_killmails_time ON killmails(killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_killmails_ship ON killmails(victim_ship_id);
CREATE INDEX IF NOT EXISTS idx_fits_ship ON fits(ship_id);
CREATE INDEX IF NOT EXISTS idx_fits_time ON fits(killed_at DESC);
CREATE INDEX IF NOT EXISTS idx_fits_cluster ON fits(cluster_id) WHERE cluster_id IS NOT NULL;

-- Index for vector similarity search (HNSW for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_fits_vector ON fits USING hnsw (fit_vector vector_cosine_ops)
    WHERE fit_vector IS NOT NULL;

-- Materialized view for ship class statistics (refresh periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS ship_class_stats AS
SELECT
    ship_id,
    COUNT(*) as fit_count,
    MIN(killed_at) as first_seen,
    MAX(killed_at) as last_seen,
    COUNT(DISTINCT solar_system_id) as systems_seen
FROM fits
GROUP BY ship_id
WITH DATA;

-- Unique constraint to prevent duplicate imports
CREATE UNIQUE INDEX IF NOT EXISTS idx_killmails_hash ON killmails(killmail_hash);
