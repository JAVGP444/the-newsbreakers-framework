from database.geo import country_info, resolve_article_country, resolve_article_place


def test_unknown_country_is_unlocated():
    info = country_info("Texas")
    assert info["unlocated"] is True
    assert info["lat"] is None
    assert info["lng"] is None


def test_usa_and_mexico_names_resolve():
    assert resolve_article_country({"country": "USA", "title": "screwworm"}) == "US"
    assert resolve_article_country({"country": "Mexico", "title": "gusano"}) == "MX"
    assert resolve_article_country({"country": "XX", "title": "Flesh-eating screwworm in the United States"}) == "US"
    assert resolve_article_country({"country": "", "title": "nota sin lugar"}) == "XX"


def test_iso_codes_keep_centroids():
    mx = country_info("MX")
    assert mx.get("unlocated") is not True
    assert mx["lat"] == 23.63
    assert mx["lng"] == -102.55


def test_texas_beats_usa_centroid():
    place = resolve_article_place(
        {"country": "US", "title": "First New World screwworm in a Texas horse"}
    )
    assert place["place_id"] == "US-TX"
    assert place["grain"] == "place"
    assert place["lat"] == 31.0
    assert place["query"] == "Texas"


def test_presidio_beats_texas():
    place = resolve_article_place({"title": "Screwworm confirmed in Presidio County, Texas"})
    assert place["place_id"] == "US-TX-PRESIDIO"
    assert "Presidio" in place["name"]


def test_chiapas_beats_mexico_centroid():
    place = resolve_article_place({"country": "MX", "title": "Gusano barrenador en fauna de Chiapas"})
    assert place["place_id"] == "MX-CHIS"


def test_gusano_does_not_become_usa():
    place = resolve_article_place({"title": "Gusano barrenador en fauna silvestre de México"})
    assert place["country"] == "MX"
    assert place["place_id"] != "US"


def test_new_mexico_is_not_mexico():
    place = resolve_article_place({"title": "Avian influenza in New Mexico dairies"})
    assert place["place_id"] == "US-NM"
    assert resolve_article_country({"title": "Avian influenza in New Mexico dairies"}) == "US"
