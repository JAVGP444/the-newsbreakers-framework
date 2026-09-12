from database.geo import country_info, resolve_article_country


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
