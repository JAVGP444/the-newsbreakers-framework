from signals import analyze_text, classify_narrative


def test_word_is_not_a_verdict():
    pack = analyze_text("El texto menciona un posible ocultamiento.")
    assert pack["signals"]
    assert all(s["not_a_verdict"] for s in pack["signals"])
    cls = classify_narrative(pack, [])
    assert cls["code"] != "maliciosa"
    assert cls["not_malicious_verdict"] is True


def test_question_is_not_an_accusation():
    pack = analyze_text("¿Las autoridades ocultaron el brote?")
    assert pack["signals"]
    assert pack["signals"][0]["modality"] == "pregunta"
    assert "pregunta" in pack["signals"][0]["note"].lower()


def test_negation_is_not_an_accusation():
    pack = analyze_text("No existe evidencia de que las autoridades ocultaran el brote.")
    assert pack["signals"][0]["modality"] == "negacion"


def test_attribution_is_marked():
    pack = analyze_text("La oposición acusa a las autoridades de ocultar el brote de gripe aviar.")
    assert pack["signals"][0]["modality"] == "cita"


def test_compound_claim_splits():
    pack = analyze_text(
        "Las autoridades ocultaron durante tres semanas un brote de gripe aviar para evitar generar alarma."
    )
    texts = [c["text"].lower() for c in pack["claims"]]
    assert len(texts) >= 2
    assert any("ocult" in t for t in texts)


def test_structure_is_not_malice():
    pack = analyze_text("Las autoridades ocultaron deliberadamente el brote y no reportaron los casos.")
    assert pack["structures"]
    assert all("no es malicia" in (s["note"].lower()) for s in pack["structures"])
