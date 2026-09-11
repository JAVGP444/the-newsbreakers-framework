"""Scheduler de watchlist — un ciclo o --loop según next_check.

    python ingestion/scheduler.py
    python -m pipeline.run --loop
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ING = Path(__file__).resolve().parent
if str(_ING) not in sys.path:
    sys.path.insert(0, str(_ING))
_FW = _ING.parent
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import ensure_paths  # noqa: E402

ensure_paths()

from access import resolve_access  # noqa: E402
from source_catalog import frequency_minutes, is_due, next_check, sources_due  # noqa: E402

due = is_due


def run_cycle(now: datetime | None = None, persist_last_checked: bool = True) -> dict[str, Any]:
    from pipeline.run import run_cycle as _run

    return _run()


def plan(now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    rows = []
    for source in sources_due(now=now, methods=("api", "rss", "scrape")):
        rows.append(
            {
                "source_id": source.get("source_id"),
                "name": source.get("name"),
                "access": resolve_access(source),
                "frequency_minutes": frequency_minutes(source),
                "next_check": next_check(source, now=now).isoformat(),
                "due": is_due(source, now=now),
            }
        )
    return rows


def main() -> None:
    result = run_cycle()
    summary = {k: v for k, v in result.items() if k not in {"items"}}
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
