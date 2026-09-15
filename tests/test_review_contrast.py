import os

os.environ["TNB_FAST"] = "1"

from database.event_facts import compare_facts, extract_facts
from database.review_contrast import build_review_contrast, clean_claim_text, pick_review_claim
from nli import stance_from_text


WOAH_GENERIC = (
    "The New World screwworm (NWS), Cochliomyia hominivorax (Coquerel), is an "
    "obligate parasite of mammals, including humans, during their larval stages. "
    "Larvae feeding on the skin and underlying tissues of the host cause a condition "
    "known as wound or traumatic myiasis, which can be fatal."
)


def test_generic_woah_card_does_not_support_texas_horse():
    claim = "Flesh-eating screwworm hits Texas horse in first U.S. equine case this century"
    url = "https://www.woah.org/en/disease/new-world-screwworm/"
    assert stance_from_text(claim, WOAH_GENERIC, url) == "Unknown"


def test_facts_from_mexico_wildlife_headline():
    facts = extract_facts(
        "Leones, monos y pavo reales, entre la fauna silvestre afectada por Gusano Barrenador en México"
    )
    assert "gusano barrenador" in facts["diseases"]
    assert "México" in facts["places"]
    assert "fauna silvestre" in facts["animals"]
    assert "EE.UU." not in facts["places"]


def test_facts_from_texas_horse_headline():
    facts = extract_facts("Flesh-eating screwworm hits Texas horse in first U.S. equine case this century")
    assert "gusano barrenador" in facts["diseases"]
    assert "Texas" in facts["places"]
    assert "caballo" in facts["animals"]
    assert facts["novelty"] is True


def test_pick_paragraph_skips_pet_travel_chrome():
    from database.event_facts import pick_paragraph

    claim = "Flesh-eating screwworm found in Texas ranch horse"
    body = (
        "All submissions must be made by the veterinarian through VEHCS. "
        "Latest News 9/04/26 Texas Modifies New World Screwworm Infested Zone. "
        "On September 8, 2026, NWS was detected in a horse in Presidio County, Texas."
    )
    para, score = pick_paragraph(claim, body)
    assert "VEHCS" not in para
    assert "horse" in para.lower()
    assert score >= 3


def test_usda_calf_bulletin_is_partial_for_horse_claim():
    claim = "Flesh-eating screwworm hits Texas horse in first U.S. equine case this century"
    snippet = (
        "APHIS confirmed the detection of a New World screwworm in a bovine in Zavala County, Texas. "
        "The affected animal is a 3-week-old calf."
    )
    compared = compare_facts(claim, snippet)
    assert compared["status"] == "partial"
    assert "caballo" in compared["why"]


def test_tahc_horse_order_supports_the_claim():
    claim = "New World Screwworm Found In Texas Horse, First Case This Century"
    snippet = "On September 8, 2026, NWS was detected in a horse in Presidio County, Texas."
    compared = compare_facts(claim, snippet)
    assert compared["status"] == "hit"
    assert compared["stance"] == "Supported"


def test_review_strips_gdelt_dump_and_skips_bio():
    title = "Flesh - eating screwworm found in Texas ranch horse"
    claims = [
        {
            "text": (
                "In 2005, he joined the United Nations, serving as UN System Senior Coordinator "
                "for Avian and Pandemic Influenza (2005-2014)"
            ),
            "verifiable": 1,
        },
        {
            "text": title + " 20260912T021500Z avian influenza H5N1 HPAI screwworm SENASICA WOAH klif.com",
            "verifiable": 1,
        },
    ]
    picked = pick_review_claim(claims, title)
    assert "United Nations" not in picked
    assert "20260912" not in picked
    assert "Texas" in picked or "screwworm" in picked.lower()


def test_clean_claim_drops_gdelt_tail():
    raw = "Leones, monos y pavo reales 20260911T190000Z avian influenza H5N1 HPAI screwworm SENASICA"
    assert "20260911" not in clean_claim_text(raw)
    assert "Leones" in clean_claim_text(raw)


def test_contrast_rejects_encyclopedia_keeps_specific():
    claim = "SENASICA confirma gusano barrenador en un caballo de Texas, primer caso equino en EE.UU. este siglo"
    generic = {
        "snippet": WOAH_GENERIC,
        "url": "https://www.woah.org/en/disease/new-world-screwworm/",
    }
    none = build_review_contrast(claim, [generic])
    assert none["status"] == "none"
    assert none["snippet"] is None

    specific = {
        "snippet": (
            "SENASICA confirma el primer caso de gusano barrenador en un caballo de Texas "
            "en Estados Unidos en este siglo, con notificación a WOAH."
        ),
        "url": "https://www.gob.mx/senasica/articulos/gusano-barrenador-texas-caballo",
        "title": "SENASICA",
    }
    hit = build_review_contrast(claim, [generic, specific])
    assert hit["status"] == "hit"
    assert hit["stance"] == "Supported"
    assert "caballo" in hit["snippet"].lower()
    assert hit["url"].endswith("caballo")


def test_contrast_uses_peer_notes_when_no_bulletin():
    claim = "Flesh-eating screwworm found in Texas ranch horse"
    out = build_review_contrast(
        claim,
        [],
        item={"content_id": "me", "title": claim},
        corpus=[
            {
                "content_id": "other",
                "source_id": "SRC109",
                "title": "New World Screwworm Found In Texas Horse, First Case This Century",
                "text": "Ranch horse in Texas.",
                "url": "https://news.example/horse",
            }
        ],
        sources={"SRC109": {"type": "aggregator", "category": "news", "domain": "gdeltproject.org"}},
    )
    assert out["status"] == "peer"
    assert out["peers"]
    assert "prensa" in (out["why"] or "").lower()


def test_contrast_partial_from_stored_usda_calf():
    claim = "Flesh-eating screwworm hits Texas horse in first U.S. equine case this century"
    out = build_review_contrast(
        claim,
        [
            {
                "snippet": (
                    "APHIS confirmed the detection of a New World screwworm in a bovine in "
                    "Zavala County, Texas. The affected animal is a 3-week-old calf."
                ),
                "url": "https://www.aphis.usda.gov/news/agency-announcements/usda-confirms",
                "title": "USDA confirma NWS",
            }
        ],
    )
    assert out["status"] == "partial"
    assert out["snippet"]
    assert "caballo" in (out["why"] or "").lower()
