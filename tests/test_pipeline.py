from pathlib import Path

from database.store import Store
from pipeline.run import run_cycle


def test_sqlite_schema_and_audit(tmp_path):
    db = tmp_path / "tnb.db"
    store = Store(db)
    store.upsert_source(
        {
            "source_id": "SRC-TEST",
            "name": "Test",
            "domain": "example.org",
            "access_method": "rss",
            "rss_url": "https://example.org/rss",
            "parser_version": "parser_v1",
            "frequency_minutes": 15,
            "active": True,
        }
    )
    row = store.get_source("SRC-TEST")
    assert row["parser_version"] == "parser_v1"
    store.audit("source", "SRC-TEST", "checked", {"ok": True})
    logs = store.list_audit("SRC-TEST")
    assert logs and logs[0]["action"] == "checked"
    store.close()


def test_cycle_demo_seed_writes_articles(tmp_path, monkeypatch):
    monkeypatch.setenv("TNB_DEMO_SEED", "1")
    monkeypatch.setenv("TNB_FAST", "1")
    monkeypatch.setenv("TNB_MAX_SOURCES", "0")
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    monkeypatch.setattr("pipeline.run.MAX_SOURCES", 0)
    summary = run_cycle(max_sources=0, demo_seed=True)
    assert summary["articles_new"] >= 1
    assert summary["claims"] >= 1
    store = Store(db)
    assert store.count_articles() >= 1
    arts = store.list_articles()
    assert all("FAKE" not in (a.get("verdict") or "") for a in arts)
    blob = " ".join(str(a.get("url") or "") for a in arts).lower()
    assert "example.invalid" not in blob
    assert "example.com" not in blob
    store.close()
