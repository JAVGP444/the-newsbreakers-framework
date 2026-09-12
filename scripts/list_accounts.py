"""Lista cuentas y equipos. Corre en la máquina que tiene accounts.sqlite.

  python scripts/list_accounts.py
  TNB_SELLER_TOKEN=... python scripts/list_accounts.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.accounts import _connect, admin_accounts  # noqa: E402


def main() -> int:
    token = (os.environ.get("TNB_SELLER_TOKEN") or "").strip()
    if token:
        print(json.dumps(admin_accounts(token), indent=2, ensure_ascii=False))
        return 0
    conn = _connect()
    try:
        users = [dict(r) for r in conn.execute("SELECT email, license_fp, created_at FROM users ORDER BY created_at")]
        devices = [
            dict(r)
            for r in conn.execute(
                "SELECT license_fp, device_id, email, name, seen_at FROM devices ORDER BY license_fp, seen_at"
            )
        ]
    finally:
        conn.close()
    print(json.dumps({"users": users, "devices": devices, "max": 3}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
