"""Persistencia local (MVP): SQLite PROCESSED + JSONL RAW.

Sustituye Postgres/Mongo para demo en Windows sin Docker.
Tablas: sources, articles, images, claims, evidence, alerts, reviews, audit_logs.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

from bootstrap import DB_PATH, FRAMEWORK_ROOT, IMAGES_DIR, PROCESSED_DIR, RAW_DIR

_ing = str(FRAMEWORK_ROOT / "ingestion")
if _ing not in sys.path:
    sys.path.insert(0, _ing)
from safe_urls import public_http_url, stored_article_url

_MIGRATE_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT,
  country TEXT,
  language TEXT,
  type TEXT,
  category TEXT,
  priority TEXT DEFAULT 'normal',
  access_method TEXT DEFAULT 'rss',
  rss_url TEXT,
  base_url TEXT,
  parser_version TEXT DEFAULT 'parser_v1',
  frequency_minutes INTEGER DEFAULT 60,
  confidence INTEGER,
  active INTEGER DEFAULT 1,
  last_checked TEXT,
  next_check TEXT,
  last_error TEXT,
  last_success TEXT,
  consecutive_failures INTEGER DEFAULT 0,
  extra TEXT
);

CREATE TABLE IF NOT EXISTS articles (
  content_id TEXT PRIMARY KEY,
  source_id TEXT,
  url TEXT NOT NULL,
  url_sha256 TEXT NOT NULL,
  text_sha256 TEXT,
  title TEXT,
  text TEXT,
  author TEXT,
  language TEXT,
  published_at TEXT,
  collected_at TEXT,
  relevance_score REAL,
  pipeline_level INTEGER DEFAULT 0,
  raw_format TEXT,
  risk_score INTEGER,
  verdict TEXT,
  model_versions TEXT,
  UNIQUE (url),
  UNIQUE (url_sha256)
);

CREATE INDEX IF NOT EXISTS idx_articles_text_sha256 ON articles (text_sha256);
CREATE INDEX IF NOT EXISTS idx_articles_collected ON articles (collected_at);

CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  content_id TEXT,
  text TEXT NOT NULL,
  subject TEXT,
  predicate TEXT,
  object TEXT,
  location TEXT,
  animal TEXT,
  verifiable INTEGER DEFAULT 1,
  nli_label TEXT,
  verdict TEXT,
  confidence REAL,
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  claim_id TEXT,
  url TEXT,
  source_tier TEXT,
  snippet TEXT,
  stance TEXT,
  collected_at TEXT
);

CREATE TABLE IF NOT EXISTS images (
  image_id TEXT PRIMARY KEY,
  content_id TEXT,
  storage_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  phash TEXT,
  mime_type TEXT,
  width INTEGER,
  height INTEGER,
  ocr_text TEXT,
  cnn_class TEXT,
  cnn_confidence REAL,
  reused INTEGER DEFAULT 0,
  alt_text TEXT,
  source_url TEXT,
  model_versions TEXT
);

CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images (sha256);
CREATE INDEX IF NOT EXISTS idx_images_phash ON images (phash);

CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  content_id TEXT,
  claim_id TEXT,
  risk_score INTEGER,
  verdict TEXT,
  explanation TEXT,
  status TEXT DEFAULT 'pending_review',
  model_name TEXT,
  model_version TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
  review_id TEXT PRIMARY KEY,
  alert_id TEXT,
  prediction TEXT,
  human_label TEXT,
  reason TEXT,
  analyst TEXT,
  used_for_retraining INTEGER DEFAULT 0,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  action TEXT NOT NULL,
  payload TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS narratives (
  narrative_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  keywords TEXT,
  claim_count INTEGER DEFAULT 0,
  prev_count INTEGER DEFAULT 0,
  growth_pct REAL,
  cycle_id TEXT,
  model_name TEXT,
  model_version TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  content_id TEXT,
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  model_name TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS mining_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  cycle_id TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  articles_new INTEGER DEFAULT 0,
  images_new INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0,
  extra TEXT
);

CREATE TABLE IF NOT EXISTS cnn_samples (
  sample_id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  class TEXT NOT NULL,
  split TEXT NOT NULL,
  source_article_id TEXT,
  image_id TEXT,
  sha256 TEXT,
  confidence REAL,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_cnn_samples_class ON cnn_samples (class);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cnn_samples_sha ON cnn_samples (sha256);

CREATE TABLE IF NOT EXISTS translation_cache (
  text_hash TEXT PRIMARY KEY,
  source_text TEXT NOT NULL,
  translated TEXT NOT NULL,
  provider TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS keyword_terms (
  term_id TEXT PRIMARY KEY,
  term TEXT NOT NULL,
  category TEXT NOT NULL,
  label TEXT,
  weight INTEGER DEFAULT 2,
  active INTEGER DEFAULT 1,
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_keyword_terms_cat ON keyword_terms (category);

CREATE TABLE IF NOT EXISTS narrative_members (
  narrative_id TEXT NOT NULL,
  content_id TEXT NOT NULL,
  PRIMARY KEY (narrative_id, content_id)
);
CREATE INDEX IF NOT EXISTS idx_narrative_members_art ON narrative_members (content_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


class Store:
    def __init__(self, path: Path | None = None) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.path = Path(path or DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.seed_keyword_bank()
        self.conn.commit()
        from database.mysql_mirror import get_mirror

        self.mysql = get_mirror()
        self.maybe_backfill_mysql()

    def _migrate(self) -> None:
        extras = {
            "articles": [
                ("country", "TEXT"),
                ("source_type", "TEXT"),
                ("disease_tags", "TEXT"),
                ("llm_status", "TEXT"),
                ("llm_explanation", "TEXT"),
                ("llm_provider", "TEXT"),
                ("thumb_path", "TEXT"),
            ],
            "images": [
                ("ocr_engine", "TEXT"),
                ("cnn_scores", "TEXT"),
            ],
            "alerts": [
                ("human_label", "TEXT"),
                ("human_reason", "TEXT"),
                ("reviewed_at", "TEXT"),
            ],
            "narratives": [
                ("description", "TEXT"),
                ("state", "TEXT"),
                ("extra", "TEXT"),
            ],
            "claims": [
                ("modality", "TEXT"),
            ],
        }
        with _MIGRATE_LOCK:
            for table, cols in extras.items():
                existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
                for name, typ in cols:
                    if name in existing:
                        continue
                    try:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
                    except sqlite3.OperationalError as exc:
                        if "duplicate column" not in str(exc).lower():
                            raise

    def maybe_backfill_mysql(self) -> int:
        """Copia SQLite → MySQL la primera vez que el warehouse está vacío."""
        mirror = getattr(self, "mysql", None)
        if not mirror or not mirror.connected or getattr(mirror, "_backfilled", False):
            return 0
        counts = mirror.counts() or {}
        if int(counts.get("articles") or 0) > 0:
            mirror._backfilled = True
            return 0
        sqlite_n = self.count_articles()
        if sqlite_n == 0:
            return 0
        print(f"[mysql] backfill inicial desde SQLite ({sqlite_n} artículos)…", file=sys.stderr)
        for source in self.list_sources():
            mirror.upsert_source(source, source)
        for article in self.fetchall("SELECT * FROM articles"):
            mirror.insert_article(dict(article))
        for claim in self.fetchall("SELECT * FROM claims"):
            mirror.insert_claim(dict(claim))
        for ev in self.fetchall("SELECT * FROM evidence"):
            mirror.insert_evidence(dict(ev))
        for ent in self.fetchall("SELECT * FROM entities"):
            mirror.insert_entity(dict(ent))
        for img in self.fetchall("SELECT * FROM images"):
            mirror.insert_image(dict(img))
        for alert in self.fetchall("SELECT * FROM alerts"):
            mirror.insert_alert(dict(alert))
        for nar in self.fetchall("SELECT * FROM narratives"):
            mirror.upsert_narrative(dict(nar), int(nar.get("prev_count") or 0))
        for sample in self.fetchall("SELECT * FROM cnn_samples"):
            mirror.insert_cnn_sample(dict(sample))
        for review in self.fetchall("SELECT * FROM reviews"):
            mirror.insert_review(dict(review))
        for log in self.fetchall("SELECT * FROM audit_logs"):
            mirror.insert_audit(dict(log))
        for run in self.fetchall("SELECT * FROM mining_runs"):
            mirror.insert_mining_run(dict(run))
        mirror._backfilled = True
        print("[mysql] backfill listo", file=sys.stderr)
        return sqlite_n

    def close(self) -> None:
        self.conn.close()

    def _mysql(self, method: str, *args: Any, **kwargs: Any) -> None:
        mirror = getattr(self, "mysql", None)
        if not mirror or not mirror.connected:
            return
        fn = getattr(mirror, method, None)
        if not fn:
            return
        try:
            fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            print(f"[mysql] {method} falló: {exc}", file=sys.stderr)

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cur

    def fetchall(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        cur = self.conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]

    def fetchone(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        cur = self.conn.execute(sql, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None

    def translation_hash(self, text: str) -> str:
        return hashlib.sha256(f"en|es\n{text}".encode("utf-8")).hexdigest()

    def get_translation(self, text: str) -> str | None:
        row = self.fetchone(
            "SELECT translated FROM translation_cache WHERE text_hash=?",
            (self.translation_hash(text),),
        )
        return None if row is None else row.get("translated")

    def put_translation(self, text: str, translated: str, provider: str) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO translation_cache
              (text_hash, source_text, translated, provider, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.translation_hash(text), text[:8000], translated, provider, _now()),
        )

    # ── sources ────────────────────────────────────────────────────────────
    def upsert_source(self, source: dict[str, Any]) -> None:
        existing = self.fetchone(
            "SELECT last_checked, next_check, last_error, last_success, consecutive_failures FROM sources WHERE source_id=?",
            (source["source_id"],),
        )
        self.execute(
            """
            INSERT INTO sources (
              source_id, name, domain, country, language, type, category, priority,
              access_method, rss_url, base_url, parser_version, frequency_minutes,
              confidence, active, last_checked, next_check, last_error, last_success,
              consecutive_failures, extra
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_id) DO UPDATE SET
              name=excluded.name, domain=excluded.domain, country=excluded.country,
              language=excluded.language, type=excluded.type, category=excluded.category,
              priority=excluded.priority, access_method=excluded.access_method,
              rss_url=excluded.rss_url, base_url=excluded.base_url,
              parser_version=excluded.parser_version,
              frequency_minutes=excluded.frequency_minutes,
              confidence=excluded.confidence, active=excluded.active, extra=excluded.extra
            """,
            (
                source.get("source_id"),
                source.get("name") or source.get("source_id"),
                source.get("domain"),
                source.get("country"),
                source.get("language"),
                source.get("type"),
                source.get("category"),
                source.get("priority") or "normal",
                source.get("access_method") or "rss",
                source.get("rss_url"),
                source.get("base_url"),
                source.get("parser_version") or "parser_v1",
                int(source.get("frequency_minutes") or 60),
                source.get("confidence"),
                1 if source.get("active", True) else 0,
                (existing or {}).get("last_checked") or source.get("last_checked"),
                (existing or {}).get("next_check") or source.get("next_check"),
                (existing or {}).get("last_error") or source.get("last_error"),
                (existing or {}).get("last_success"),
                (existing or {}).get("consecutive_failures") or 0,
                _json({k: source.get(k) for k in ("diseases", "authority", "registry_id")}),
            ),
        )
        self._mysql("upsert_source", source, existing)

    def patch_source(self, source_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        row = self.get_source(source_id)
        if not row:
            return None
        allowed = {
            "name",
            "domain",
            "country",
            "language",
            "type",
            "category",
            "priority",
            "access_method",
            "rss_url",
            "base_url",
            "frequency_minutes",
            "confidence",
            "active",
        }
        payload = dict(row)
        for key, value in fields.items():
            if key not in allowed:
                continue
            payload[key] = value
        if "active" in fields:
            payload["active"] = bool(fields["active"])
        self.upsert_source(payload)
        return self.get_source(source_id)

    def sync_sources(self, sources: list[dict[str, Any]]) -> int:
        for source in sources:
            self.upsert_source(source)
        return len(sources)

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return self._decorate_source(self.fetchone("SELECT * FROM sources WHERE source_id=?", (source_id,)))

    def _decorate_source(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        out = dict(row)
        extra = out.get("extra")
        if isinstance(extra, str) and extra.strip():
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}
        if isinstance(extra, dict):
            out["extra"] = extra
            for key in ("authority", "diseases", "registry_id"):
                if extra.get(key) and not out.get(key):
                    out[key] = extra.get(key)
        try:
            from risk_engine import infer_authority

            inferred = infer_authority(out)
            if inferred and not str(out.get("authority") or "").strip():
                out["authority"] = inferred
        except Exception:
            pass
        return out

    def list_sources(self, active_only: bool = False) -> list[dict[str, Any]]:
        if active_only:
            rows = self.fetchall("SELECT * FROM sources WHERE active=1 ORDER BY priority, source_id")
        else:
            rows = self.fetchall("SELECT * FROM sources ORDER BY priority, source_id")
        counts = {
            r["source_id"]: int(r.get("n") or 0)
            for r in self.fetchall("SELECT source_id, COUNT(*) AS n FROM articles GROUP BY source_id")
        }
        out = []
        for row in rows:
            item = self._decorate_source(row) or dict(row)
            method = (item.get("access_method") or "").lower()
            checked = item.get("last_checked") or item.get("last_success")
            if item.get("last_error"):
                status = "error"
            elif method == "scrape" and not checked:
                status = "deferred"
            else:
                status = "ok"
            item["article_count"] = counts.get(item.get("source_id"), 0)
            item["evidence_uses"] = 0
            item["status"] = status
            item["healthy"] = status == "ok"
            out.append(item)
        hosts = self.evidence_host_counts()
        for item in out:
            domain = str(item.get("domain") or "").lower().removeprefix("www.")
            if domain:
                item["evidence_uses"] = int(hosts.get(domain) or 0)
                for host, n in hosts.items():
                    if host == domain or host.endswith("." + domain) or domain.endswith("." + host):
                        if n > item["evidence_uses"]:
                            item["evidence_uses"] = n
        return out

    def mark_source_result(
        self,
        source_id: str,
        *,
        ok: bool,
        error: str | None = None,
        next_check: str | None = None,
        note: str | None = None,
    ) -> None:
        now = _now()
        row = self.get_source(source_id) or {}
        fails = int(row.get("consecutive_failures") or 0)
        if ok:
            fails = 0
            last_error = None
            last_success = now
        else:
            fails += 1
            last_error = error or note or "error"
            last_success = row.get("last_success")
        self.execute(
            """
            UPDATE sources SET last_checked=?, next_check=?, last_error=?,
              last_success=?, consecutive_failures=?
            WHERE source_id=?
            """,
            (now, next_check, last_error, last_success, fails, source_id),
        )
        self._mysql(
            "mark_source_result",
            source_id,
            last_checked=now,
            next_check=next_check,
            last_error=last_error,
            last_success=last_success,
            consecutive_failures=fails,
        )

    # ── articles / dedup ───────────────────────────────────────────────────
    def url_exists(self, url: str) -> bool:
        return self.fetchone("SELECT 1 FROM articles WHERE url=?", (url,)) is not None

    def purge_fake_urls(self) -> dict[str, int]:
        """Quita example.invalid / example.com / localhost de artículos y evidencia."""
        patterns = (
            "%example.invalid%",
            "%example.com%",
            "%social.local%",
            "http://localhost%",
            "https://localhost%",
            "%rumor-vacuna%",
            "%poultryworld.net/demo%",
            "%woah.org/en/demo%",
        )
        deleted_articles = 0
        cleaned_evidence = 0
        for pat in patterns:
            rows = self.fetchall("SELECT content_id FROM articles WHERE url LIKE ?", (pat,))
            for row in rows:
                cid = row["content_id"]
                self.execute(
                    "DELETE FROM evidence WHERE claim_id IN (SELECT claim_id FROM claims WHERE content_id=?)",
                    (cid,),
                )
                self.execute("DELETE FROM claims WHERE content_id=?", (cid,))
                self.execute("DELETE FROM images WHERE content_id=?", (cid,))
                self.execute("DELETE FROM alerts WHERE content_id=?", (cid,))
                self.execute("DELETE FROM entities WHERE content_id=?", (cid,))
                self.execute("DELETE FROM articles WHERE content_id=?", (cid,))
                deleted_articles += 1
            self.execute(
                "UPDATE evidence SET url='' WHERE url LIKE ?",
                (pat,),
            )
            cleaned_evidence += self.conn.total_changes
        self.execute(
            "UPDATE evidence SET url='' WHERE url LIKE 'catalog://%' OR url LIKE 'inapp:%' OR url NOT LIKE 'http%'"
        )
        return {"articles_deleted": deleted_articles, "evidence_cleared": cleaned_evidence}

    def delete_article(self, content_id: str) -> bool:
        """Quita un artículo y sus claims/evidencia/imágenes/alertas/entidades (SQLite + MySQL)."""
        cid = str(content_id or "").strip()
        if not cid or not self.get_article(cid):
            return False
        self.execute(
            "DELETE FROM evidence WHERE claim_id IN (SELECT claim_id FROM claims WHERE content_id=?)",
            (cid,),
        )
        self.execute("DELETE FROM claims WHERE content_id=?", (cid,))
        self.execute("DELETE FROM images WHERE content_id=?", (cid,))
        self.execute("DELETE FROM alerts WHERE content_id=?", (cid,))
        self.execute("DELETE FROM entities WHERE content_id=?", (cid,))
        self.execute("DELETE FROM articles WHERE content_id=?", (cid,))
        self._mysql("delete_article", cid)
        return True

    def public_row(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return row
        out = dict(row)
        raw = out.get("url") or ""
        if raw.startswith("inapp:"):
            out["url"] = ""
            out["in_app_only"] = True
        else:
            out["url"] = stored_article_url(raw)
            out["in_app_only"] = not bool(out["url"])
        cid = str(out.get("content_id") or "").strip()
        path = out.get("thumb_path")
        from database.thumbs import is_generic_visual

        if cid and path and not is_generic_visual(str(path)):
            out["thumb_url"] = f"/thumbs/{cid}"
            out["is_news_thumb"] = True
        else:
            out["thumb_url"] = None
            out["is_news_thumb"] = False
        return out

    def url_hash_exists(self, url_sha256: str) -> bool:
        if self.fetchone("SELECT 1 FROM articles WHERE url_sha256=?", (url_sha256,)) is not None:
            return True
        mirror = getattr(self, "mysql", None)
        if mirror and mirror.connected:
            return bool(mirror.url_hash_exists(url_sha256))
        return False

    def text_hash_exists(self, text_sha256: str) -> bool:
        if not text_sha256:
            return False
        return self.fetchone("SELECT 1 FROM articles WHERE text_sha256=?", (text_sha256,)) is not None

    def insert_article(self, article: dict[str, Any]) -> None:
        raw = (article.get("url") or "").strip()
        url = stored_article_url(raw)
        article = dict(article)
        article["url"] = url
        try:
            self.execute(
                """
                INSERT INTO articles (
                  content_id, source_id, url, url_sha256, text_sha256, title, text,
                  author, language, published_at, collected_at, relevance_score,
                  pipeline_level, raw_format, risk_score, verdict, model_versions,
                  country, source_type, disease_tags, llm_status, llm_explanation, llm_provider
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    article["content_id"],
                    article.get("source_id"),
                    article["url"],
                    article["url_sha256"],
                    article.get("text_sha256"),
                    article.get("title"),
                    article.get("text"),
                    article.get("author"),
                    article.get("language"),
                    article.get("published_at"),
                    article.get("collected_at") or _now(),
                    article.get("relevance_score"),
                    article.get("pipeline_level") or 1,
                    article.get("raw_format"),
                    article.get("risk_score"),
                    article.get("verdict"),
                    _json(article.get("model_versions") or {}),
                    article.get("country"),
                    article.get("source_type"),
                    _json(article.get("disease_tags") or [])
                    if not isinstance(article.get("disease_tags"), str)
                    else article.get("disease_tags"),
                    article.get("llm_status"),
                    article.get("llm_explanation"),
                    article.get("llm_provider"),
                ),
            )
        except sqlite3.IntegrityError:
            return
        self._mysql("insert_article", article)

    def update_article_analysis(self, content_id: str, **fields: Any) -> None:
        if not fields:
            return
        allowed = {
            "relevance_score",
            "pipeline_level",
            "risk_score",
            "verdict",
            "model_versions",
            "language",
            "country",
            "source_type",
            "disease_tags",
            "llm_status",
            "llm_explanation",
            "llm_provider",
            "text",
            "thumb_path",
        }
        sets = []
        vals: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key in {"model_versions", "disease_tags"} and not isinstance(value, str):
                value = _json(value)
            sets.append(f"{key}=?")
            vals.append(value)
        if not sets:
            return
        vals.append(content_id)
        self.execute(f"UPDATE articles SET {', '.join(sets)} WHERE content_id=?", vals)
        payload = {k: v for k, v in fields.items() if k in allowed}
        self._mysql("update_article_analysis", content_id, payload)

    def get_article(self, content_id: str) -> dict[str, Any] | None:
        return self.fetchone("SELECT * FROM articles WHERE content_id=?", (content_id,))

    def resolve_article(self, content_id: str) -> dict[str, Any] | None:
        """Lookup by content_id (CNT-*), case/prefix variants, or numeric rowid/list index."""
        raw = unquote(str(content_id or "")).strip()
        if not raw:
            return None
        candidates: list[str] = [raw]
        if raw.lower().startswith("cnt-"):
            hexpart = raw[4:]
            candidates.extend([f"CNT-{hexpart}", f"cnt-{hexpart}", hexpart])
        elif raw.isalnum():
            candidates.append(f"CNT-{raw}")
        seen: set[str] = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            row = self.get_article(cand)
            if row:
                return row
            row = self.fetchone("SELECT * FROM articles WHERE content_id = ? COLLATE NOCASE", (cand,))
            if row:
                return row
        if raw.isdigit():
            row = self.fetchone("SELECT * FROM articles WHERE rowid = ?", (int(raw),))
            if row:
                return row
            idx = int(raw)
            rows = self.list_articles(limit=max(idx, 80))
            if 1 <= idx <= len(rows):
                return rows[idx - 1]
        return None

    def recent_article_cards(self, limit: int = 5) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for row in self.list_articles(limit=limit):
            pub = self.public_row(row) or row
            cid = pub.get("content_id")
            if not cid:
                continue
            cards.append(
                {
                    "content_id": cid,
                    "title": pub.get("title") or pub.get("url") or cid,
                    "source_id": pub.get("source_id"),
                    "verdict": pub.get("verdict"),
                    "risk_score": pub.get("risk_score"),
                    "country": pub.get("country"),
                }
            )
        return cards

    def list_articles(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.fetchall(
            "SELECT * FROM articles ORDER BY datetime(coalesce(nullif(published_at,''), collected_at)) DESC, collected_at DESC LIMIT ?",
            (limit,),
        )

    def count_articles(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS n FROM articles")
        return int((row or {}).get("n") or 0)

    def load_dedup_hashes(self) -> tuple[set[str], set[str], set[str]]:
        urls = {r["url"] for r in self.fetchall("SELECT url FROM articles") if r.get("url")}
        url_hashes = {r["url_sha256"] for r in self.fetchall("SELECT url_sha256 FROM articles") if r.get("url_sha256")}
        text_hashes = {
            r["text_sha256"] for r in self.fetchall("SELECT text_sha256 FROM articles") if r.get("text_sha256")
        }
        mirror = getattr(self, "mysql", None)
        if mirror and mirror.connected:
            mu, mh, mt = mirror.load_dedup_hashes()
            urls |= mu
            url_hashes |= mh
            text_hashes |= mt
        return urls, url_hashes, text_hashes

    # ── claims / evidence / entities ───────────────────────────────────────
    def insert_claim(self, claim: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO claims (
              claim_id, content_id, text, subject, predicate, object, location,
              animal, verifiable, nli_label, verdict, confidence, model_name, model_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                claim["claim_id"],
                claim.get("content_id"),
                claim.get("text") or claim.get("claim_text") or "",
                claim.get("subject"),
                claim.get("predicate"),
                claim.get("object"),
                claim.get("location"),
                claim.get("animal"),
                1 if claim.get("verifiable", True) else 0,
                claim.get("nli_label"),
                claim.get("verdict"),
                claim.get("confidence"),
                claim.get("model_name"),
                claim.get("model_version"),
            ),
        )
        self._mysql("insert_claim", claim)

    def list_claims(self, content_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if content_id:
            return self.fetchall(
                "SELECT * FROM claims WHERE content_id=? ORDER BY claim_id LIMIT ?",
                (content_id, limit),
            )
        return self.fetchall("SELECT * FROM claims ORDER BY rowid DESC LIMIT ?", (limit,))

    def count_claims(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS n FROM claims")
        return int((row or {}).get("n") or 0)

    def insert_evidence(self, row: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO evidence (
              evidence_id, claim_id, url, source_tier, snippet, stance, collected_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                row["evidence_id"],
                row.get("claim_id"),
                public_http_url(row.get("url")) if not str(row.get("url") or "").startswith("inapp:") else "",
                row.get("source_tier") or row.get("tier"),
                row.get("snippet"),
                row.get("stance"),
                row.get("collected_at") or _now(),
            ),
        )
        self._mysql("insert_evidence", row)

    def evidence_host_counts(self) -> dict[str, int]:
        from urllib.parse import urlparse

        counts: dict[str, int] = {}
        for row in self.fetchall("SELECT url FROM evidence WHERE url IS NOT NULL AND url != ''"):
            try:
                host = (urlparse(str(row.get("url") or "")).hostname or "").lower().removeprefix("www.")
            except Exception:
                continue
            if not host:
                continue
            counts[host] = counts.get(host, 0) + 1
        return counts

    def list_evidence(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        if claim_id:
            return self.fetchall("SELECT * FROM evidence WHERE claim_id=?", (claim_id,))
        return self.fetchall("SELECT * FROM evidence ORDER BY rowid DESC LIMIT 800")

    def insert_entity(self, row: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO entities (
              entity_id, content_id, kind, value, model_name, model_version
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                row["entity_id"],
                row.get("content_id"),
                row["kind"],
                row["value"],
                row.get("model_name"),
                row.get("model_version"),
            ),
        )
        self._mysql("insert_entity", row)

    # ── images ─────────────────────────────────────────────────────────────
    def insert_image(self, row: dict[str, Any]) -> None:
        mv = row.get("model_versions") or {}
        if isinstance(mv, str):
            try:
                mv = json.loads(mv)
            except Exception:
                mv = {}
        cnn = row.get("cnn") if isinstance(row.get("cnn"), dict) else {}
        scores = row.get("cnn_scores") or (cnn or {}).get("scores")
        if scores:
            mv["cnn_scores"] = scores
        self.execute(
            """
            INSERT OR REPLACE INTO images (
              image_id, content_id, storage_key, sha256, phash, mime_type, width, height,
              ocr_text, cnn_class, cnn_confidence, reused, alt_text, source_url, model_versions,
              cnn_scores
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["image_id"],
                row.get("content_id"),
                row["storage_key"],
                row["sha256"],
                row.get("phash"),
                row.get("mime_type"),
                row.get("width"),
                row.get("height"),
                row.get("ocr_text"),
                row.get("cnn_class"),
                row.get("cnn_confidence"),
                1 if row.get("reused") else 0,
                row.get("alt_text"),
                row.get("source_url"),
                _json(mv),
                _json(scores) if scores and not isinstance(scores, str) else (scores or None),
            ),
        )
        self._mysql("insert_image", row)

    def list_images(self, content_id: str | None = None) -> list[dict[str, Any]]:
        if content_id:
            rows = self.fetchall("SELECT * FROM images WHERE content_id=?", (content_id,))
        else:
            rows = self.fetchall("SELECT * FROM images ORDER BY rowid DESC LIMIT 240")
        return [self.decorate_image(r) for r in rows]

    def get_image(self, image_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM images WHERE image_id=?", (image_id,))
        if not row and image_id and not image_id.isdigit() and len(image_id) >= 6:
            row = self.fetchone(
                "SELECT * FROM images WHERE storage_key LIKE ? OR sha256 LIKE ?",
                (f"%{image_id}%", f"{image_id}%"),
            )
        return self.decorate_image(row) if row else None

    def count_images(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS n FROM images")
        return int((row or {}).get("n") or 0)

    def phash_neighbors(self, phash: str, exclude_id: str | None = None) -> list[dict[str, Any]]:
        if not phash:
            return []
        rows = self.fetchall("SELECT image_id, content_id, phash, sha256 FROM images WHERE phash IS NOT NULL AND phash!=''")
        if exclude_id:
            rows = [r for r in rows if r["image_id"] != exclude_id]
        return rows

    # ── alerts / reviews / audit / narratives ──────────────────────────────
    def insert_alert(self, row: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO alerts (
              alert_id, content_id, claim_id, risk_score, verdict, explanation,
              status, model_name, model_version, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["alert_id"],
                row.get("content_id"),
                row.get("claim_id"),
                row.get("risk_score"),
                row.get("verdict"),
                _json(row.get("explanation") or {}),
                row.get("status") or "pending_review",
                row.get("model_name"),
                row.get("model_version"),
                row.get("created_at") or _now(),
            ),
        )
        self._mysql("insert_alert", row)

    def list_alerts(self, limit: int = 50, status: str | None = None, include: bool = False) -> list[dict[str, Any]]:
        if status:
            rows = self.fetchall(
                "SELECT * FROM alerts WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            rows = self.fetchall("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
        if not include:
            return rows
        corpus = self.fetchall(
            "SELECT content_id, source_id, title, url FROM articles ORDER BY rowid DESC LIMIT 220"
        )
        sources = {
            str(r["source_id"]): r
            for r in self.fetchall("SELECT source_id, type, category, domain, name FROM sources")
        }
        out = []
        for row in rows:
            item = dict(row)
            art = self.get_article(item.get("content_id") or "")
            claims = self.list_claims(item.get("content_id") or "", limit=3)
            evidence = []
            for claim in claims:
                cid = claim.get("claim_id")
                if cid:
                    evidence.extend(self.list_evidence(cid))
            item["title"] = (art or {}).get("title") or item.get("content_id")
            item["article_verdict"] = (art or {}).get("verdict")
            item["claims"] = claims
            item["evidence"] = [self.public_row(e) or e for e in evidence[:3]]
            from database.review_contrast import attach_review_contrast

            attach_review_contrast(item, claims, evidence, corpus=corpus, sources=sources)
            out.append(item)
        return out

    def alerts_for_article(self, content_id: str) -> list[dict[str, Any]]:
        if not content_id:
            return []
        return self.fetchall(
            "SELECT * FROM alerts WHERE content_id=? ORDER BY created_at DESC",
            (content_id,),
        )

    def count_alerts(self, status: str | None = None) -> int:
        if status:
            row = self.fetchone("SELECT COUNT(*) AS n FROM alerts WHERE status=?", (status,))
        else:
            row = self.fetchone("SELECT COUNT(*) AS n FROM alerts")
        return int((row or {}).get("n") or 0)

    def source_hitl_shift(self, source_id: str) -> float:
        if not source_id:
            return 0.0
        rows = self.fetchall(
            """
            SELECT a.human_label AS human_label
            FROM alerts a
            JOIN articles art ON art.content_id = a.content_id
            WHERE art.source_id=? AND a.status='reviewed'
              AND a.human_label IN ('validado', 'descartado')
            """,
            (source_id,),
        )
        delta = 0.0
        for row in rows:
            label = str(row.get("human_label") or "")
            if label == "validado":
                delta -= 8.0
            elif label == "descartado":
                delta += 10.0
        return max(-40.0, min(40.0, delta))

    def review_alert(
        self,
        alert_id: str,
        *,
        human_label: str,
        reason: str = "",
        analyst: str = "analista",
    ) -> dict[str, Any] | None:
        alert = self.fetchone("SELECT * FROM alerts WHERE alert_id=?", (alert_id,))
        if not alert:
            return None
        now = _now()
        label = str(human_label or "").strip().lower()
        if label == "modificado":
            self.execute(
                """
                UPDATE alerts SET human_label=?, human_reason=?
                WHERE alert_id=?
                """,
                (label, reason, alert_id),
            )
            self.audit("alert", alert_id, "human_review", {"label": label, "analyst": analyst, "open": True})
            cid = alert.get("content_id")
            if cid:
                article = self.get_article(cid)
                if article:
                    versions = article.get("model_versions")
                    if isinstance(versions, str):
                        try:
                            versions = json.loads(versions)
                        except json.JSONDecodeError:
                            versions = {}
                    versions = dict(versions or {})
                    why = versions.get("risk_why") if isinstance(versions.get("risk_why"), dict) else {}
                    why = dict(why)
                    why["rule"] = "hitl_modificado"
                    why["hitl"] = {"label": label, "reason": reason}
                    versions["risk_why"] = why
                    self.update_article_analysis(cid, verdict="REVISIÓN HUMANA", model_versions=versions)
            return self.fetchone("SELECT * FROM alerts WHERE alert_id=?", (alert_id,))

        self.execute(
            """
            UPDATE alerts SET status=?, human_label=?, human_reason=?, reviewed_at=?
            WHERE alert_id=?
            """,
            ("reviewed", label, reason, now, alert_id),
        )
        review_id = "RV-" + hashlib.sha256(f"{alert_id}:{now}".encode()).hexdigest()[:12]
        self.insert_review(
            {
                "review_id": review_id,
                "alert_id": alert_id,
                "prediction": alert.get("verdict"),
                "human_label": label,
                "reason": reason,
                "analyst": analyst,
                "used_for_retraining": 1,
            }
        )
        cid = alert.get("content_id")
        if cid:
            try:
                from risk_engine import apply_hitl_label

                spec = apply_hitl_label(label, reason)
            except Exception:
                spec = {
                    "validado": {"verdict": "RESPALDADO", "risk_score": 22, "rule": "hitl_validado"},
                    "descartado": {"verdict": "CONTRADICHO", "risk_score": 82, "rule": "hitl_descartado"},
                }.get(label)
                if spec:
                    spec = {**spec, "reason": reason}
            if spec:
                article = self.get_article(cid)
                versions = {}
                if article:
                    versions = article.get("model_versions") or {}
                    if isinstance(versions, str):
                        try:
                            versions = json.loads(versions)
                        except json.JSONDecodeError:
                            versions = {}
                    versions = dict(versions or {})
                why = versions.get("risk_why") if isinstance(versions.get("risk_why"), dict) else {}
                why = dict(why)
                why["rule"] = spec["rule"]
                why["score"] = spec["risk_score"]
                why["hitl"] = {"label": label, "reason": reason}
                versions["risk_why"] = why
                self.update_article_analysis(
                    cid,
                    verdict=spec["verdict"],
                    risk_score=spec["risk_score"],
                    model_versions=versions,
                )
        self.audit("alert", alert_id, "human_review", {"label": label, "analyst": analyst})
        self._mysql(
            "update_alert_review",
            alert_id,
            human_label=label,
            reason=reason,
            reviewed_at=now,
        )
        return self.fetchone("SELECT * FROM alerts WHERE alert_id=?", (alert_id,))

    def review_article(
        self,
        content_id: str,
        *,
        human_label: str,
        reason: str = "",
        analyst: str = "analista",
    ) -> dict[str, Any] | None:
        art = self.get_article(content_id)
        if not art:
            return None
        pending = [
            a
            for a in self.alerts_for_article(content_id)
            if str(a.get("status") or "") == "pending_review"
        ]
        if pending:
            return self.review_alert(
                pending[0]["alert_id"],
                human_label=human_label,
                reason=reason,
                analyst=analyst,
            )
        alert_id = "AL-" + hashlib.sha256(f"{content_id}:{_now()}:{human_label}".encode()).hexdigest()[:12]
        self.insert_alert(
            {
                "alert_id": alert_id,
                "content_id": content_id,
                "risk_score": art.get("risk_score"),
                "verdict": art.get("verdict"),
                "status": "pending_review",
                "model_name": "hitl",
                "model_version": "sala",
            }
        )
        return self.review_alert(
            alert_id,
            human_label=human_label,
            reason=reason,
            analyst=analyst,
        )

    def insert_review(self, row: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO reviews (
              review_id, alert_id, prediction, human_label, reason, analyst,
              used_for_retraining, created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                row["review_id"],
                row.get("alert_id"),
                row.get("prediction"),
                row.get("human_label"),
                row.get("reason"),
                row.get("analyst"),
                1 if row.get("used_for_retraining") else 0,
                row.get("created_at") or _now(),
            ),
        )
        self._mysql("insert_review", row)

    def audit(self, subject_type: str, subject_id: str, action: str, payload: Any = None) -> None:
        created = _now()
        self.execute(
            "INSERT INTO audit_logs (subject_type, subject_id, action, payload, created_at) VALUES (?,?,?,?,?)",
            (subject_type, subject_id, action, _json(payload or {}), created),
        )
        self._mysql(
            "insert_audit",
            {
                "subject_type": subject_type,
                "subject_id": subject_id,
                "action": action,
                "payload": payload or {},
                "created_at": created,
            },
        )

    def list_audit(self, subject_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if subject_id:
            return self.fetchall(
                "SELECT * FROM audit_logs WHERE subject_id=? ORDER BY audit_id DESC LIMIT ?",
                (subject_id, limit),
            )
        return self.fetchall("SELECT * FROM audit_logs ORDER BY audit_id DESC LIMIT ?", (limit,))

    def upsert_narrative(self, row: dict[str, Any]) -> None:
        prev = self.fetchone("SELECT claim_count FROM narratives WHERE narrative_id=?", (row["narrative_id"],))
        prev_count = int((prev or {}).get("claim_count") or 0)
        extra = row.get("extra")
        if extra is None:
            extra = {
                k: row.get(k)
                for k in ("state_label", "priority", "first_seen", "last_seen", "country_n", "sources_n", "classification")
                if row.get(k) is not None
            }
        self.execute(
            """
            INSERT INTO narratives (
              narrative_id, label, keywords, claim_count, prev_count, growth_pct,
              cycle_id, model_name, model_version, updated_at, description, state, extra
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(narrative_id) DO UPDATE SET
              label=excluded.label, keywords=excluded.keywords,
              claim_count=excluded.claim_count, prev_count=excluded.prev_count,
              growth_pct=excluded.growth_pct, cycle_id=excluded.cycle_id,
              model_name=excluded.model_name, model_version=excluded.model_version,
              updated_at=excluded.updated_at, description=excluded.description,
              state=excluded.state, extra=excluded.extra
            """,
            (
                row["narrative_id"],
                row["label"],
                _json(row.get("keywords") or []),
                int(row.get("claim_count") or 0),
                prev_count,
                row.get("growth_pct"),
                row.get("cycle_id"),
                row.get("model_name"),
                row.get("model_version"),
                _now(),
                row.get("description"),
                row.get("state"),
                extra if isinstance(extra, str) else _json(extra or {}),
            ),
        )
        self._mysql("upsert_narrative", row, prev_count)

    def list_narratives(self) -> list[dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM narratives ORDER BY claim_count DESC")
        out = []
        for row in rows:
            item = dict(row)
            extra = item.get("extra")
            if isinstance(extra, str) and extra.strip():
                try:
                    extra = json.loads(extra)
                except json.JSONDecodeError:
                    extra = {}
            if isinstance(extra, dict):
                item["extra"] = extra
                for key in ("priority", "state_label", "first_seen", "last_seen", "classification"):
                    if extra.get(key) and not item.get(key):
                        item[key] = extra.get(key)
            out.append(item)
        return out

    def _term_id(self, category: str, term: str) -> str:
        raw = f"{category}|{term}".strip().lower()
        return "KW-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def seed_keyword_bank(self) -> None:
        n = self.fetchone("SELECT COUNT(*) AS n FROM keyword_terms")
        if int((n or {}).get("n") or 0) == 0:
            nar = str(FRAMEWORK_ROOT / "ai-service" / "narratives")
            if nar not in sys.path:
                sys.path.insert(0, nar)
            from lexicon import yaml_term_rows

            for row in yaml_term_rows():
                self.upsert_keyword_term(row)
        self.apply_keyword_bank()

    def apply_keyword_bank(self) -> None:
        nar = str(FRAMEWORK_ROOT / "ai-service" / "narratives")
        if nar not in sys.path:
            sys.path.insert(0, nar)
        from lexicon import apply_term_rows

        apply_term_rows(self.list_keyword_terms())

    def list_keyword_terms(self, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            return self.fetchall(
                "SELECT * FROM keyword_terms WHERE category=? ORDER BY category, term",
                (category,),
            )
        return self.fetchall("SELECT * FROM keyword_terms ORDER BY category, term")

    def upsert_keyword_term(self, row: dict[str, Any]) -> dict[str, Any]:
        term = str(row.get("term") or "").strip()
        category = str(row.get("category") or "").strip()
        if not term or not category:
            raise ValueError("term y category son obligatorios")
        tid = str(row.get("term_id") or self._term_id(category, term))
        active = 1 if row.get("active", True) not in {0, False, "0", "false", "no"} else 0
        try:
            weight = max(1, min(5, int(row.get("weight") or 2)))
        except (TypeError, ValueError):
            weight = 2
        self.execute(
            """
            INSERT INTO keyword_terms (term_id, term, category, label, weight, active, updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(term_id) DO UPDATE SET
              term=excluded.term, category=excluded.category, label=excluded.label,
              weight=excluded.weight, active=excluded.active, updated_at=excluded.updated_at
            """,
            (tid, term, category, row.get("label") or category, weight, active, _now()),
        )
        self.apply_keyword_bank()
        return self.fetchone("SELECT * FROM keyword_terms WHERE term_id=?", (tid,)) or {}

    def delete_keyword_term(self, term_id: str) -> bool:
        existing = self.fetchone("SELECT term_id FROM keyword_terms WHERE term_id=?", (term_id,))
        if not existing:
            return False
        self.execute("DELETE FROM keyword_terms WHERE term_id=?", (term_id,))
        self.apply_keyword_bank()
        return True

    def persist_narrative_pack(self, pack: dict[str, Any], cycle_id: str) -> int:
        n = 0
        for row in pack.get("narratives") or []:
            nid = str(row.get("narrative_id") or "")
            if not nid:
                continue
            self.upsert_narrative(
                {
                    "narrative_id": nid,
                    "label": row.get("label") or nid,
                    "keywords": row.get("keywords") or [],
                    "claim_count": int(row.get("volume") or row.get("claims_n") or 0),
                    "growth_pct": row.get("growth_pct"),
                    "cycle_id": cycle_id,
                    "model_name": "narrative_surveillance",
                    "model_version": "v1",
                    "description": row.get("description"),
                    "state": row.get("state"),
                    "state_label": row.get("state_label"),
                    "priority": row.get("priority"),
                    "first_seen": row.get("first_seen"),
                    "last_seen": row.get("last_seen"),
                    "classification": row.get("classification"),
                }
            )
            self.execute("DELETE FROM narrative_members WHERE narrative_id=?", (nid,))
            for art in row.get("articles") or []:
                cid = str(art.get("content_id") or "")
                if cid:
                    self.execute(
                        "INSERT OR IGNORE INTO narrative_members (narrative_id, content_id) VALUES (?,?)",
                        (nid, cid),
                    )
            n += 1
        return n

    def insert_mining_run(self, row: dict[str, Any]) -> None:
        extra = row.get("extra")
        self.execute(
            """
            INSERT INTO mining_runs (
              cycle_id, started_at, finished_at, articles_new, images_new, errors, extra
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                row.get("cycle_id"),
                row.get("started_at") or _now(),
                row.get("finished_at"),
                int(row.get("articles_new") or 0),
                int(row.get("images_new") or 0),
                int(row.get("errors") or 0),
                extra if isinstance(extra, str) else _json(extra or {}),
            ),
        )
        self._mysql("insert_mining_run", row)

    def last_mining_run(self) -> dict[str, Any] | None:
        mirror = getattr(self, "mysql", None)
        if mirror and mirror.connected:
            row = mirror.last_mining_run()
            if row:
                return row
        return self.fetchone("SELECT * FROM mining_runs ORDER BY run_id DESC LIMIT 1")

    def insert_cnn_sample(self, row: dict[str, Any]) -> None:
        try:
            self.execute(
                """
                INSERT OR IGNORE INTO cnn_samples (
                  sample_id, path, class, split, source_article_id, image_id, sha256, confidence, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["sample_id"],
                    row["path"],
                    row["class"],
                    row["split"],
                    row.get("source_article_id"),
                    row.get("image_id"),
                    row.get("sha256"),
                    row.get("confidence"),
                    row.get("created_at") or _now(),
                ),
            )
        except sqlite3.IntegrityError:
            return
        self._mysql("insert_cnn_sample", row)

    def count_cnn_samples(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS n FROM cnn_samples")
        return int((row or {}).get("n") or 0)

    def kpis(self) -> dict[str, Any]:
        def _n(sql: str, params: Iterable[Any] = ()) -> int:
            row = self.fetchone(sql, params)
            return int((row or {}).get("n") or 0)

        mysql_on = bool(getattr(self, "mysql", None) and self.mysql.connected)
        mysql_counts = self.mysql.counts() if mysql_on else None
        last = self.last_mining_run() or {}
        local = {
            "articles": self.count_articles(),
            "claims": self.count_claims(),
            "alerts": self.count_alerts(),
            "alerts_pending": self.count_alerts("pending_review"),
            "images": self.count_images(),
            "sources": len(self.list_sources(active_only=True)),
            "youtube": _n("SELECT COUNT(*) AS n FROM articles WHERE raw_format='youtube'"),
            "social": _n("SELECT COUNT(*) AS n FROM articles WHERE raw_format='social'"),
            "reviews": _n("SELECT COUNT(*) AS n FROM reviews"),
            "narratives": _n("SELECT COUNT(*) AS n FROM narratives"),
            "entities": _n("SELECT COUNT(*) AS n FROM entities"),
            "cnn_samples": self.count_cnn_samples(),
            "mining_runs": _n("SELECT COUNT(*) AS n FROM mining_runs"),
        }
        counts = dict(local)
        if mysql_counts:
            for key, value in mysql_counts.items():
                counts[key] = value
        last_mine = last.get("started_at") or last.get("finished_at")
        if hasattr(last_mine, "isoformat"):
            last_mine = last_mine.isoformat()
        counts.update(
            {
                "mysql": mysql_on,
                "backend": "mysql" if mysql_on else "sqlite",
                "last_mine": str(last_mine) if last_mine else None,
                **self.capture_quality(),
                **self.mysql_lag_info(),
            }
        )
        return counts

    def capture_quality(self) -> dict[str, Any]:
        rows = self.fetchall("SELECT raw_format, length(coalesce(text,'')) AS n FROM articles")
        total = len(rows)
        by_format: dict[str, int] = {}
        rss = 0
        seed = 0
        no_body = 0
        for row in rows:
            fmt = (row.get("raw_format") or "unknown").lower()
            by_format[fmt] = by_format.get(fmt, 0) + 1
            if fmt in {"rss", "api"}:
                rss += 1
            if fmt in {"seed", "corpus", "fixture", "demo"}:
                seed += 1
            if int(row.get("n") or 0) < 500:
                no_body += 1
        return {
            "docs": total,
            "rss": rss,
            "seed": seed,
            "no_body": no_body,
            "pct_rss": round(100 * rss / total) if total else 0,
            "pct_seed": round(100 * seed / total) if total else 0,
            "pct_no_body": round(100 * no_body / total) if total else 0,
            "by_format": by_format,
        }

    def mysql_lag_info(self) -> dict[str, Any]:
        sqlite_max = (self.fetchone("SELECT MAX(collected_at) AS m FROM articles") or {}).get("m")
        mysql_on = bool(getattr(self, "mysql", None) and self.mysql.connected)
        mysql_max = None
        error = None
        if mysql_on:
            try:
                row = self.mysql._fetchone("SELECT MAX(collected_at) AS m FROM articles")
                mysql_max = (row or {}).get("m")
            except Exception as exc:  # noqa: BLE001
                error = str(exc)[:200]
        lag = None
        if sqlite_max and mysql_max:
            try:
                a = datetime.fromisoformat(str(sqlite_max).replace("Z", "+00:00").split(".")[0])
                b = datetime.fromisoformat(str(mysql_max).replace("Z", "+00:00").split(".")[0])
                if a.tzinfo is None:
                    a = a.replace(tzinfo=timezone.utc)
                if b.tzinfo is None:
                    b = b.replace(tzinfo=timezone.utc)
                lag = max(0, int((a - b).total_seconds()))
            except Exception:
                lag = None
        stale = bool(mysql_on and (lag is None or lag >= 300 or error))
        if mysql_on and sqlite_max and not mysql_max:
            stale = True
        return {
            "mysql_connected": mysql_on,
            "mysql_lag_seconds": lag,
            "mysql_stale": stale,
            "mysql_max_collected": str(mysql_max) if mysql_max else None,
            "sqlite_max_collected": str(sqlite_max) if sqlite_max else None,
            "mysql_error": error,
        }

    CNN_CLASSES = (
        "OFFICIAL_DOCUMENT",
        "NEWS_SCREENSHOT",
        "SOCIAL_MEDIA",
        "MEME",
        "INFOGRAPHIC",
        "PHOTOGRAPH",
        "ANIMAL_HEALTH_CONTENT",
        "POTENTIALLY_MANIPULATED",
    )

    DISEASE_META = {
        "gusano_barrenador": {"label": "Gusano barrenador", "short": "Gusano"},
        "gripe_aviar": {"label": "Gripe aviar", "short": "Gripe aviar"},
        "fiebre_porcina_clasica": {"label": "Peste porcina clásica", "short": "PPC"},
    }

    DISEASE_KEYWORDS = {
        "gusano_barrenador": (
            "gusano barrenador", "screwworm", "cochliomyia", "myiasis", "miasis", "nws", "gbg",
        ),
        "gripe_aviar": (
            "gripe aviar", "influenza aviar", "avian influenza", "bird flu", "h5n1", "h5n2", "hpai",
        ),
        "fiebre_porcina_clasica": (
            "peste porcina", "fiebre porcina", "classical swine fever", "hog cholera", "csfv",
        ),
    }

    def decorate_image(self, row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        scores = None
        raw_scores = row.get("cnn_scores")
        if raw_scores:
            try:
                scores = json.loads(raw_scores) if isinstance(raw_scores, str) else raw_scores
            except Exception:
                scores = None
        if not scores:
            mv = row.get("model_versions") or "{}"
            try:
                parsed = json.loads(mv) if isinstance(mv, str) else (mv or {})
            except Exception:
                parsed = {}
            scores = parsed.get("cnn_scores") if isinstance(parsed, dict) else None
        label = row.get("cnn_class") or "PHOTOGRAPH"
        conf = float(row.get("cnn_confidence") or 0.55)
        if not scores or not isinstance(scores, dict):
            rest = max(0.05, 1.0 - max(conf, 0.4))
            other = rest / max(1, len(self.CNN_CLASSES) - 1)
            scores = {name: round(other, 4) for name in self.CNN_CLASSES}
            if label in scores:
                scores[label] = round(max(conf, 0.42), 4)
        out["cnn_scores"] = scores
        out["file_url"] = f"/images/{row.get('image_id')}"
        phash = (row.get("phash") or "").strip()
        out["phash_short"] = phash[:8] if phash else ""
        fusion = {}
        mv = row.get("model_versions") or {}
        if isinstance(mv, str):
            try:
                mv = json.loads(mv)
            except Exception:
                mv = {}
        if isinstance(mv, dict):
            fusion = mv.get("visual_fusion") or {}
            out["encoder"] = mv.get("encoder") or (fusion.get("encoder") if isinstance(fusion, dict) else None)
            out["visual_role"] = mv.get("role")
        if isinstance(fusion, dict) and fusion:
            out["visual_fusion"] = fusion
            out["reuse_similarity_pct"] = fusion.get("reuse_similarity_pct")
            out["reuse_hamming"] = fusion.get("reuse_hamming")
            out["animal_health_relevance"] = fusion.get("animal_health_relevance")
        if row.get("reused") and out.get("reuse_similarity_pct") is not None:
            out["reuse_label"] = (
                f"Reuso visual {out['reuse_similarity_pct']}% "
                f"(Hamming {out.get('reuse_hamming')}/{fusion.get('reuse_bits') or '?'})"
            )
        elif row.get("reused"):
            out["reuse_label"] = "Imagen reutilizada"
        else:
            out["reuse_label"] = None
        out["is_news_thumb"] = self.is_news_thumb(out)
        return out

    def is_news_thumb(self, row: dict[str, Any]) -> bool:
        """Foto real o miniatura YouTube — nunca el dataset sintético del CNN."""
        key = str(row.get("storage_key") or "").replace("\\", "/").lower()
        src = str(row.get("source_url") or "").replace("\\", "/").lower()
        mime = str(row.get("mime_type") or "").lower()
        blob = f"{key} {src}"
        name = Path(str(row.get("storage_key") or "")).name.lower()
        if name.startswith("ph_") or name.endswith(".svg") or "svg" in mime:
            return False
        if "models/cnn" in blob or "cnn/dataset" in blob:
            return False
        extra = name + " " + Path(str(row.get("source_url") or "")).name.lower()
        if extra.startswith("corpus_") or " corpus_" in extra or extra.startswith("fb_") or " fb_" in extra or "demo_seed_" in extra:
            return False
        if mime and not any(token in mime for token in ("jpeg", "jpg", "png", "webp", "svg")):
            return False
        if src.startswith("http://") or src.startswith("https://"):
            return True
        return bool(row.get("image_id") and row.get("storage_key"))

    def article_diseases(self, article: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        raw = article.get("disease_tags")
        if raw:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                parsed = []
            if isinstance(parsed, str):
                parsed = [parsed]
            tags = [str(t).strip() for t in (parsed or []) if str(t).strip()]
        blob = f"{article.get('title') or ''} {article.get('text') or ''}".lower()
        for did, kws in self.DISEASE_KEYWORDS.items():
            if did in tags:
                continue
            if any(kw in blob for kw in kws):
                tags.append(did)
        return tags

    def disease_label(self, did: str) -> str:
        meta = self.DISEASE_META.get(did)
        if meta:
            return meta["label"]
        return did.replace("_", " ")

    def _matches_disease(self, article: dict[str, Any], disease: str | None) -> bool:
        if not disease:
            return True
        needle = disease.strip().lower()
        tags = [t.lower() for t in self.article_diseases(article)]
        if needle in tags:
            return True
        for did, meta in self.DISEASE_META.items():
            aliases = {did, meta["label"].lower(), meta["short"].lower()}
            if needle in aliases and did in tags:
                return True
        blob = f"{article.get('title') or ''} {article.get('text') or ''}".lower()
        for did, kws in self.DISEASE_KEYWORDS.items():
            aliases = {did, self.DISEASE_META[did]["label"].lower(), self.DISEASE_META[did]["short"].lower(), *kws}
            if needle in aliases:
                return did in tags or any(kw in blob for kw in kws)
        return needle in blob

    def query_articles(self, q=None, *, limit: int | None = 400) -> list[dict[str, Any]]:
        from database.query_filters import (
            ArticleQuery,
            article_day,
            origin_matches,
            published_sort_key,
            stance_matches,
            verdict_matches,
        )

        if q is None:
            q = ArticleQuery()
        elif not isinstance(q, ArticleQuery):
            q = ArticleQuery(disease=str(q) if q else None)

        published = "datetime(coalesce(nullif(published_at,''), collected_at)) DESC, collected_at DESC"
        order_sql = {
            "risk_score": "risk_score DESC, collected_at DESC",
            "published_at": published,
            "newest": published,
            "collected_at": "collected_at DESC",
        }.get(q.order, published)

        sql = "SELECT * FROM articles WHERE 1=1"
        params: list[Any] = []
        if q.source_id:
            sql += " AND source_id = ?"
            params.append(q.source_id)
        if q.raw_format:
            sql += " AND lower(coalesce(raw_format,'')) = ?"
            params.append(q.raw_format.lower())
        if q.risk_null:
            sql += " AND risk_score IS NULL"
        else:
            if q.risk_min is not None:
                sql += " AND risk_score >= ?"
                params.append(q.risk_min)
            if q.risk_max is not None:
                sql += " AND risk_score <= ?"
                params.append(q.risk_max)
        sql += f" ORDER BY {order_sql}"
        fetch_limit = 8000 if limit is None else max(limit * 8, 400)
        sql += " LIMIT ?"
        params.append(fetch_limit)

        stance_ids: set[str] | None = None
        if q.stance:
            stance_ids = set()
            for claim in self.fetchall("SELECT content_id, nli_label FROM claims"):
                if stance_matches(claim.get("nli_label"), q.stance):
                    stance_ids.add(claim["content_id"])

        source_rows = self.fetchall("SELECT * FROM sources")
        source_names = {
            s["source_id"]: f"{s.get('name') or ''} {s.get('domain') or ''}"
            for s in source_rows
        }
        source_meta = {s["source_id"]: s for s in source_rows}
        from relevance import should_skip

        out: list[dict[str, Any]] = []
        for row in self.fetchall(sql, params):
            row = dict(row)
            if q.verdict and not verdict_matches(row.get("verdict"), q.verdict):
                continue
            if q.origin and not origin_matches(row, q.origin):
                continue
            if q.disease and not self._matches_disease(row, q.disease):
                continue
            if q.country:
                from database.geo import resolve_article_country

                extra = " ".join((c.get("location") or "") for c in self.list_claims(row["content_id"], limit=6))
                code = resolve_article_country(row, extra)
                needle = q.country.strip().upper()
                stored = str(row.get("country") or "").strip().upper()
                if needle not in {code, stored, stored[:2]}:
                    continue
            if stance_ids is not None and row.get("content_id") not in stance_ids:
                continue
            if q.q:
                name = source_names.get(row.get("source_id"), "")
                blob = f"{row.get('title') or ''} {row.get('text') or ''} {row.get('source_id') or ''} {name}".lower()
                if q.q.lower() not in blob:
                    continue
            fmt = str(row.get("raw_format") or "").lower()
            if fmt not in {"fixture", "corpus"}:
                src = source_meta.get(row.get("source_id"))
                title = row.get("title") or ""
                blob = f"{title} {row.get('text') or ''}"
                if should_skip(blob, source=src, title=title):
                    continue
            day = article_day(row)
            if q.date_from and (not day or day < str(q.date_from)[:10]):
                continue
            if q.date_to and (not day or day > str(q.date_to)[:10]):
                continue
            row["disease_list"] = self.article_diseases(row)
            row["day"] = day
            out.append(row)
        if q.order == "risk_score":
            out.sort(key=lambda r: (r.get("risk_score") is None, -(r.get("risk_score") or 0), r.get("collected_at") or ""), reverse=False)
        elif q.order == "collected_at":
            out.sort(key=lambda r: r.get("collected_at") or "", reverse=True)
        else:
            out.sort(key=published_sort_key, reverse=True)
        if limit is not None:
            out = out[:limit]
        return out

    def filtered_articles(self, disease: str | None = None, limit: int = 400, q=None) -> list[dict[str, Any]]:
        from database.query_filters import ArticleQuery

        if q is None:
            q = ArticleQuery(disease=disease)
        elif disease and not q.disease:
            q.disease = disease
        return self.query_articles(q, limit=limit)

    def paged_articles(self, q=None) -> dict[str, Any]:
        from database.query_filters import ArticleQuery

        q = q or ArticleQuery()
        rows = self.query_articles(q, limit=None)
        total = len(rows)
        start = (q.page - 1) * q.page_size
        page_rows = rows[start : start + q.page_size]
        return {
            "count": total,
            "page": q.page,
            "page_size": q.page_size,
            "articles": page_rows,
        }

    def disease_counts(self, disease: str | None = None, q=None) -> list[dict[str, Any]]:
        counts: dict[str, int] = {k: 0 for k in self.DISEASE_META}
        extras: dict[str, int] = {}
        for row in self.filtered_articles(disease, limit=8000, q=q):
            for tag in self.article_diseases(row):
                if tag in counts:
                    counts[tag] += 1
                else:
                    extras[tag] = extras.get(tag, 0) + 1
        cards = [
            {
                "id": did,
                "label": meta["label"],
                "short": meta["short"],
                "menciones": counts[did],
            }
            for did, meta in self.DISEASE_META.items()
        ]
        other_n = 0
        for tag, n in sorted(extras.items(), key=lambda x: -x[1]):
            if n:
                cards.append({"id": tag, "label": self.disease_label(tag), "short": tag, "menciones": n})
            other_n += n
        if other_n:
            cards.append({"id": "otras", "label": "Otras", "short": "Otras", "menciones": other_n})
        return cards

    def geo_table(self, disease: str | None = None, q=None) -> list[dict[str, Any]]:
        from database.geo import resolve_article_place

        buckets: dict[str, dict[str, Any]] = {}
        for row in self.filtered_articles(disease, limit=8000, q=q):
            extra = f"{row.get('title') or ''} {(row.get('text') or '')[:800]}"
            info = resolve_article_place(row, extra)
            key = info.get("place_id") or info.get("country") or "XX"
            bucket = buckets.setdefault(
                key,
                {
                    **info,
                    "count": 0,
                    "articles": [],
                    "disease_counts": {},
                    "risk_sum": 0,
                    "risk_n": 0,
                    "first_seen": None,
                    "unlocated": bool(info.get("unlocated")),
                },
            )
            bucket["count"] += 1
            for tag in self.article_diseases(row):
                counts = bucket["disease_counts"]
                counts[tag] = counts.get(tag, 0) + 1
            score = row.get("risk_score")
            if score is not None:
                try:
                    bucket["risk_sum"] += int(score)
                    bucket["risk_n"] += 1
                except (TypeError, ValueError):
                    pass
            day = str(row.get("published_at") or row.get("collected_at") or "")[:10]
            if len(day) == 10 and (bucket["first_seen"] is None or day < bucket["first_seen"]):
                bucket["first_seen"] = day
            if len(bucket["articles"]) < 8:
                bucket["articles"].append(
                    {
                        "content_id": row["content_id"],
                        "title": row.get("title") or row.get("url"),
                        "risk_score": row.get("risk_score"),
                    }
                )
        out: list[dict[str, Any]] = []
        for bucket in buckets.values():
            counts: dict[str, int] = bucket.pop("disease_counts")
            risk_n = bucket.pop("risk_n")
            risk_sum = bucket.pop("risk_sum")
            diseases = sorted(counts, key=lambda d: (-counts[d], d))
            bucket["diseases"] = diseases
            bucket["disease"] = diseases[0] if diseases else None
            bucket["risk_mean"] = round(risk_sum / risk_n) if risk_n else None
            out.append(bucket)
        return sorted(out, key=lambda r: -r["count"])

    def chart_payload(self, disease: str | None = None, q=None) -> dict[str, Any]:
        from datetime import date, timedelta

        from database.query_filters import (
            ORIGIN_LABELS,
            ORIGIN_ORDER,
            VERDICT_CHART_LABELS,
            VERDICT_CHART_ORDER,
            ArticleQuery,
            article_day,
            content_origin,
            verdict_chart_key,
        )

        if q is None:
            q = ArticleQuery(disease=disease)
        elif disease and not q.disease:
            q.disease = disease
        articles = self.query_articles(q, limit=None)
        empty = not articles
        series_ids = list(self.DISEASE_META.keys())
        for extra in q.compare:
            if extra not in series_ids:
                series_ids.append(extra)
        volume_map: dict[str, int] = {did: 0 for did in series_ids}
        extras_vol: dict[str, int] = {}
        origin_map: dict[str, int] = {key: 0 for key in ORIGIN_ORDER}
        verdict_map: dict[str, int] = {key: 0 for key, _ in VERDICT_CHART_ORDER}
        buckets: dict[str, list[dict[str, Any]]] = {}
        claim_ids = {c["content_id"] for c in self.fetchall("SELECT DISTINCT content_id FROM claims")}
        without_claims = 0
        for row in articles:
            day = article_day(row)
            if day:
                buckets.setdefault(day, []).append(row)
            tags = self.article_diseases(row)
            if not tags:
                extras_vol["otras"] = extras_vol.get("otras", 0) + 1
            for tag in tags:
                if tag in volume_map:
                    volume_map[tag] += 1
                else:
                    extras_vol[tag] = extras_vol.get(tag, 0) + 1
            oid = content_origin(row)
            origin_map[oid] = origin_map.get(oid, 0) + 1
            vid = verdict_chart_key(row.get("verdict"))
            verdict_map[vid] = verdict_map.get(vid, 0) + 1
            if row.get("content_id") not in claim_ids:
                without_claims += 1

        alert_days: dict[str, int] = {}
        for alert in self.fetchall("SELECT content_id, created_at FROM alerts"):
            day = str(alert.get("created_at") or "")[:10]
            if day:
                alert_days[day] = alert_days.get(day, 0) + 1

        iso_days = [d for d in buckets if len(d) == 10 and d[4:5] == "-" and d[7:8] == "-"]
        start = article_day({"published_at": q.date_from}) or None
        end = article_day({"published_at": q.date_to}) or None
        if iso_days:
            data_min, data_max = min(iso_days), max(iso_days)
            end = end or data_max
            if not start:
                try:
                    last = date.fromisoformat(end)
                    start = max(data_min, (last - timedelta(days=90)).isoformat())
                except ValueError:
                    start = data_min
            try:
                span = (date.fromisoformat(end) - date.fromisoformat(start)).days if start and end else 0
            except ValueError:
                span = 0
            if span > 400:
                try:
                    start = (date.fromisoformat(end) - timedelta(days=400)).isoformat()
                except ValueError:
                    start = data_min
        by_day: list[dict[str, Any]] = []
        try:
            cur = date.fromisoformat(start) if start else None
            last = date.fromisoformat(end) if end else None
        except ValueError:
            cur = last = None
        if cur is not None and last is not None and not empty:
            while cur <= last:
                key = cur.isoformat()
                rows = buckets.get(key, [])
                scores = [int(r["risk_score"]) for r in rows if r.get("risk_score") is not None]
                item: dict[str, Any] = {
                    "day": key,
                    "count": len(rows),
                    "missing": key not in buckets,
                    "risk_mean": round(sum(scores) / len(scores), 1) if scores else None,
                    "risk_unknown": sum(1 for r in rows if r.get("risk_score") is None),
                    "alerts": alert_days.get(key, 0),
                    "sample_titles": [(r.get("title") or r.get("content_id") or "")[:90] for r in rows[:3]],
                    "filter": {"from": key, "to": key, "disease": q.disease},
                }
                for did in series_ids:
                    item[did] = sum(1 for r in rows if did in self.article_diseases(r))
                by_day.append(item)
                cur += timedelta(days=1)

        risk_hist = [
            {"bucket": "0-20", "count": 0, "filter": {"risk_min": 0, "risk_max": 20}},
            {"bucket": "21-40", "count": 0, "filter": {"risk_min": 21, "risk_max": 40}},
            {"bucket": "41-60", "count": 0, "filter": {"risk_min": 41, "risk_max": 60}},
            {"bucket": "61-80", "count": 0, "filter": {"risk_min": 61, "risk_max": 80}},
            {"bucket": "81-100", "count": 0, "filter": {"risk_min": 81, "risk_max": 100}},
            {"bucket": "sin_puntuacion", "count": 0, "filter": {"risk_null": True}},
        ]
        for row in articles:
            score = row.get("risk_score")
            if score is None:
                risk_hist[-1]["count"] += 1
                continue
            n = int(score)
            if n <= 20:
                risk_hist[0]["count"] += 1
            elif n <= 40:
                risk_hist[1]["count"] += 1
            elif n <= 60:
                risk_hist[2]["count"] += 1
            elif n <= 80:
                risk_hist[3]["count"] += 1
            else:
                risk_hist[4]["count"] += 1

        ids = {a["content_id"] for a in articles}
        stance = {"Supported": 0, "Contradicted": 0, "Unknown": 0}
        for claim in self.fetchall("SELECT content_id, nli_label FROM claims"):
            if ids and claim.get("content_id") not in ids:
                continue
            label = (claim.get("nli_label") or "Unknown").lower()
            if "contrad" in label:
                stance["Contradicted"] += 1
            elif "support" in label or "respald" in label:
                stance["Supported"] += 1
            else:
                stance["Unknown"] += 1

        volume = []
        for did, n in volume_map.items():
            meta = self.DISEASE_META.get(did, {"label": self.disease_label(did), "short": did})
            volume.append(
                {
                    "id": did,
                    "name": meta.get("short") or meta["label"],
                    "label": meta["label"],
                    "count": n,
                    "filter": {"disease": did},
                }
            )
        for tag, n in extras_vol.items():
            volume.append(
                {
                    "id": tag,
                    "name": self.disease_label(tag),
                    "label": self.disease_label(tag),
                    "count": n,
                    "filter": {"disease": tag},
                }
            )

        annotations = []
        for run in self.fetchall("SELECT started_at, extra FROM mining_runs ORDER BY started_at DESC LIMIT 8"):
            day = str(run.get("started_at") or "")[:10]
            if day:
                annotations.append({"day": day, "label": "ciclo RSS", "kind": "mine"})

        origin_volume = [
            {
                "id": oid,
                "name": ORIGIN_LABELS[oid],
                "label": ORIGIN_LABELS[oid],
                "count": origin_map.get(oid, 0),
                "filter": {"origin": oid},
            }
            for oid in ORIGIN_ORDER
        ]
        for oid, n in origin_map.items():
            if oid in ORIGIN_LABELS:
                continue
            origin_volume.append(
                {
                    "id": oid,
                    "name": oid.replace("_", " "),
                    "label": oid.replace("_", " "),
                    "count": n,
                    "filter": {"origin": oid},
                }
            )

        verdict_volume = []
        seen_verdicts: set[str] = set()
        for vid, label in VERDICT_CHART_ORDER:
            seen_verdicts.add(vid)
            verdict_volume.append(
                {
                    "id": vid,
                    "name": label,
                    "label": label,
                    "count": verdict_map.get(vid, 0),
                    "filter": {"verdict": vid},
                }
            )
        for vid, n in verdict_map.items():
            if vid in seen_verdicts:
                continue
            verdict_volume.append(
                {
                    "id": vid,
                    "name": VERDICT_CHART_LABELS.get(vid, vid.replace("_", " ")),
                    "label": VERDICT_CHART_LABELS.get(vid, vid.replace("_", " ")),
                    "count": n,
                    "filter": {"verdict": vid},
                }
            )

        scored_bins = [b for b in risk_hist if b["bucket"] != "sin_puntuacion" and b["count"] > 0]
        top_risk = max(scored_bins, key=lambda b: b["count"]) if scored_bins else None
        risk_note = f"El tramo de riesgo más común es {top_risk['bucket']}." if top_risk else None

        return {
            "empty": empty,
            "n": len(articles),
            "articles_without_claims": without_claims,
            "db_empty": self.count_articles() == 0,
            "filter": q.as_filter_dict(),
            "series": [{"id": v["id"], "name": v["label"]} for v in volume if v["id"] in series_ids],
            "volume_by_disease": volume,
            "volume_by_origin": origin_volume,
            "volume_by_verdict": verdict_volume,
            "volume_by_day": [{"day": d["day"], "count": d["count"]} for d in by_day],
            "by_day": by_day,
            "risk_histogram": risk_hist,
            "risk_note": risk_note,
            "stance": [
                {"name": k, "value": v, "filter": {"stance": k}}
                for k, v in stance.items()
            ],
            "annotations": annotations,
        }

    def sparkline_series(self, disease: str | None = None, q=None) -> dict[str, list[int]]:
        charts = self.chart_payload(disease, q=q)
        days = [int(p["count"]) for p in charts.get("by_day") or charts["volume_by_day"]]
        return {
            "articles": days[-14:] or [0],
            "claims": days[-14:] or [0],
            "risk": [int(p["count"]) for p in charts["risk_histogram"] if p["bucket"] != "sin_puntuacion"] or [0],
            "diseases": [int(p["count"]) for p in charts["volume_by_disease"]] or [0],
        }

    def network_graph(self, disease: str | None = None, q=None, limit: int = 40) -> dict[str, Any]:
        articles = self.filtered_articles(disease, limit=220, q=q)
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []
        seen_edges: set[tuple[str, str]] = set()

        def add_node(nid: str, label: str, group: str, value: int = 1, **extra: Any) -> None:
            if nid in nodes:
                nodes[nid]["value"] = int(nodes[nid].get("value") or 1) + value
                return
            nodes[nid] = {"id": nid, "label": label, "group": group, "value": value, **extra}

        def add_edge(a: str, b: str, label: str = "") -> None:
            key = (a, b) if a < b else (b, a)
            if a == b or key in seen_edges:
                return
            seen_edges.add(key)
            edges.append({"from": a, "to": b, "label": label})

        if not articles:
            return {"nodes": [], "edges": [], "empty": True, "sample": 0, "universe": 0}

        narratives = self.list_narratives()
        nar_kws: list[tuple[str, str, list[str]]] = []
        for nar in narratives:
            if int(nar.get("claim_count") or 0) <= 0:
                continue
            raw = nar.get("keywords") or "[]"
            try:
                kws = json.loads(raw) if isinstance(raw, str) else (raw or [])
            except Exception:
                kws = []
            nar_kws.append((nar["narrative_id"], nar.get("label") or nar["narrative_id"], [str(k).lower() for k in kws]))
            add_node(
                nar["narrative_id"],
                nar.get("label") or nar["narrative_id"],
                "narrative",
                int(nar.get("claim_count") or 1),
                filter={"q": nar.get("label") or nar["narrative_id"]},
            )

        source_hits: dict[str, int] = {}
        article_nodes = 0
        for row in articles:
            sid = row.get("source_id") or "desconocido"
            cid = row.get("content_id") or ""
            src = self.get_source(sid) if sid != "desconocido" else None
            source_name = (src or {}).get("name") or (src or {}).get("domain") or sid
            source_hits[sid] = source_hits.get(sid, 0) + 1
            add_node(f"SRC-{sid}", source_name, "source", 1, source_id=sid, filter={"source": sid})
            tags = self.article_diseases(row)
            if cid and article_nodes < max(10, min(limit, 80)):
                add_node(cid, (row.get("title") or cid)[:42], "article", 2)
                add_edge(cid, f"SRC-{sid}", "publicó")
                article_nodes += 1
            blob = f"{row.get('title') or ''} {row.get('text') or ''}".lower()
            for did in tags or []:
                meta = self.DISEASE_META.get(did, {"short": self.disease_label(did)})
                add_node(f"DIS-{did}", meta.get("short") or did, "disease", 1, filter={"disease": did})
                add_edge(f"SRC-{sid}", f"DIS-{did}", "habla de")
                if cid:
                    add_edge(cid, f"DIS-{did}", "menciona")
            for nid, label, kws in nar_kws:
                if any(kw and kw in blob for kw in kws):
                    for did in tags or ["misc"]:
                        add_edge(
                            f"DIS-{did}" if did != "misc" else f"SRC-{sid}",
                            nid,
                            "entra en" if did != "misc" else "alimenta",
                        )

        top_sources = {f"SRC-{s}" for s, _ in sorted(source_hits.items(), key=lambda x: -x[1])[:28]}
        keep = {n for n, meta in nodes.items() if meta["group"] != "source" or n in top_sources}
        nodes = {k: v for k, v in nodes.items() if k in keep}
        edges = [e for e in edges if e["from"] in nodes and e["to"] in nodes]
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "empty": not edges,
            "sample": article_nodes,
            "universe": len(articles),
        }

    def similar_articles(self, content_id: str, limit: int = 10) -> list[dict[str, Any]]:
        article = self.get_article(content_id)
        if not article:
            return []
        tags = set(self.article_diseases(article))
        images = self.list_images(content_id)
        phashes = [im.get("phash") or "" for im in images if im.get("phash")]
        scored: list[tuple[int, dict[str, Any]]] = []
        for other in self.fetchall("SELECT * FROM articles WHERE content_id!=? LIMIT 250", (content_id,)):
            score = 0
            reasons: list[str] = []
            other_tags = set(self.article_diseases(other))
            shared = tags & other_tags
            if shared:
                score += 4 * len(shared)
                reasons.append("misma enfermedad")
            others_imgs = self.fetchall(
                "SELECT phash FROM images WHERE content_id=? AND phash IS NOT NULL",
                (other["content_id"],),
            )
            for im in others_imgs:
                ph = im.get("phash") or ""
                for mine in phashes:
                    if mine and ph and mine == ph:
                        score += 8
                        reasons.append("pHash idéntico")
                        break
                    if mine and ph and len(mine) == len(ph):
                        dist = sum(a != b for a, b in zip(mine, ph))
                        if dist <= 10:
                            score += 5
                            reasons.append("pHash cercano")
                            break
            if article.get("source_id") and article.get("source_id") == other.get("source_id"):
                score += 1
            if score:
                scored.append(
                    (
                        score,
                        {
                            "content_id": other["content_id"],
                            "title": other.get("title") or other.get("url"),
                            "score": score,
                            "reasons": list(dict.fromkeys(reasons)),
                            "country": other.get("country"),
                            "risk_score": other.get("risk_score"),
                        },
                    )
                )
        scored.sort(key=lambda x: -x[0])
        return [row for _, row in scored[:limit]]

    def article_graph(self, content_id: str) -> dict[str, Any]:
        article = self.get_article(content_id)
        if not article:
            return {"nodes": [], "edges": []}
        nodes = [
            {
                "id": content_id,
                "label": (article.get("title") or "artículo")[:48],
                "group": "article",
                "value": 6,
            }
        ]
        edges = []
        for neigh in self.similar_articles(content_id, limit=8):
            nodes.append(
                {
                    "id": neigh["content_id"],
                    "label": (neigh.get("title") or neigh["content_id"])[:42],
                    "group": "similar",
                    "value": 2 + int(neigh.get("score") or 1),
                }
            )
            edges.append({"from": content_id, "to": neigh["content_id"], "label": ", ".join(neigh.get("reasons") or [])})
        for did in self.article_diseases(article):
            nid = f"DIS-{did}"
            nodes.append({"id": nid, "label": self.DISEASE_META.get(did, {}).get("short") or did, "group": "disease", "value": 3})
            edges.append({"from": content_id, "to": nid})
        return {"nodes": nodes, "edges": edges}

    def grouped_entities(self, content_id: str) -> dict[str, list[str]]:
        groups = {"DISEASE": [], "ANIMAL": [], "COUNTRY": [], "ORG": []}
        seen: set[tuple[str, str]] = set()
        kind_map = {
            "DISEASE": "DISEASE",
            "ANIMAL": "ANIMAL",
            "COUNTRY": "COUNTRY",
            "LOCATION": "COUNTRY",
            "ORG": "ORG",
            "ORGANIZATION": "ORG",
        }
        for row in self.fetchall("SELECT kind, value FROM entities WHERE content_id=?", (content_id,)):
            kind = kind_map.get((row.get("kind") or "").upper())
            value = str(row.get("value") or "").strip()
            if not kind or not value:
                continue
            key = (kind, value.lower())
            if key in seen:
                continue
            seen.add(key)
            groups[kind].append(value)
        article = self.get_article(content_id) or {}
        for did in self.article_diseases(article):
            label = self.disease_label(did)
            if label.lower() not in {v.lower() for v in groups["DISEASE"]} and did.lower() not in {v.lower() for v in groups["DISEASE"]}:
                groups["DISEASE"].append(label)
        cleaned: list[str] = []
        seen_l: set[str] = set()
        for value in groups["DISEASE"]:
            key = value.lower().replace(" ", "_")
            label = self.DISEASE_META.get(value, {}).get("label") or self.DISEASE_META.get(key, {}).get("label") or value.replace("_", " ")
            if label.lower() in seen_l:
                continue
            seen_l.add(label.lower())
            cleaned.append(label)
        groups["DISEASE"] = cleaned
        return groups

    def stats_payload(self, disease: str | None = None, q=None) -> dict[str, Any]:
        kpis = self.kpis()
        articles = self.filtered_articles(disease, limit=8000, q=q)
        if disease or q is not None:
            ids = {a["content_id"] for a in articles}
            kpis = {
                **kpis,
                "articles": len(articles),
                "claims": len([c for c in self.fetchall("SELECT content_id FROM claims") if c["content_id"] in ids]),
                "images": len([i for i in self.fetchall("SELECT content_id FROM images") if i["content_id"] in ids]),
            }
        return {
            "kpis": kpis,
            "sparklines": self.sparkline_series(disease, q=q),
            "diseases": self.disease_counts(),
            "filter": (q.as_filter_dict() if q is not None else disease),
            "mysql": bool(getattr(self, "mysql", None) and self.mysql.connected),
            "mysql_stale": bool(kpis.get("mysql_stale")),
            "mysql_lag_seconds": kpis.get("mysql_lag_seconds"),
            "last_mine": kpis.get("last_mine"),
            "capture": {
                "docs": kpis.get("docs"),
                "rss": kpis.get("rss"),
                "seed": kpis.get("seed"),
                "no_body": kpis.get("no_body"),
                "pct_rss": kpis.get("pct_rss"),
                "pct_seed": kpis.get("pct_seed"),
                "pct_no_body": kpis.get("pct_no_body"),
                "by_format": kpis.get("by_format"),
            },
        }

    def explanation_quality(self, article: dict[str, Any], claims: list[dict[str, Any]], evidence: list[dict[str, Any]], images: list[dict[str, Any]]) -> dict[str, Any]:
        score = 18
        notes: list[str] = []
        if claims:
            score += 18
        nli_ok = sum(1 for c in claims if (c.get("nli_label") or "").lower() not in {"", "unknown"})
        if nli_ok:
            score += 18
            notes.append(f"{nli_ok} claims con stance NLI")
        else:
            notes.append("Pocos claims con stance claro")
        if evidence:
            score += 16
            notes.append(f"{len(evidence)} fragmentos de evidencia")
        else:
            notes.append("Sin evidencia oficial vinculada")
        if images:
            score += 12
        llm_on = bool(article.get("llm_explanation")) and (article.get("llm_provider") or "") not in {"", "local"}
        if llm_on:
            score += 18
            notes.append("Hay explicación LLM")
        else:
            notes.append("Ollama no activo: explicación local por solapamiento y NLI")
        score = min(100, score)
        band = "alta" if score >= 70 else "media" if score >= 45 else "baja"
        return {"score": score, "band": band, "notes": notes, "llm_used": llm_on}

    def local_explanation(self, article: dict[str, Any], claims: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> str:
        expl = str(article.get("llm_explanation") or "").strip()
        if expl and "solapamiento" not in expl.lower() and len(expl) >= 80:
            return expl
        grouped = self.grouped_entities(article.get("content_id") or "")
        diseases = ", ".join(grouped.get("DISEASE") or []) or ", ".join(
            self.disease_label(d) for d in self.article_diseases(article)
        ) or "salud animal"
        animals = ", ".join(grouped.get("ANIMAL") or []) or "especie no precisada"
        country = ", ".join(grouped.get("COUNTRY") or []) or (article.get("country") or "ámbito no determinado")
        orgs = ", ".join(grouped.get("ORG") or []) or "WOAH, FAO"
        verdict = article.get("verdict") or "Sin verificar"
        risk = article.get("risk_score")
        risk_txt = f"riesgo {risk}/100" if risk is not None else "riesgo no calculado"
        title = article.get("title") or "este documento"
        return (
            f"Lectura del caso «{title}»: se clasifica como {verdict} con {risk_txt}. "
            f"Enfermedad: {diseases}. Especie: {animals}. País o ámbito: {country}. "
            f"Organizaciones de referencia: {orgs}. "
            f"{'Hay ' + str(len(evidence)) + ' fragmentos oficiales.' if evidence else ''} "
            "Plantilla a partir de entidades, veredicto y riesgo; no decide la verdad."
        )

    def list_by_format(self, raw_format: str, limit: int = 80) -> list[dict[str, Any]]:
        return self.fetchall(
            "SELECT * FROM articles WHERE raw_format=? ORDER BY collected_at DESC LIMIT ?",
            (raw_format, limit),
        )


def append_raw(source_id: str, payload: dict[str, Any]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{source_id}.jsonl"
    line = json.dumps({"fetched_at": _now(), **payload}, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path
