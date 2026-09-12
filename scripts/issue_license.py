"""Emite una clave TNB1. Corre desde la raíz del pack:

  python scripts/issue_license.py --who cliente@correo --days 365 --features mine,llm,ocr
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.license import FEATURES, issue, parse  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Emitir licencia The NewsBreakers")
    p.add_argument("--who", required=True, help="correo o nombre del cliente")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--features", default="mine,llm,ocr", help="mine,llm,ocr")
    args = p.parse_args()
    feats = [x.strip() for x in args.features.split(",") if x.strip()]
    bad = [f for f in feats if f not in FEATURES]
    if bad:
        print("features desconocidas:", ", ".join(bad), file=sys.stderr)
        return 1
    key = issue(args.who, days=args.days, features=feats)
    info = parse(key)
    print(key)
    print(f"# {info.get('who')}  caduca {info.get('exp')}  {','.join(info.get('features') or [])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
