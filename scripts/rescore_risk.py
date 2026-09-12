"""Recalcula veredictos ya guardados con las seis señales (no Fake/Real).

  python scripts/rescore_risk.py
  python scripts/rescore_risk.py --db "$HOME/Library/Application Support/TheNewsBreakers/data/processed/tnb.db"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap import DB_PATH, ensure_paths  # noqa: E402

ensure_paths()

from database.store import Store  # noqa: E402
from pipeline.run import refresh_article_risk  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--limit", type=int, default=0, help="0 = todos")
    args = p.parse_args()
    db = Path(args.db)
    if not db.is_file():
        print(f"no está {db}", file=sys.stderr)
        return 1
    store = Store(db)
    rows = store.list_articles(limit=args.limit or 5000)
    n = 0
    for row in rows:
        cid = row.get("content_id")
        if not cid:
            continue
        refresh_article_risk(store, cid)
        n += 1
    store.close()
    print(f"rescored {n} {db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
