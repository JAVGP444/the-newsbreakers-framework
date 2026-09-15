from lexicon import BANK, apply_term_rows, narrative_specs, term_weight
from signals import analyze_text, classify_narrative
from surveillance import characterize


def test_yaml_bank_has_weights_not_malice():
    assert "ocultamiento" in BANK
    assert term_weight("ocultamiento") >= 1
    assert any("ocultaron" in BANK["ocultamiento"] or t == "ocultaron" for t in BANK["ocultamiento"])


def test_narrative_specs_exist():
    specs = narrative_specs()
    ids = {s["id"] for s in specs}
    assert "NAR-ocultamiento" in ids
    assert all(s.get("label") for s in specs)


def test_editable_bank_overlay():
    try:
        apply_term_rows(
            [
                {"term": "ocultar", "category": "ocultamiento", "label": "Ocultamiento", "weight": 5, "active": 1},
                {"term": "brote", "category": "salud_animal", "label": "Eventos", "weight": 2, "active": 1},
            ]
        )
        assert BANK["ocultamiento"] == ("ocultar",)
        assert term_weight("ocultamiento") == 5
    finally:
        apply_term_rows([])


def test_characterize_does_not_stamp_malice():
    articles = [
        {
            "content_id": "CNT-1",
            "title": "Las autoridades ocultaron el brote de influenza aviar",
            "text": "Las autoridades ocultaron el brote. SENASICA reportó casos.",
            "published_at": "2026-09-01",
            "country": "MX",
            "source_id": "SRC001",
            "source_name": "SENASICA",
        },
        {
            "content_id": "CNT-2",
            "title": "Se detectaron casos de influenza aviar",
            "text": "Se detectaron casos. Las autoridades investigan.",
            "published_at": "2026-09-03",
            "country": "US",
            "source_id": "SRC002",
            "source_name": "WOAH",
        },
    ]
    claims = [
        {
            "claim_id": "CL-1",
            "content_id": "CNT-1",
            "text": "Las autoridades ocultaron el brote",
            "nli_label": "unknown",
        }
    ]
    evidence = [
        {
            "evidence_id": "EV-1",
            "claim_id": "CL-1",
            "url": "https://www.woah.org/report",
            "source_tier": "oficial",
            "snippet": "Official notification of outbreak",
            "stance": "supports",
        }
    ]
    pack = characterize(articles, claims=claims, evidence=evidence, sources=[{"source_id": "SRC001", "name": "SENASICA", "domain": "gob.mx", "type": "oficial", "active": 1}])
    assert pack["narratives"]
    for row in pack["narratives"]:
        cls = row.get("classification") or {}
        assert cls.get("code") != "maliciosa"
        assert "FAKE" not in str(cls.get("label") or "").upper()
        assert "REAL" not in str(cls.get("label") or "").upper()
    cls = classify_narrative(analyze_text(articles[0]["title"] + " " + articles[0]["text"]), claims)
    assert cls["not_malicious_verdict"] is True
