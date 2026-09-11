"""Genera miniaturas JPEG reales (o tarjetas de contenido) para artículos sin thumb."""
from __future__ import annotations

import os
import sys
from pathlib import Path

FW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FW))

from bootstrap import ensure_paths  # noqa: E402

ensure_paths()

from database.store import Store  # noqa: E402
from database.thumbs import backfill_missing  # noqa: E402


def main() -> None:
    store = Store()
    limit = int(os.environ.get("TNB_THUMB_LIMIT", "400"))
    n = backfill_missing(store, limit=limit, fetch_html=True)
    print(f"thumbs backfilled: {n}")
    store.close()


if __name__ == "__main__":
    main()
