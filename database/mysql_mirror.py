"""Cliente MySQL (warehouse). Dual-write: si no hay conexión, solo SQLite.

Log claro: "MySQL no conectado". Reintenta cada 60s. Sin secretos en código:
lee MYSQL_* del entorno o de .env (copia de .env.example).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

from bootstrap import FRAMEWORK_ROOT

SCHEMA_PATH = FRAMEWORK_ROOT / "database" / "mysql" / "schema.sql"
_LOGGED_DOWN = False
_MIRROR: "MysqlMirror | None" = None
RECONNECT_EVERY = 60.0


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _load_env_file() -> None:
    path = FRAMEWORK_ROOT / ".env"
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


def mysql_enabled() -> bool:
    flag = (os.environ.get("TNB_MYSQL") or "1").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return True


def mysql_config() -> dict[str, Any]:
    _load_env_file()
    return {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT") or 3306),
        "user": os.environ.get("MYSQL_USER", "tnb"),
        "password": os.environ.get("MYSQL_PASSWORD", "tnb"),
        "database": os.environ.get("MYSQL_DATABASE", "newsbreakers"),
        "charset": "utf8mb4",
        "autocommit": True,
        "connect_timeout": 3,
        "read_timeout": 15,
        "write_timeout": 15,
    }


def _json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _dt(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower().startswith("sin fecha") or text.lower() in {"none", "null"}:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for cand in candidates:
        try:
            dt = datetime.fromisoformat(cand)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            continue
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        return None


class MysqlMirror:
    def __init__(self) -> None:
        self.connected = False
        self.error: str | None = None
        self._conn: Any = None
        self._last_try = 0.0
        self._last_write_error: str | None = None
        self._lock = threading.RLock()

    def connect(self) -> "MysqlMirror":
        self._try_connect(force=True)
        return self

    def _try_connect(self, force: bool = False) -> None:
        global _LOGGED_DOWN
        now = time.time()
        if not force and self.connected:
            return
        if not force and (now - self._last_try) < RECONNECT_EVERY:
            return
        self._last_try = now
        if not mysql_enabled():
            self.connected = False
            self.error = "TNB_MYSQL=0"
            if not _LOGGED_DOWN:
                print("[mysql] MySQL no conectado (TNB_MYSQL=0) — se usa solo SQLite", file=sys.stderr)
                _LOGGED_DOWN = True
            return
        cfg = mysql_config()
        try:
            import pymysql

            self._conn = pymysql.connect(**cfg)
            self._ensure_schema()
            self.connected = True
            self.error = None
            _LOGGED_DOWN = False
            print(
                f"[mysql] conectado {cfg['database']}@{cfg['host']}:{cfg['port']}",
                file=sys.stderr,
            )
        except Exception as exc:  # noqa: BLE001
            self.connected = False
            self._conn = None
            self.error = str(exc)[:240]
            if not _LOGGED_DOWN:
                print(f"[mysql] MySQL no conectado — se usa solo SQLite ({self.error})", file=sys.stderr)
                _LOGGED_DOWN = True

    def reconnect_if_due(self) -> None:
        with self._lock:
            if self.connected and self._conn is not None:
                try:
                    self._conn.ping(reconnect=True)
                    return
                except Exception:
                    self.connected = False
                    self._conn = None
            self._try_connect(force=True)

    def _ensure_schema(self) -> None:
        if not SCHEMA_PATH.is_file() or self._conn is None:
            return
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        parts: list[str] = []
        for raw in sql.split(";"):
            stmt = raw.strip()
            if not stmt or stmt.startswith("--"):
                continue
            upper = stmt.upper()
            if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
                continue
            parts.append(stmt)
        cur = self._conn.cursor()
        try:
            for stmt in parts:
                cur.execute(stmt)
            self._conn.commit()
        finally:
            cur.close()
        extra = [
            "ALTER TABLE alerts ADD COLUMN human_label VARCHAR(64)",
            "ALTER TABLE alerts ADD COLUMN human_reason TEXT",
            "ALTER TABLE alerts ADD COLUMN reviewed_at DATETIME(6)",
            "ALTER TABLE articles ADD COLUMN thumb_path TEXT",
        ]
        cur = self._conn.cursor()
        try:
            for stmt in extra:
                try:
                    cur.execute(stmt)
                except Exception:
                    pass
            self._conn.commit()
        finally:
            cur.close()

    def _exec(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self._lock:
            self.reconnect_if_due()
            if not self.connected or self._conn is None:
                return
            try:
                cur = self._conn.cursor()
                try:
                    cur.execute(sql, tuple(params))
                    self._conn.commit()
                finally:
                    cur.close()
            except Exception as exc:  # noqa: BLE001
                self._last_write_error = f"{sql[:40]}: {exc}"[:240]
                print(f"[mysql] escritura fallida: {self._last_write_error}", file=sys.stderr)

    def _fetchone(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self._lock:
            self.reconnect_if_due()
            if not self.connected or self._conn is None:
                return None
            try:
                import pymysql.cursors

                cur = self._conn.cursor(pymysql.cursors.DictCursor)
                try:
                    cur.execute(sql, tuple(params))
                    row = cur.fetchone()
                    return dict(row) if row else None
                finally:
                    cur.close()
            except Exception:
                self.connected = False
                self._conn = None
                return None

    def _fetchall(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            self.reconnect_if_due()
            if not self.connected or self._conn is None:
                return []
            try:
                import pymysql.cursors

                cur = self._conn.cursor(pymysql.cursors.DictCursor)
                try:
                    cur.execute(sql, tuple(params))
                    return [dict(r) for r in (cur.fetchall() or [])]
                finally:
                    cur.close()
            except Exception:
                self.connected = False
                self._conn = None
                return []

    def counts(self) -> dict[str, int] | None:
        self.reconnect_if_due()
        if not self.connected:
            return None
        out: dict[str, int] = {}
        mapping = {
            "articles": "SELECT COUNT(*) AS n FROM articles",
            "claims": "SELECT COUNT(*) AS n FROM claims",
            "alerts": "SELECT COUNT(*) AS n FROM alerts",
            "images": "SELECT COUNT(*) AS n FROM images",
            "sources": "SELECT COUNT(*) AS n FROM sources WHERE active=1",
            "entities": "SELECT COUNT(*) AS n FROM entities",
            "narratives": "SELECT COUNT(*) AS n FROM narratives",
            "cnn_samples": "SELECT COUNT(*) AS n FROM cnn_samples",
            "reviews": "SELECT COUNT(*) AS n FROM reviews",
            "audit_logs": "SELECT COUNT(*) AS n FROM audit_logs",
        }
        for key, sql in mapping.items():
            row = self._fetchone(sql)
            out[key] = int((row or {}).get("n") or 0)
        pending = self._fetchone("SELECT COUNT(*) AS n FROM alerts WHERE status=%s", ("pending_review",))
        out["alerts_pending"] = int((pending or {}).get("n") or 0)
        return out

    def load_dedup_hashes(self) -> tuple[set[str], set[str], set[str]]:
        urls = {r["url"] for r in self._fetchall("SELECT url FROM articles") if r.get("url")}
        url_hashes = {
            r["url_sha256"] for r in self._fetchall("SELECT url_sha256 FROM articles") if r.get("url_sha256")
        }
        text_hashes = {
            r["text_sha256"] for r in self._fetchall("SELECT text_sha256 FROM articles") if r.get("text_sha256")
        }
        return urls, url_hashes, text_hashes

    def url_hash_exists(self, url_sha256: str) -> bool:
        if not url_sha256:
            return False
        row = self._fetchone("SELECT 1 AS n FROM articles WHERE url_sha256=%s", (url_sha256,))
        return row is not None

    def last_mining_run(self) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM mining_runs ORDER BY run_id DESC LIMIT 1")

    def upsert_source(self, source: dict[str, Any], existing: dict[str, Any] | None = None) -> None:
        extra = source.get("extra")
        if extra is None:
            extra = {k: source.get(k) for k in ("diseases", "authority", "registry_id")}
        self._exec(
            """
            INSERT INTO sources (
              source_id, name, domain, country, language, type, category, priority,
              access_method, rss_url, base_url, parser_version, frequency_minutes,
              confidence, active, last_checked, next_check, last_error, last_success,
              consecutive_failures, extra
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              name=VALUES(name), domain=VALUES(domain), country=VALUES(country),
              language=VALUES(language), type=VALUES(type), category=VALUES(category),
              priority=VALUES(priority), access_method=VALUES(access_method),
              rss_url=VALUES(rss_url), base_url=VALUES(base_url),
              parser_version=VALUES(parser_version), frequency_minutes=VALUES(frequency_minutes),
              confidence=VALUES(confidence), active=VALUES(active), extra=VALUES(extra)
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
                _dt((existing or {}).get("last_checked") or source.get("last_checked")),
                _dt((existing or {}).get("next_check") or source.get("next_check")),
                (existing or {}).get("last_error") or source.get("last_error"),
                _dt((existing or {}).get("last_success")),
                (existing or {}).get("consecutive_failures") or 0,
                _json(extra),
            ),
        )

    def mark_source_result(
        self,
        source_id: str,
        *,
        last_checked: str,
        next_check: str | None,
        last_error: str | None,
        last_success: str | None,
        consecutive_failures: int,
    ) -> None:
        self._exec(
            """
            UPDATE sources SET last_checked=%s, next_check=%s, last_error=%s,
              last_success=%s, consecutive_failures=%s
            WHERE source_id=%s
            """,
            (_dt(last_checked), _dt(next_check), last_error, _dt(last_success), consecutive_failures, source_id),
        )

    def insert_article(self, article: dict[str, Any]) -> None:
        tags = article.get("disease_tags")
        self._exec(
            """
            INSERT INTO articles (
              content_id, source_id, url, url_sha256, text_sha256, title, text,
              author, language, published_at, collected_at, relevance_score,
              pipeline_level, raw_format, risk_score, verdict, model_versions,
              country, source_type, disease_tags, llm_status, llm_explanation, llm_provider
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE title=VALUES(title)
            """,
            (
                article["content_id"],
                article.get("source_id"),
                article.get("url") or "",
                article.get("url_sha256"),
                article.get("text_sha256"),
                article.get("title"),
                article.get("text"),
                article.get("author"),
                article.get("language"),
                _dt(article.get("published_at")),
                _dt(article.get("collected_at")) or _now(),
                article.get("relevance_score"),
                article.get("pipeline_level") or 1,
                article.get("raw_format"),
                article.get("risk_score"),
                article.get("verdict"),
                _json(article.get("model_versions") or {}),
                article.get("country"),
                article.get("source_type"),
                _json(tags) if not isinstance(tags, str) else tags,
                article.get("llm_status"),
                article.get("llm_explanation"),
                article.get("llm_provider"),
            ),
        )

    def update_article_analysis(self, content_id: str, fields: dict[str, Any]) -> None:
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
            sets.append(f"{key}=%s")
            vals.append(value)
        if not sets:
            return
        vals.append(content_id)
        self._exec(f"UPDATE articles SET {', '.join(sets)} WHERE content_id=%s", vals)

    def delete_article(self, content_id: str) -> None:
        cid = str(content_id or "").strip()
        if not cid:
            return
        self._exec(
            "DELETE FROM evidence WHERE claim_id IN (SELECT claim_id FROM claims WHERE content_id=%s)",
            (cid,),
        )
        self._exec("DELETE FROM claims WHERE content_id=%s", (cid,))
        self._exec("DELETE FROM images WHERE content_id=%s", (cid,))
        self._exec("DELETE FROM alerts WHERE content_id=%s", (cid,))
        self._exec("DELETE FROM entities WHERE content_id=%s", (cid,))
        self._exec("DELETE FROM articles WHERE content_id=%s", (cid,))

    def insert_claim(self, claim: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO claims (
              claim_id, content_id, text, subject, predicate, object, location,
              animal, verifiable, nli_label, verdict, confidence, model_name, model_version
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              nli_label=VALUES(nli_label), verdict=VALUES(verdict), confidence=VALUES(confidence)
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

    def insert_evidence(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO evidence (
              evidence_id, claim_id, url, source_tier, snippet, stance, collected_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE snippet=VALUES(snippet)
            """,
            (
                row["evidence_id"],
                row.get("claim_id"),
                row.get("url") or "",
                row.get("source_tier") or row.get("tier"),
                row.get("snippet"),
                row.get("stance"),
                _dt(row.get("collected_at")) or _now(),
            ),
        )

    def insert_entity(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO entities (
              entity_id, content_id, kind, value, model_name, model_version
            ) VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE value=VALUES(value)
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

    def insert_image(self, row: dict[str, Any]) -> None:
        scores = row.get("cnn_scores")
        if not scores and isinstance(row.get("cnn"), dict):
            scores = row["cnn"].get("scores")
        mv = row.get("model_versions") or {}
        self._exec(
            """
            INSERT INTO images (
              image_id, content_id, storage_key, sha256, phash, mime_type, width, height,
              ocr_text, cnn_class, cnn_confidence, reused, alt_text, source_url, model_versions,
              cnn_scores
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              cnn_class=VALUES(cnn_class), cnn_confidence=VALUES(cnn_confidence)
            """,
            (
                row["image_id"],
                row.get("content_id"),
                row.get("storage_key") or "",
                row.get("sha256"),
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
                _json(mv) if not isinstance(mv, str) else mv,
                _json(scores),
            ),
        )

    def insert_alert(self, row: dict[str, Any]) -> None:
        expl = row.get("explanation")
        self._exec(
            """
            INSERT INTO alerts (
              alert_id, content_id, claim_id, risk_score, verdict, explanation,
              status, model_name, model_version, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE risk_score=VALUES(risk_score)
            """,
            (
                row["alert_id"],
                row.get("content_id"),
                row.get("claim_id"),
                row.get("risk_score"),
                row.get("verdict"),
                _json(expl) if not isinstance(expl, str) else expl,
                row.get("status") or "pending_review",
                row.get("model_name"),
                row.get("model_version"),
                _dt(row.get("created_at")) or _now(),
            ),
        )

    def upsert_narrative(self, row: dict[str, Any], prev_count: int = 0) -> None:
        self._exec(
            """
            INSERT INTO narratives (
              narrative_id, label, keywords, claim_count, prev_count, growth_pct,
              cycle_id, model_name, model_version, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              label=VALUES(label), keywords=VALUES(keywords),
              claim_count=VALUES(claim_count), prev_count=VALUES(prev_count),
              growth_pct=VALUES(growth_pct), cycle_id=VALUES(cycle_id),
              model_name=VALUES(model_name), model_version=VALUES(model_version),
              updated_at=VALUES(updated_at)
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
            ),
        )

    def insert_mining_run(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO mining_runs (
              cycle_id, started_at, finished_at, articles_new, images_new, errors, extra
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                row.get("cycle_id"),
                _dt(row.get("started_at")) or _now(),
                _dt(row.get("finished_at")),
                int(row.get("articles_new") or 0),
                int(row.get("images_new") or 0),
                int(row.get("errors") or 0),
                _json(row.get("extra") or {}),
            ),
        )

    def insert_cnn_sample(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO cnn_samples (
              sample_id, path, class, split, source_article_id, image_id, sha256, confidence, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE confidence=VALUES(confidence)
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
                _dt(row.get("created_at")) or _now(),
            ),
        )

    def insert_review(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO reviews (
              review_id, alert_id, prediction, human_label, reason, analyst,
              used_for_retraining, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              human_label=VALUES(human_label), reason=VALUES(reason)
            """,
            (
                row["review_id"],
                row.get("alert_id"),
                row.get("prediction"),
                row.get("human_label"),
                row.get("reason"),
                row.get("analyst"),
                1 if row.get("used_for_retraining") else 0,
                _dt(row.get("created_at")) or _now(),
            ),
        )

    def insert_audit(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO audit_logs (subject_type, subject_id, action, payload, created_at)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                row.get("subject_type"),
                row.get("subject_id"),
                row.get("action"),
                _json(row.get("payload") or {}),
                _dt(row.get("created_at")) or _now(),
            ),
        )

    def update_alert_review(
        self,
        alert_id: str,
        *,
        human_label: str,
        reason: str = "",
        reviewed_at: str | None = None,
    ) -> None:
        self._exec(
            """
            UPDATE alerts SET status=%s, human_label=%s, human_reason=%s, reviewed_at=%s
            WHERE alert_id=%s
            """,
            ("reviewed", human_label, reason, _dt(reviewed_at) or _now(), alert_id),
        )


def get_mirror() -> MysqlMirror:
    global _MIRROR
    if _MIRROR is None:
        _MIRROR = MysqlMirror().connect()
    else:
        _MIRROR.reconnect_if_due()
    return _MIRROR


def mysql_status() -> dict[str, Any]:
    mirror = get_mirror()
    return {
        "connected": bool(mirror.connected),
        "error": None if mirror.connected else (mirror.error or "MySQL no conectado"),
        "counts": mirror.counts() if mirror.connected else None,
    }
