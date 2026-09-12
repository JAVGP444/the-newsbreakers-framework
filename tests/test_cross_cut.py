"""Smoke: filtro de Sala, traductor gtx-off, pesos CNN en disco."""
from pathlib import Path

from bootstrap import CNN_WEIGHTS, FRAMEWORK_ROOT


def test_offtopic_title_stays_out_of_sala():
    from relevance import should_skip

    press = {"type": "GENERAL_MEDIA", "category": "media", "domain": "aljazeera.com"}
    assert should_skip(
        "Saudi Arabia livestock",
        source=press,
        title="Iran war live: Houthis control Red Sea coast",
    )
    assert not should_skip("brote de gripe aviar H5N1 en aves de corral")


def test_cnn_weights_ship_with_repo():
    assert CNN_WEIGHTS.is_file(), CNN_WEIGHTS
    assert FRAMEWORK_ROOT.joinpath("frontend", "package.json").is_file()


def test_spanish_hint_skips_gtx(monkeypatch, tmp_path):
    from api.translate import translate_texts
    from database.store import Store

    monkeypatch.setattr("database.store.DB_PATH", tmp_path / "tnb.db")
    monkeypatch.setattr(
        "api.translate._gtx_many",
        lambda _texts: (_ for _ in ()).throw(AssertionError("gtx no debe llamarse")),
    )
    store = Store(tmp_path / "tnb.db")
    src = "Leones y monos entre la fauna silvestre afectada por gusano barrenador en México"
    assert translate_texts([src], store=store)[0] == src
    store.close()
