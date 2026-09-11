-- The NewsBreakers — MySQL 8 warehouse (watchlist mining).
-- Dual-write with SQLite. Dedup: UNIQUE(url_sha256). LLM no decide la verdad.
-- charset utf8mb4. Init: docker-entrypoint y/o Python MysqlMirror._ensure_schema.

CREATE DATABASE IF NOT EXISTS newsbreakers
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE newsbreakers;

CREATE TABLE IF NOT EXISTS sources (
  source_id VARCHAR(64) NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  domain VARCHAR(255),
  country VARCHAR(32),
  language VARCHAR(16),
  type VARCHAR(64),
  category VARCHAR(64),
  priority VARCHAR(32) DEFAULT 'normal',
  access_method VARCHAR(16) DEFAULT 'rss',
  rss_url TEXT,
  base_url TEXT,
  parser_version VARCHAR(64) DEFAULT 'parser_v1',
  frequency_minutes INT DEFAULT 60,
  confidence INT,
  active TINYINT(1) DEFAULT 1,
  last_checked DATETIME(6),
  next_check DATETIME(6),
  last_error TEXT,
  last_success DATETIME(6),
  consecutive_failures INT DEFAULT 0,
  extra JSON,
  updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS articles (
  content_id VARCHAR(64) NOT NULL PRIMARY KEY,
  source_id VARCHAR(64),
  url TEXT NOT NULL,
  url_sha256 CHAR(64) NOT NULL,
  text_sha256 CHAR(64),
  title TEXT,
  text MEDIUMTEXT,
  author VARCHAR(255),
  language VARCHAR(16),
  published_at DATETIME(6),
  collected_at DATETIME(6),
  relevance_score DOUBLE,
  pipeline_level INT DEFAULT 0,
  raw_format VARCHAR(64),
  risk_score INT,
  verdict VARCHAR(64),
  model_versions JSON,
  country VARCHAR(32),
  source_type VARCHAR(64),
  disease_tags JSON,
  llm_status TEXT,
  llm_explanation TEXT,
  llm_provider VARCHAR(64),
  thumb_path TEXT,
  UNIQUE KEY uk_articles_url_sha256 (url_sha256),
  KEY idx_articles_text_sha256 (text_sha256),
  KEY idx_articles_collected (collected_at),
  KEY idx_articles_source (source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS claims (
  claim_id VARCHAR(64) NOT NULL PRIMARY KEY,
  content_id VARCHAR(64),
  text TEXT NOT NULL,
  subject TEXT,
  predicate TEXT,
  object TEXT,
  location VARCHAR(255),
  animal VARCHAR(255),
  verifiable TINYINT(1) DEFAULT 1,
  nli_label VARCHAR(32),
  verdict VARCHAR(64),
  confidence DOUBLE,
  model_name VARCHAR(64),
  model_version VARCHAR(64),
  KEY idx_claims_content (content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS entities (
  entity_id VARCHAR(64) NOT NULL PRIMARY KEY,
  content_id VARCHAR(64),
  kind VARCHAR(32) NOT NULL,
  value VARCHAR(512) NOT NULL,
  model_name VARCHAR(64),
  model_version VARCHAR(64),
  KEY idx_entities_content (content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id VARCHAR(64) NOT NULL PRIMARY KEY,
  claim_id VARCHAR(64),
  url TEXT,
  source_tier VARCHAR(64),
  snippet TEXT,
  stance VARCHAR(32),
  collected_at DATETIME(6),
  KEY idx_evidence_claim (claim_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS images (
  image_id VARCHAR(64) NOT NULL PRIMARY KEY,
  content_id VARCHAR(64),
  storage_key TEXT NOT NULL,
  sha256 CHAR(64) NOT NULL,
  phash VARCHAR(128),
  mime_type VARCHAR(64),
  width INT,
  height INT,
  ocr_text TEXT,
  cnn_class VARCHAR(64),
  cnn_confidence DOUBLE,
  reused TINYINT(1) DEFAULT 0,
  alt_text TEXT,
  source_url TEXT,
  model_versions JSON,
  cnn_scores JSON,
  KEY idx_images_sha256 (sha256),
  KEY idx_images_phash (phash),
  KEY idx_images_content (content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS narratives (
  narrative_id VARCHAR(64) NOT NULL PRIMARY KEY,
  label VARCHAR(255) NOT NULL,
  keywords JSON,
  claim_count INT DEFAULT 0,
  prev_count INT DEFAULT 0,
  growth_pct DOUBLE,
  cycle_id VARCHAR(64),
  model_name VARCHAR(64),
  model_version VARCHAR(64),
  updated_at DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS alerts (
  alert_id VARCHAR(64) NOT NULL PRIMARY KEY,
  content_id VARCHAR(64),
  claim_id VARCHAR(64),
  risk_score INT,
  verdict VARCHAR(64),
  explanation JSON,
              status VARCHAR(32) DEFAULT 'pending_review',
  human_label VARCHAR(64),
  human_reason TEXT,
  reviewed_at DATETIME(6),
  model_name VARCHAR(64),
  model_version VARCHAR(64),
  created_at DATETIME(6),
  KEY idx_alerts_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mining_runs (
  run_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  cycle_id VARCHAR(64),
  started_at DATETIME(6) NOT NULL,
  finished_at DATETIME(6),
  articles_new INT DEFAULT 0,
  images_new INT DEFAULT 0,
  errors INT DEFAULT 0,
  extra JSON,
  KEY idx_mining_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cnn_samples (
  sample_id VARCHAR(64) NOT NULL PRIMARY KEY,
  path TEXT NOT NULL,
  class VARCHAR(64) NOT NULL,
  split ENUM('train','val','test') NOT NULL,
  source_article_id VARCHAR(64),
  image_id VARCHAR(64),
  sha256 CHAR(64),
  confidence DOUBLE,
  created_at DATETIME(6),
  UNIQUE KEY uk_cnn_sha256 (sha256),
  KEY idx_cnn_class_split (class, split)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reviews (
  review_id VARCHAR(64) NOT NULL PRIMARY KEY,
  alert_id VARCHAR(64),
  prediction VARCHAR(64),
  human_label VARCHAR(64),
  reason TEXT,
  analyst VARCHAR(128),
  used_for_retraining TINYINT(1) DEFAULT 0,
  created_at DATETIME(6),
  KEY idx_reviews_alert (alert_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  subject_type VARCHAR(64) NOT NULL,
  subject_id VARCHAR(128) NOT NULL,
  action VARCHAR(64) NOT NULL,
  payload JSON,
  created_at DATETIME(6),
  KEY idx_audit_subject (subject_id),
  KEY idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
