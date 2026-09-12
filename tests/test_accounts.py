from config.accounts import MAX_DEVICES, login, register, revoke_device
from config.license import issue


def test_register_login_and_device_cap(monkeypatch, tmp_path):
    monkeypatch.setenv("TNB_SEATS_PATH", str(tmp_path / "seats.sqlite"))
    monkeypatch.setenv("TNB_HOME", str(tmp_path))
    monkeypatch.setattr("config.license.ROOT", tmp_path)
    monkeypatch.delenv("TNB_LICENSE_KEY", raising=False)
    key = issue("cliente@clinica.mx", days=30)
    first = register(
        "ana@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-1",
        device_name="Mac",
    )
    assert first["ok"] is True
    assert first["session"]
    assert first["device_n"] == 1

    second = register(
        "ana@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-2",
        device_name="PC",
    )
    assert second["ok"] is False
    assert second["reason"] == "existe"

    other = register(
        "beto@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-2",
        device_name="PC",
    )
    assert other["ok"] is True
    third = register(
        "caro@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-3",
        device_name="Laptop",
    )
    assert third["ok"] is True
    fourth = register(
        "diego@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-4",
        device_name="Tablet",
    )
    assert fourth["ok"] is False
    assert fourth["reason"] == "cupo"
    assert MAX_DEVICES == 3

    out = login("ana@clinica.mx", "secreto12", device_id="dev-1", device_name="Mac")
    assert out["ok"] is True
    bad = login("ana@clinica.mx", "nope-nope", device_id="dev-1", device_name="Mac")
    assert bad["ok"] is False

    revoked = revoke_device("ana@clinica.mx", "dev-1")
    assert revoked["ok"] is True
    again = register(
        "eva@clinica.mx",
        "secreto12",
        license_key=key,
        device_id="dev-5",
        device_name="Nuevo",
    )
    assert again["ok"] is True
