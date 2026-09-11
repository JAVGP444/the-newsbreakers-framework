"""Estado de minería (última corrida / próximo ciclo) — archivo local OneDrive-friendly."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bootstrap import PROCESSED_DIR

STATE_PATH = PROCESSED_DIR / "mine_state.json"


def mine_interval_seconds(cli_interval: int | None = None) -> int:
    if cli_interval and cli_interval > 0:
        return int(cli_interval)
    try:
        minutes = int(os.environ.get("TNB_MINE_INTERVAL_MINUTES") or 30)
    except ValueError:
        minutes = 30
    return max(60, minutes * 60)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def read_mine_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_mine_state(payload: dict[str, Any]) -> dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    prev = read_mine_state()
    prev.update(payload)
    STATE_PATH.write_text(json.dumps(prev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return prev


def record_cycle(summary: dict[str, Any], interval_seconds: int | None = None) -> dict[str, Any]:
    interval = mine_interval_seconds(interval_seconds)
    now = _now()
    nxt = now + timedelta(seconds=interval)
    prev = read_mine_state()
    state = {
        **prev,
        "last_mine": summary.get("ran_at") or now.isoformat(),
        "next_mine": nxt.isoformat(),
        "interval_seconds": interval,
        "cycle_id": summary.get("cycle_id"),
        "articles_new": summary.get("articles_new"),
        "images_processed": summary.get("images_processed"),
        "cnn_samples_new": summary.get("cnn_samples_new"),
        "errors": len(summary.get("errors") or []),
        "mysql": bool((summary.get("mysql") or {}).get("connected")),
        "kpis": summary.get("kpis") or {},
    }
    extra = summary.get("extra") or {}
    if "gdelt_offset_days" in extra:
        state["gdelt_offset_days"] = extra["gdelt_offset_days"]
    elif summary.get("gdelt_offset_days") is not None:
        state["gdelt_offset_days"] = summary["gdelt_offset_days"]
    return write_mine_state(state)


def mine_banner(state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state if state is not None else read_mine_state()
    last = state.get("last_mine")
    nxt = state.get("next_mine")
    minutes = None
    if nxt:
        try:
            dt = datetime.fromisoformat(str(nxt).replace("Z", "+00:00"))
            minutes = max(0, int((dt - _now()).total_seconds() // 60))
        except ValueError:
            minutes = None
    return {
        "last_mine": last,
        "next_mine": nxt,
        "next_mine_minutes": minutes,
        "interval_seconds": state.get("interval_seconds"),
        "articles_new": state.get("articles_new"),
        "images_processed": state.get("images_processed"),
        "cnn_samples_new": state.get("cnn_samples_new"),
        "mysql": state.get("mysql"),
    }
