from api.translate import translate_texts
from database.store import Store


def test_ollama_down_uses_mymemory_then_original(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)

    monkeypatch.setattr("api.translate.probe_ollama", lambda: {"available": False, "reason": "down"})
    monkeypatch.setattr("api.translate._google_gtx_one", lambda _text: None)
    monkeypatch.setattr(
        "api.translate._mymemory_one",
        lambda text: "Brote de gripe aviar" if text == "Avian flu outbreak" else None,
    )

    out = translate_texts(["Avian flu outbreak", "A" * 600], store=store)
    assert out[0] == "Brote de gripe aviar"
    assert out[1] == "A" * 600
    assert store.get_translation("Avian flu outbreak") == "Brote de gripe aviar"

    monkeypatch.setattr("api.translate._mymemory_one", lambda _text: (_ for _ in ()).throw(AssertionError("cache")))
    again = translate_texts(["Avian flu outbreak"], store=store)
    assert again == ["Brote de gripe aviar"]
    store.close()


def test_skips_spanish_without_calling_gtx(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)
    monkeypatch.setattr("api.translate._google_gtx_one", lambda _text: (_ for _ in ()).throw(AssertionError("gtx")))
    monkeypatch.setattr("api.translate._gtx_many", lambda texts: [None] * len(texts))
    src = "Leones, monos y pavos reales entre la fauna silvestre afectada por gusano barrenador"
    assert translate_texts([src], store=store) == [src]
    store.close()


def test_gtx_fallback_when_ollama_and_memory_fail(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)
    monkeypatch.setattr("api.translate.probe_ollama", lambda: {"available": False, "reason": "down"})
    monkeypatch.setattr("api.translate._ollama_one", lambda *_a, **_k: None)
    monkeypatch.setattr("api.translate._mymemory_one", lambda _text: None)
    monkeypatch.setattr("api.translate._google_gtx_one", lambda text: "Brote de gripe aviar" if "Avian" in text else None)
    out = translate_texts(["Avian flu outbreak"], store=store)
    assert out == ["Brote de gripe aviar"]
    store.close()
