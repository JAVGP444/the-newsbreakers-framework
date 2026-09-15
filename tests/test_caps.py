from config.caps import allows, apply_cap, public_status


def test_pipeline_caps_are_open():
    assert allows("mine") is True
    assert allows("llm") is True
    assert allows("ocr") is True
    assert apply_cap("mine", 250, 8) == 250
    assert public_status()["ok"] is True
    assert public_status()["tier"] == "open"
