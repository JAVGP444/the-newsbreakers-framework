from config.license import allows, is_licensed, issue, normalize_key, parse, save_key, sign_payload


def test_community_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TNB_LICENSE_KEY", raising=False)
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    info = parse("")
    assert info["ok"] is False
    assert info["tier"] == "community"
    assert allows("llm") is False
    assert allows("mine") is False


def test_apply_cap_community(monkeypatch, tmp_path):
    from config.license import apply_cap

    monkeypatch.delenv("TNB_LICENSE_KEY", raising=False)
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    assert apply_cap("mine", 250, 8) == 8
    assert apply_cap("mine", 0, 8) == 0


def test_valid_key_unlocks_llm(monkeypatch, tmp_path):
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    key = issue("ana@clinica.mx", days=30, features=["llm"])
    monkeypatch.setenv("TNB_LICENSE_KEY", key)
    info = parse()
    assert info["ok"] is True
    assert allows("llm") is True
    assert allows("ocr") is True
    assert allows("mine") is True
    assert is_licensed() is True


def test_bad_signature_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    key = sign_payload({"who": "x", "exp": "2099-01-01", "f": ["llm"]})
    monkeypatch.setenv("TNB_LICENSE_KEY", key[:-1] + ("0" if key[-1] != "0" else "1"))
    assert parse()["ok"] is False


def test_normalize_key_pulls_tnb1_out_of_noise():
    key = issue("lab", days=10, features=["mine"])
    assert normalize_key(f"1. `{key}`") == key
    assert normalize_key(f"\n{key}\n") == key


def test_save_key_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    monkeypatch.delenv("TNB_LICENSE_KEY", raising=False)
    key = issue("lab", days=10, features=["ocr"])
    out = save_key(key)
    assert out["ok"] is True
    assert (tmp_path / "data" / "license.key").read_text(encoding="utf-8").strip() == key
