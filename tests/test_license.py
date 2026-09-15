from config.license import allows, apply_cap, is_licensed, public_status


def test_observatory_is_open():
    assert is_licensed() is True
    assert allows("mine") is True
    assert allows("llm") is True
    assert allows("ocr") is True
    assert apply_cap("mine", 250, 8) == 250
    assert public_status()["ok"] is True
    assert public_status()["tier"] == "open"
