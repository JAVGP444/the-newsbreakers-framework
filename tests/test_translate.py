from api.translate import translate_texts
from database.store import Store


def test_ollama_down_uses_mymemory_then_original(tmp_path, monkeypatch):
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)

    monkeypatch.setattr("api.translate.probe_ollama", lambda: {"available": False, "reason": "down"})
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
