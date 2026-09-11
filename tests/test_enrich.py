from pathlib import Path

from database.enrich import enrich_article
from database.store import Store


def test_title_only_article_gets_entities_and_lectura(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    monkeypatch.setattr("database.thumbs.THUMBS_DIR", tmp_path / "thumbs")
    monkeypatch.setattr("live_pages.live_evidence_cards", lambda *a, **k: [])
    store = Store(db)
    store.insert_article(
        {
            "content_id": "CNT-81e391829346",
            "source_id": "SRC-SOCIAL",
            "url": "inapp:social/avian",
            "url_sha256": "abc123",
            "text_sha256": "def456",
            "title": "Avian influenza",
            "text": "Avian influenza",
            "country": "INT",
            "source_type": "LinkedIn",
            "raw_format": "social",
            "verdict": "RESPALDADO",
            "risk_score": 30,
            "disease_tags": ["gripe_aviar"],
        }
    )
    result = enrich_article(store, "CNT-81e391829346")
    assert result["ok"]
    row = store.get_article("CNT-81e391829346")
    assert row["text"] != "Avian influenza"
    assert "gripe aviar" in (row["text"] or "").lower() or "influenza" in (row["text"] or "").lower()
    grouped = store.grouped_entities("CNT-81e391829346")
    assert grouped["DISEASE"]
    assert any("gripe" in v.lower() or "influenza" in v.lower() or "aviar" in v.lower() for v in grouped["DISEASE"])
    assert grouped["ANIMAL"]
    assert grouped["COUNTRY"]
    text_l = (row["text"] or "").lower()
    if "woah" not in text_l and "fao" not in text_l:
        assert "WOAH" not in [str(v).upper() for v in grouped["ORG"]]
    claims = store.list_claims("CNT-81e391829346")
    assert claims
    evidence = store.list_evidence(claims[0]["claim_id"])
    assert 2 <= len(evidence) <= 4
    assert all((e.get("url") or "").startswith("http") for e in evidence)
    assert any("woah.org/en/disease" in (e.get("url") or "") for e in evidence)
    images = store.list_images("CNT-81e391829346")
    assert not any(
        "svg" in str(im.get("mime_type") or "").lower() or str(im.get("storage_key") or "").lower().endswith(".svg")
        for im in images
    )
    thumb = Path(str(row.get("thumb_path") or ""))
    assert thumb.is_file()
    assert thumb.suffix.lower() in {".jpg", ".jpeg"}
    assert thumb.read_bytes()[:3] == b"\xff\xd8\xff"
    expl = store.local_explanation(row, claims, evidence)
    assert expl
    assert "Lectura del caso" in expl
    store.close()


def test_paho_fmd_history_does_not_get_avian_evidence(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    monkeypatch.setattr("database.thumbs.THUMBS_DIR", tmp_path / "thumbs")
    monkeypatch.setattr("live_pages.live_evidence_cards", lambda *a, **k: [])
    store = Store(db)
    store.insert_article(
        {
            "content_id": "CNT-paho-aftosa",
            "source_id": "SRC-PAHO",
            "url": "https://www.paho.org/es/historias/de-fiebre-aftosa-una-sola-salud",
            "url_sha256": "paho1",
            "text_sha256": "paho2",
            "title": "De la fiebre aftosa a Una Sola Salud: 70 años de cooperación veterinaria",
            "text": (
                "La historia de la fiebre aftosa en las Américas y el enfoque Una Sola Salud. "
                "El artículo menciona influenza y otras zoonosis de forma secundaria."
            ),
            "country": "INT",
            "source_type": "oficial",
            "raw_format": "html",
            "verdict": "Unknown",
            "risk_score": 20,
        }
    )
    result = enrich_article(store, "CNT-paho-aftosa")
    assert result["ok"]
    claims = store.list_claims("CNT-paho-aftosa")
    evidence = []
    for claim in claims:
        evidence.extend(store.list_evidence(claim["claim_id"]))
    from database.enrich import cap_official_cards, filter_article_evidence

    article = store.get_article("CNT-paho-aftosa")
    filtered = filter_article_evidence(article, evidence, store)
    assert filtered == []
    assert not any("avian-influenza" in (e.get("url") or "") for e in evidence)
    assert not any("bird-flu" in (e.get("url") or "") for e in evidence)
    unrelated = filter_article_evidence(
        {"title": "Vacunas durante el embarazo protegen a madres y recién nacidos", "text": "Coberturas de inmunización. " * 20, "url": "https://www.paho.org/es/noticias/vacunas"},
        [
            {"url": "https://www.woah.org/en/disease/avian-influenza/", "snippet": "x" * 50},
            {"url": "https://www.cdc.gov/bird-flu/index.html", "snippet": "y" * 50},
        ],
        store,
    )
    assert unrelated == []
    dups = cap_official_cards(
        [
            {"url": "https://www.woah.org/en/disease/avian-influenza/", "snippet": "x" * 50},
            {"url": "https://www.woah.org/en/disease/avian-influenza/", "snippet": "y" * 50},
            {"url": "https://www.cdc.gov/bird-flu/index.html", "snippet": "z" * 50},
            {"url": "https://www.cdc.gov/bird-flu/other.html", "snippet": "w" * 50},
        ],
        ["gripe_aviar"],
    )
    hosts = [(e["url"].split("/")[2]) for e in dups]
    assert len(dups) == 2
    assert len(set(hosts)) == 2
    store.close()
