-- The NewsBreakers — PostgreSQL (PROCESSED + auditoría + HITL)
-- Mongo guarda RAW. Las imágenes van a object storage; aquí solo metadatos.
-- pgvector: extensión para embeddings (Fase 6 / 15). Si no está, comentar CREATE EXTENSION.

CREATE EXTENSION IF NOT EXISTS vector;

-- ── Fuentes (watchlist) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT NOT NULL,
  country TEXT,
  language TEXT,
  type TEXT,
  category TEXT,
  priority TEXT NOT NULL DEFAULT 'normal',
  access_method TEXT NOT NULL DEFAULT 'rss',  -- api | rss | scrape
  rss_url TEXT,
  base_url TEXT,
  scraper_type TEXT,
  parser_version TEXT NOT NULL DEFAULT 'parser_v1',
  frequency_minutes INTEGER NOT NULL DEFAULT 60,
  confidence INTEGER,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  last_checked TIMESTAMPTZ,
  last_success TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sources_active_priority ON sources (active, priority);

-- ── Artículos normalizados (UniversalContent) ──────────────────────────────
-- pipeline_level: embudo 0–9 (ver docs/ARCHITECTURE.md)
CREATE TABLE IF NOT EXISTS articles (
  content_id TEXT PRIMARY KEY,
  source_id TEXT REFERENCES sources(source_id),
  url TEXT NOT NULL,
  url_sha256 TEXT NOT NULL,
  text_sha256 TEXT,
  title TEXT,
  text TEXT,
  author TEXT,
  language TEXT,
  published_at TIMESTAMPTZ,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  relevance_score REAL,
  pipeline_level INTEGER NOT NULL DEFAULT 0,
  raw_format TEXT,
  model_versions JSONB,
  UNIQUE (url),
  UNIQUE (url_sha256)
);

CREATE INDEX IF NOT EXISTS idx_articles_text_sha256 ON articles (text_sha256);
CREATE INDEX IF NOT EXISTS idx_articles_pipeline ON articles (pipeline_level);

-- ── Claims / entidades ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES articles(content_id),
  text TEXT NOT NULL,
  subject TEXT,
  predicate TEXT,
  object TEXT,
  location TEXT,
  animal TEXT,
  verifiable BOOLEAN DEFAULT TRUE,
  nli_label TEXT,          -- Supported | Contradicted | Unknown
  verdict TEXT,            -- veredicto de producto (5 valores)
  confidence REAL,
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES articles(content_id),
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  model_name TEXT,
  model_version TEXT
);

-- ── Evidencia (NLI se calcula claim × evidence) ────────────────────────────
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  claim_id TEXT REFERENCES claims(claim_id),
  url TEXT,
  source_tier TEXT,        -- official | international | scientific | trusted_journalism | other
  snippet TEXT,
  stance TEXT,             -- Supported | Contradicted | Unknown
  collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Narrativas (cluster de claims, no un artículo) ─────────────────────────
CREATE TABLE IF NOT EXISTS narratives (
  narrative_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  growth_pct REAL,
  first_seen TIMESTAMPTZ,
  last_seen TIMESTAMPTZ,
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS narrative_claims (
  narrative_id TEXT REFERENCES narratives(narrative_id),
  claim_id TEXT REFERENCES claims(claim_id),
  PRIMARY KEY (narrative_id, claim_id)
);

-- ── Alertas + HITL + auditoría ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  risk_score INTEGER,
  verdict TEXT,
  claim_id TEXT REFERENCES claims(claim_id),
  narrative_id TEXT REFERENCES narratives(narrative_id),
  explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'pending_review',
  model_name TEXT,
  model_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews (
  review_id TEXT PRIMARY KEY,
  alert_id TEXT REFERENCES alerts(alert_id),
  prediction TEXT,
  human_label TEXT,
  reason TEXT,
  analyst TEXT,
  used_for_retraining BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGSERIAL PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  action TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (model_name, model_version)
);

-- ── Imágenes: binario en object storage; metadatos aquí ────────────────────
CREATE TABLE IF NOT EXISTS images (
  image_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES articles(content_id),
  storage_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  phash TEXT,
  mime_type TEXT,
  width INTEGER,
  height INTEGER,
  ocr_text TEXT,
  cnn_class TEXT,
  cnn_confidence REAL,
  model_versions JSONB
);

CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images (sha256);
CREATE INDEX IF NOT EXISTS idx_images_phash ON images (phash);

-- ── Embeddings (pgvector) ──────────────────────────────────────────────────
-- Dimensiones iniciales: texto 384 / visión 512 — ajustar al modelo real.
CREATE TABLE IF NOT EXISTS article_embeddings (
  content_id TEXT PRIMARY KEY REFERENCES articles(content_id),
  embedding VECTOR(384),
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS claim_embeddings (
  claim_id TEXT PRIMARY KEY REFERENCES claims(claim_id),
  embedding VECTOR(384),
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS image_embeddings (
  image_id TEXT PRIMARY KEY REFERENCES images(image_id),
  content_id TEXT REFERENCES articles(content_id),
  embedding VECTOR(512),
  model_name TEXT,
  model_version TEXT
);

-- Índices IVFFlat/HNSW se crean cuando haya volumen (ver database/pgvector.md)
