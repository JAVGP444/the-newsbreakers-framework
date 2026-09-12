"""Cuentas, sesión y tope de 3 equipos por licencia TNB1.

Usuarios y asientos viven en SQLite (TNB_SEATS_PATH o data/accounts.sqlite).
Si Mac y Windows apuntan al mismo archivo (OneDrive), el tope es global.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from config.paths import seats_db_path

MAX_DEVICES = 3
SESSION_DAYS = 30
_PBKDF_ROUNDS = 120_000


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    path = seats_db_path()
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          email TEXT PRIMARY KEY,
          password_hash TEXT NOT NULL,
          license_fp TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY,
          email TEXT NOT NULL,
          device_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expires_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS devices (
          license_fp TEXT NOT NULL,
          device_id TEXT NOT NULL,
          email TEXT NOT NULL,
          name TEXT,
          seen_at TEXT NOT NULL,
          PRIMARY KEY (license_fp, device_id)
        );
        """
    )
    conn.commit()
    return conn


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def hash_password(password: str, salt: str | None = None) -> str:
    salt_hex = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt_hex.encode("ascii"), _PBKDF_ROUNDS)
    return f"{salt_hex}:{digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    if ":" not in (stored or ""):
        return False
    salt, _digest = stored.split(":", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def license_fp(key: str) -> str:
    token = (key or "").strip()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _device_name(raw: str | None) -> str:
    name = (raw or "").strip()[:80]
    return name or "Equipo"


def register(
    email: str,
    password: str,
    *,
    license_key: str = "",
    device_id: str = "",
    device_name: str = "",
) -> dict[str, Any]:
    from config.license import normalize_key, parse, save_key

    mail = normalize_email(email)
    if "@" not in mail or "." not in mail.split("@")[-1]:
        return {"ok": False, "reason": "correo"}
    if len(password or "") < 8:
        return {"ok": False, "reason": "clave_corta"}
    did = (device_id or "").strip()
    if not did:
        return {"ok": False, "reason": "dispositivo"}

    token = normalize_key(license_key) if license_key else ""
    fp = ""
    if token:
        info = parse(token)
        if not info.get("ok"):
            return {"ok": False, "reason": info.get("reason") or "licencia"}
        fp = license_fp(token)

    conn = _connect()
    try:
        row = conn.execute("SELECT email FROM users WHERE email = ?", (mail,)).fetchone()
        if row:
            return {"ok": False, "reason": "existe"}
        if fp:
            seated = _claim_device(conn, fp, did, mail, device_name)
            if not seated.get("ok"):
                return seated
            save_key(token)
        conn.execute(
            "INSERT INTO users(email, password_hash, license_fp, created_at) VALUES (?,?,?,?)",
            (mail, hash_password(password), fp or None, _now()),
        )
        session = _new_session(conn, mail, did)
        conn.commit()
        return {"ok": True, "session": session, "email": mail, **public_user(mail)}
    finally:
        conn.close()


def login(
    email: str,
    password: str,
    *,
    device_id: str = "",
    device_name: str = "",
    license_key: str = "",
) -> dict[str, Any]:
    from config.license import normalize_key, parse, save_key

    mail = normalize_email(email)
    did = (device_id or "").strip()
    if not did:
        return {"ok": False, "reason": "dispositivo"}
    conn = _connect()
    try:
        row = conn.execute("SELECT email, password_hash, license_fp FROM users WHERE email = ?", (mail,)).fetchone()
        if not row or not check_password(password, row["password_hash"]):
            return {"ok": False, "reason": "credenciales"}
        fp = row["license_fp"] or ""
        token = normalize_key(license_key) if license_key else ""
        if token:
            info = parse(token)
            if not info.get("ok"):
                return {"ok": False, "reason": info.get("reason") or "licencia"}
            fp = license_fp(token)
            conn.execute("UPDATE users SET license_fp = ? WHERE email = ?", (fp, mail))
            save_key(token)
        if fp:
            seated = _claim_device(conn, fp, did, mail, device_name)
            if not seated.get("ok"):
                conn.rollback()
                return seated
        session = _new_session(conn, mail, did)
        conn.commit()
        return {"ok": True, "session": session, "email": mail, **public_user(mail)}
    finally:
        conn.close()


def _claim_device(conn: sqlite3.Connection, fp: str, device_id: str, email: str, device_name: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT device_id FROM devices WHERE license_fp = ? ORDER BY seen_at",
        (fp,),
    ).fetchall()
    ids = [r["device_id"] for r in rows]
    if device_id in ids:
        conn.execute(
            "UPDATE devices SET email = ?, name = ?, seen_at = ? WHERE license_fp = ? AND device_id = ?",
            (email, _device_name(device_name), _now(), fp, device_id),
        )
        return {"ok": True, "devices": len(ids), "max": MAX_DEVICES}
    if len(ids) >= MAX_DEVICES:
        return {
            "ok": False,
            "reason": "cupo",
            "devices": list_devices(fp),
            "max": MAX_DEVICES,
        }
    conn.execute(
        "INSERT INTO devices(license_fp, device_id, email, name, seen_at) VALUES (?,?,?,?,?)",
        (fp, device_id, email, _device_name(device_name), _now()),
    )
    return {"ok": True, "devices": len(ids) + 1, "max": MAX_DEVICES}


def _new_session(conn: sqlite3.Connection, email: str, device_id: str) -> str:
    token = secrets.token_hex(24)
    expires = time.time() + SESSION_DAYS * 86400
    conn.execute(
        "INSERT INTO sessions(token, email, device_id, created_at, expires_at) VALUES (?,?,?,?,?)",
        (token, email, device_id, _now(), expires),
    )
    return token


def session_user(token: str | None) -> dict[str, Any] | None:
    raw = (token or "").strip()
    if not raw:
        return None
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT email, device_id, expires_at FROM sessions WHERE token = ?",
            (raw,),
        ).fetchone()
        if not row or float(row["expires_at"]) < time.time():
            return None
        return public_user(row["email"])
    finally:
        conn.close()


def logout(token: str | None) -> None:
    raw = (token or "").strip()
    if not raw:
        return
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (raw,))
        conn.commit()
    finally:
        conn.close()


def public_user(email: str) -> dict[str, Any]:
    from config.license import is_licensed, public_status

    mail = normalize_email(email)
    conn = _connect()
    try:
        row = conn.execute("SELECT email, license_fp, created_at FROM users WHERE email = ?", (mail,)).fetchone()
        if not row:
            return {"ok": False, "reason": "cuenta"}
        fp = row["license_fp"] or ""
        devices = list_devices(fp) if fp else []
        lic = public_status()
        return {
            "ok": True,
            "email": mail,
            "licensed": bool(fp) and is_licensed(),
            "license": lic,
            "devices": devices,
            "device_n": len(devices),
            "device_max": MAX_DEVICES,
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def list_devices(fp: str) -> list[dict[str, Any]]:
    if not fp:
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT device_id, email, name, seen_at FROM devices WHERE license_fp = ? ORDER BY seen_at",
            (fp,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def revoke_device(email: str, device_id: str) -> dict[str, Any]:
    mail = normalize_email(email)
    did = (device_id or "").strip()
    conn = _connect()
    try:
        row = conn.execute("SELECT license_fp FROM users WHERE email = ?", (mail,)).fetchone()
        if not row or not row["license_fp"]:
            return {"ok": False, "reason": "cuenta"}
        conn.execute(
            "DELETE FROM devices WHERE license_fp = ? AND device_id = ?",
            (row["license_fp"], did),
        )
        conn.execute("DELETE FROM sessions WHERE device_id = ?", (did,))
        conn.commit()
        return public_user(mail)
    finally:
        conn.close()


def bind_license(email: str, key: str, device_id: str, device_name: str = "") -> dict[str, Any]:
    from config.license import normalize_key, parse, save_key

    mail = normalize_email(email)
    token = normalize_key(key)
    info = parse(token)
    if not info.get("ok"):
        return {"ok": False, "reason": info.get("reason") or "licencia"}
    fp = license_fp(token)
    conn = _connect()
    try:
        row = conn.execute("SELECT email FROM users WHERE email = ?", (mail,)).fetchone()
        if not row:
            return {"ok": False, "reason": "cuenta"}
        seated = _claim_device(conn, fp, device_id, mail, device_name)
        if not seated.get("ok"):
            conn.rollback()
            return seated
        conn.execute("UPDATE users SET license_fp = ? WHERE email = ?", (fp, mail))
        save_key(token)
        conn.commit()
        return {"ok": True, **public_user(mail)}
    finally:
        conn.close()


def admin_accounts(seller_token: str) -> dict[str, Any]:
    expect = (os.environ.get("TNB_SELLER_TOKEN") or "").strip()
    if not expect or not hmac.compare_digest(expect, (seller_token or "").strip()):
        return {"ok": False, "reason": "seller"}
    conn = _connect()
    try:
        users = [dict(r) for r in conn.execute("SELECT email, license_fp, created_at FROM users ORDER BY created_at").fetchall()]
        seats = [dict(r) for r in conn.execute("SELECT license_fp, device_id, email, name, seen_at FROM devices ORDER BY license_fp, seen_at").fetchall()]
        return {"ok": True, "users": users, "devices": seats, "max": MAX_DEVICES}
    finally:
        conn.close()
