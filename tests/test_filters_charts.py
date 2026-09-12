import hashlib

from database.query_filters import parse_article_datetime, parse_article_query
from database.store import Store


def _art(store: Store, **kw):
    cid = kw.get("content_id") or "CNT-" + hashlib.sha256(kw["url"].encode()).hexdigest()[:10]
    store.insert_article(
        {
            "content_id": cid,
            "source_id": kw.get("source_id", "SRC001"),
            "url": kw["url"],
            "url_sha256": hashlib.sha256(kw["url"].encode()).hexdigest(),
            "title": kw.get("title", "Brote de gripe aviar H5N1"),
            "text": kw.get("text", "cuerpo " * 80),
            "collected_at": kw.get("collected_at", "2026-09-03T10:00:00"),
            "published_at": kw.get("published_at", "2026-09-03T09:00:00"),
            "country": kw.get("country", "MX"),
            "verdict": kw.get("verdict", "CONTRADICHO"),
            "risk_score": kw.get("risk_score", 70),
            "raw_format": kw.get("raw_format", "rss"),
            "disease_tags": kw.get("disease_tags", ["gripe_aviar"]),
        }
    )
    return cid


def test_filtered_articles_dates_country_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    store.upsert_source({"source_id": "SRC001", "name": "SENASICA", "domain": "gob.mx", "access_method": "rss"})
    _art(store, url="https://www.gob.mx/a", title="Gripe aviar en México", collected_at="2026-09-03T10:00:00")
    _art(
        store,
        url="https://www.gob.mx/b",
        title="Gusano barrenador",
        collected_at="2026-08-01T10:00:00",
        published_at="2026-08-01T09:00:00",
        disease_tags=["gusano_barrenador"],
        country="US",
        verdict="RESPALDADO",
        risk_score=20,
    )
    q = parse_article_query(date_from="2026-09-01", date_to="2026-09-10", country="MX", verdict="contradicho")
    rows = store.query_articles(q, limit=None)
    assert len(rows) == 1
    assert "aviar" in (rows[0].get("title") or "").lower()
    page = store.paged_articles(parse_article_query(page=1, page_size=1))
    assert page["count"] == 2
    assert page["page_size"] == 1
    store.close()


def test_chart_empty_and_risk_null(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    empty = store.chart_payload()
    assert empty["empty"] is True
    assert empty["db_empty"] is True
    _art(store, url="https://www.woah.org/a", risk_score=None, title="Gripe aviar H5N1")
    _art(store, url="https://www.woah.org/b", risk_score=72, title="Gripe aviar segundo")
    payload = store.chart_payload()
    assert payload["empty"] is False
    hist = {r["bucket"]: r["count"] for r in payload["risk_histogram"]}
    assert hist["sin_puntuacion"] == 1
    assert hist["0-20"] == 0
    assert hist["61-80"] == 1
    assert sum(d["count"] for d in payload["by_day"]) == payload["n"] == 2
    store.close()


def test_chart_payload_parses_rfc822_dates(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    _art(
        store,
        url="https://www.woah.org/rfc",
        published_at="Wed, 30 Jul 2026 12:00:00 GMT",
        collected_at="2026-07-30T12:00:00",
        title="Gripe aviar RFC",
    )
    payload = store.chart_payload()
    assert payload["empty"] is False
    days = [d["day"] for d in payload["by_day"]]
    assert "2026-07-30" in days
    assert not any(d.startswith("Wed") for d in days)
    store.close()


def test_sources_deferred_and_diseases_from_data(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    store.upsert_source(
        {"source_id": "SRC002", "name": "Portal scrape", "domain": "ejemplo.gob", "access_method": "scrape"}
    )
    store.upsert_source(
        {"source_id": "SRC001", "name": "SENASICA RSS", "domain": "gob.mx", "access_method": "rss", "last_checked": "2026-09-01"}
    )
    _art(store, url="https://www.gob.mx/c", source_id="SRC001", title="Gripe aviar en granja de aves")
    srcs = store.list_sources()
    by_id = {s["source_id"]: s for s in srcs}
    assert by_id["SRC002"]["status"] == "deferred"
    assert by_id["SRC001"]["article_count"] == 1
    cards = store.disease_counts()
    assert any(c["id"] == "gripe_aviar" and c["menciones"] >= 1 for c in cards)
    store.close()


def test_chart_origin_and_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    _art(
        store,
        url="https://www.gob.mx/senasica/aviar",
        title="Gripe aviar SENASICA",
        verdict="RESPALDADO",
        disease_tags=["gripe_aviar"],
    )
    _art(
        store,
        url="https://www.youtube.com/watch?v=abcdefghijk",
        title="Video de gripe aviar",
        raw_format="youtube",
        verdict="CONTRADICHO",
        disease_tags=["gripe_aviar"],
    )
    _art(
        store,
        url="https://pubmed.ncbi.nlm.nih.gov/123",
        title="Paper H5N1",
        raw_format="api",
        verdict="INSUFICIENTE",
        disease_tags=["gripe_aviar"],
    )
    payload = store.chart_payload()
    origin = {r["id"]: r["count"] for r in payload["volume_by_origin"]}
    assert origin["oficial"] == 1
    assert origin["youtube"] == 1
    assert origin["cientifico"] == 1
    verd = {r["id"]: r["count"] for r in payload["volume_by_verdict"]}
    assert verd["respaldado"] == 1
    assert verd["contradicho"] == 1
    assert verd["insuficiente"] == 1
    oficiales = store.query_articles(parse_article_query(origin="oficial"), limit=None)
    assert len(oficiales) == 1
    assert "gob.mx" in (oficiales[0].get("url") or "")
    store.close()


def test_articles_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    _art(
        store,
        url="https://www.gob.mx/old",
        title="Viejo brote de gripe aviar",
        collected_at="2026-08-01T10:00:00",
        published_at="2026-08-01T09:00:00",
    )
    _art(
        store,
        url="https://www.gob.mx/new",
        title="Nuevo brote de gripe aviar",
        collected_at="2026-09-12T08:00:00",
        published_at="2026-09-11T22:00:00",
    )
    rows = store.query_articles(parse_article_query(order="newest"), limit=None)
    titles = [r["title"] for r in rows]
    assert titles[0] == "Nuevo brote de gripe aviar"
    assert titles[-1] == "Viejo brote de gripe aviar"
    store.close()


def test_order_uses_published_not_collected(tmp_path, monkeypatch):
    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    store = Store(tmp_path / "tnb.db")
    _art(
        store,
        url="https://www.gob.mx/agosto",
        title="Agosto minado hoy gripe aviar",
        collected_at="2026-09-12T23:50:00",
        published_at="2026-08-01T09:00:00",
    )
    _art(
        store,
        url="https://www.gob.mx/septiembre",
        title="Septiembre publicado gripe aviar",
        collected_at="2026-09-10T08:00:00",
        published_at="Wed, 10 Sep 2026 12:00:00 GMT",
    )
    rows = store.query_articles(parse_article_query(order="published_at"), limit=None)
    titles = [r["title"] for r in rows]
    assert titles[0] == "Septiembre publicado gripe aviar"
    assert titles[1] == "Agosto minado hoy gripe aviar"
    store.close()


def test_parse_gdelt_seendate():
    dt = parse_article_datetime("20260912T0")
    assert dt is not None
    assert dt.date().isoformat() == "2026-09-12"
    assert parse_article_datetime("20260912T143000").day == 12
