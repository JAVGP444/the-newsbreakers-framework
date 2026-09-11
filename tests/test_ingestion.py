from datetime import datetime, timedelta, timezone

from access import delay_seconds, resolve_access
from dedup import DedupIndex, text_sha256, url_sha256
from normalize import UniversalContent, to_universal
from rss_fetcher import parse_rss
from nli import verify_claim
from risk_engine import WEIGHTS, risk_score
from source_catalog import (
    is_due,
    load_catalog,
    select_access_method,
    sources_due,
)


def test_catalog_loads():
    sources = load_catalog()
    assert len(sources) >= 20
    ids = [s["source_id"] for s in sources]
    assert len(ids) == len(set(ids))
    assert all("parser_version" in s and "access_method" in s for s in sources)
    assert any(s.get("rss_url") for s in sources)
    assert any(s.get("access_method") == "api" for s in sources)
    domains = {s["domain"] for s in sources}
    assert "who.int" in domains
    assert "woah.org" in domains
    assert "api.gdeltproject.org" in domains
    # Semilla del observatorio vigente (SENASICA / registro YAML)
    assert any("senasica" in (s.get("name") or "").lower() or "gob.mx" in (s.get("domain") or "") for s in sources)


def test_access_hierarchy():
    assert resolve_access({"access_method": "rss", "rss_url": "https://x"}) == "rss"
    assert resolve_access({"access_method": "api", "type": "aggregator"}) == "api"
    # Si hay RSS, no se baja a scrape aunque el YAML diga scrape
    assert select_access_method({"access_method": "scrape", "rss_url": "https://x"}) == "rss"
    assert select_access_method({"access_method": "scrape"}) == "scrape"
    assert delay_seconds({"priority": "critical"}) < delay_seconds({"priority": "low"})


def test_url_and_text_hash_stable():
    assert url_sha256("https://woah.org/a") == url_sha256("https://woah.org/a")
    assert url_sha256("https://woah.org/a") != url_sha256("https://woah.org/b")
    assert text_sha256("Hola   MUNDO") == text_sha256("hola mundo")
    assert text_sha256("hola mundo") != text_sha256("hola mundo!")


def test_dedup_index_url_then_text():
    idx = DedupIndex()
    dup, reason = idx.register("https://who.int/a", "brote H5N1")
    assert dup is False
    dup, reason = idx.register("https://who.int/a", "otro texto")
    assert dup is True and reason in {"url", "url_sha256"}
    dup, reason = idx.register("https://who.int/b", "brote H5N1")
    assert dup is True and reason == "text_sha256"


def test_normalize_universal_content():
    item = to_universal(
        source_id="SRC001",
        url="https://www.who.int/news/item/1",
        title="Avian influenza update",
        text="<p>Outbreak in poultry</p>",
        language="en",
    )
    assert isinstance(item, UniversalContent)
    assert item.content_id.startswith("CNT-")
    assert item.url_sha256 == url_sha256(item.url)
    assert "poultry" in item.text.lower()
    assert "<p>" not in item.text
    payload = item.to_dict()
    assert payload["source_id"] == "SRC001"
    assert payload["model_versions"]["normalizer"] == "universal_v1"


def test_parse_rss_items():
    xml = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item>
        <title>H5N1 poultry outbreak</title>
        <link>https://www.who.int/news/item/demo</link>
        <enclosure url="https://www.who.int/images/demo.jpg" type="image/jpeg" />
      </item>
    </channel></rss>"""
    items = parse_rss(xml, "SRC001")
    assert len(items) == 1
    assert items[0].source_id == "SRC001"
    assert items[0].url.endswith("/demo")
    assert items[0].content_id.startswith("CNT-")
    assert any("demo.jpg" in u for u in items[0].images)


def test_claim_extractor_bridge():
    from claims import extract_claims

    result = extract_claims("La OMS confirma un brote de gripe aviar H5N1 en aves de corral en México.")
    assert result["main_claim"]
    assert result["model_version"]
    assert isinstance(result["claims"], list)
    claim = result["claims"][0]
    assert claim.get("subject")
    assert claim.get("predicate")
    assert "verifiable" in claim
    assert "object" in claim


def test_relevance_skip_threshold():
    from relevance import RELEVANCE_THRESHOLD, relevance_score, should_skip

    assert RELEVANCE_THRESHOLD == 0.15
    assert should_skip("receta de pasta carbonara con albahaca y tomate")
    assert relevance_score("receta de pasta") < 0.15
    assert not should_skip("brote de gripe aviar H5N1 en aves de corral")
    official = {
        "type": "OFFICIAL",
        "category": "official",
        "diseases": ["gripe_aviar"],
        "domain": "woah.org",
    }
    assert not should_skip("WOAH weekly animal health update for poultry farms", source=official)
    long_pasta = "receta de pasta carbonara con albahaca y tomate " * 6
    assert should_skip(long_pasta, source=official)


def test_bundled_diseases_and_watchlist_without_generador():
    from bootstrap import DISEASES_YAML, FRAMEWORK_ROOT, WATCHLIST_YAML
    from relevance import TOPIC_KEYWORDS
    from source_catalog import load_catalog

    assert (FRAMEWORK_ROOT / "config" / "diseases.yaml").is_file()
    assert WATCHLIST_YAML.is_file()
    assert DISEASES_YAML.is_file()
    lowered = [k.lower() for k in TOPIC_KEYWORDS]
    assert "screwworm" in lowered
    ids = {s["source_id"] for s in load_catalog()}
    assert "SRC-PIGSITE" in ids
    assert "SRC109" in ids


def test_sources_due_force_ignores_next_check():
    from datetime import datetime, timedelta, timezone

    from source_catalog import sources_due

    now = datetime.now(timezone.utc)
    source = {
        "source_id": "SRC-FORCE",
        "priority": "critical",
        "active": True,
        "rss_url": "https://example.org/rss",
        "access_method": "rss",
        "next_check": (now + timedelta(hours=2)).isoformat(),
    }
    assert sources_due([source], now=now, methods=("rss",), force=False) == []
    forced = sources_due([source], now=now, methods=("rss",), force=True)
    assert len(forced) == 1


def test_gdelt_windows_shift_with_offset():
    from datetime import datetime, timezone

    from api_fetcher import gdelt_query_windows

    now = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    first = gdelt_query_windows(now=now, offset_days=0, lookback_days=21, windows=2, window_hours=24)
    later = gdelt_query_windows(now=now, offset_days=4, lookback_days=21, windows=2, window_hours=24)
    assert len(first) == 2
    assert first[0][1] > later[0][1]


def test_parse_rss_keeps_more_than_first_ten():
    items_xml = "".join(
        f"<item><title>H5N1 item {i}</title><link>https://www.woah.org/n/{i}</link></item>"
        for i in range(15)
    )
    xml = f'<?xml version="1.0"?><rss version="2.0"><channel>{items_xml}</channel></rss>'
    items = parse_rss(xml, "SRC002", limit=15)
    assert len(items) == 15


def test_atom_next_link_detected():
    from rss_fetcher import _next_feed_url

    xml = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <link rel="next" href="https://example.org/rss?page=2"/>
    </feed>"""
    assert _next_feed_url(xml).endswith("page=2")


def test_image_average_hash_stable(tmp_path):
    from image_hash import average_hash, hamming, perceptual_hash
    from process import write_placeholder_png

    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    write_placeholder_png(a, (10, 80, 10))
    write_placeholder_png(b, (10, 80, 10))
    ha = perceptual_hash(str(a))
    hb = perceptual_hash(str(b))
    assert ha["implemented"] is True
    assert ha["sha256"] == hb["sha256"]
    assert ha["phash"]
    assert hamming(ha["phash"], hb["phash"]) == 0
    assert average_hash(str(a)) == ha["phash"]


def test_cnn_heuristic_classes(tmp_path):
    from cnn import IMAGE_CLASSES, classify_image
    from process import write_placeholder_png

    path = tmp_path / "senasica_official.png"
    write_placeholder_png(path)
    result = classify_image(str(path), url="https://www.gob.mx/senasica/foto.png")
    assert result["implemented"] is True
    assert result["class"] in IMAGE_CLASSES
    assert "FAKE" not in (result["class"] or "")
    assert result["confidence"] > 0


def test_access_scrape_deferred_note():
    from access import SCRAPE_DEFERRED, scrape_deferred_note

    note = scrape_deferred_note({"source_id": "SRC001", "name": "SENASICA"})
    assert SCRAPE_DEFERRED in note
    assert "SRC001" in note


def test_ui_paths_point_to_generator():
    from observatory import ui_paths

    info = ui_paths()
    assert "urls_enfermedades_dashboard.html" in info["canonical_dashboard"]
    assert "observatorio_visual.html" in info["map_observatory"]
    assert "Generador_Excel_Enfermedades" in info["project_root"]


def test_scheduler_due_without_last_checked():
    source = {"source_id": "SRC001", "priority": "critical", "active": True, "rss_url": "https://x", "access_method": "rss"}
    assert is_due(source) is True
    source["last_checked"] = datetime.now(timezone.utc).isoformat()
    assert is_due(source) is False
    source["last_checked"] = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    assert is_due(source) is True
    due = sources_due([source], methods=("rss",))
    assert len(due) == 1


def test_nli_unknown_without_evidence():
    result = verify_claim("hay un brote", [])
    assert result["label"] == "Unknown"
    assert result["model_version"]


def test_nli_supported_from_evidence_stance():
    result = verify_claim("hay un brote", [{"stance": "Supported"}, {"stance": "Supported"}])
    assert result["label"] == "Supported"


def test_nli_three_tokens_not_supported():
    from nli import stance_from_text

    snippet = "WOAH outbreak H5N1 influenza avian poultry farm biosecurity notification"
    assert stance_from_text("hay un brote", snippet, url="https://www.woah.org/en/disease/avian-influenza/") == "Unknown"
    weak = verify_claim(
        "brote influenza aviar",
        [{"snippet": snippet, "url": "https://example.net/blog/post", "stance": ""}],
    )
    assert weak["label"] == "Unknown"


def test_nli_supported_needs_official_and_strong_overlap():
    from nli import stance_from_text

    claim = (
        "WOAH confirma un brote de influenza aviar H5N1 altamente patógena "
        "en aves de corral con notificación WAHIS y bioseguridad en granjas"
    )
    snippet = (
        "La ficha WOAH de influenza aviar describe H5N1 altamente patógena en aves "
        "de corral, notificación WAHIS y bioseguridad en granjas avícolas."
    )
    official = "https://www.woah.org/en/disease/avian-influenza/"
    assert stance_from_text(claim, snippet, url=official) == "Supported"
    assert stance_from_text(claim, snippet, url="https://random-blog.example/post") == "Unknown"


def test_risk_engine_verdicts_and_weights():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6
    low = risk_score({"nli_label": "Supported", "source_reliability": 5})
    assert low["verdict"] in {"RESPALDADO", "INSUFICIENTE"}
    high = risk_score({"evidence_contradiction": 100, "nli_label": "Contradicted"})
    assert high["verdict"] == "CONTRADICHO"
    human = risk_score({"low_confidence": True})
    assert human["verdict"] == "REVISIÓN HUMANA"
    assert "FAKE" not in high["verdict"] and "REAL" not in high["verdict"]
