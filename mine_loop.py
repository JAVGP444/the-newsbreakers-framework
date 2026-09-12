"""Minería continua (watchlist → RSS/API/HTML → SQLite + MySQL → imágenes CNN).

    python mine_loop.py
    python mine_loop.py --interval 1800

Equivalente: python run_cycle.py --loop --interval 1800

No scrapea todo Internet. LLM no decide la verdad. No reentrena la CNN
en cada ciclo (python -m ai_service.vision.train_cnn).

TNB_DEMO_ROOT es opcional: sin Generador se usa catalog.yaml + config/watchlist.yaml.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_FW = Path(__file__).resolve().parent
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))

from bootstrap import ensure_paths  # noqa: E402

ensure_paths()

from database.mine_state import mine_interval_seconds  # noqa: E402
from pipeline.run import main as cycle_main  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The NewsBreakers — bucle de minería")
    parser.add_argument("--interval", type=int, default=None, help="Segundos entre ciclos (default env/30 min)")
    parser.add_argument("--max-sources", type=int, default=None)
    parser.add_argument("--demo-seed", action="store_true")
    parser.add_argument("--force-due", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo_seed:
        os.environ.setdefault("TNB_DEMO_SEED", "0")
    from config.license import is_licensed

    if not is_licensed():
        print("Sin licencia no hay minería. Activa TNB1 en la app o TNB_LICENSE_KEY.")
        raise SystemExit(2)
    os.environ.setdefault("TNB_FAST", "0")
    interval = mine_interval_seconds(args.interval)
    print(f"[mine] intervalo {interval}s  watchlist RSS/API/HTML  dual-write MySQL+SQLite")
    print("[mine] TNB_DEMO_ROOT opcional; sin Generador se mina la watchlist bundled")
    argv_cycle = ["--loop", "--interval", str(interval)]
    if args.max_sources is not None:
        argv_cycle.extend(["--max-sources", str(args.max_sources)])
    if args.demo_seed:
        argv_cycle.append("--demo-seed")
    if args.force_due:
        argv_cycle.append("--force-due")
    cycle_main(argv_cycle)


if __name__ == "__main__":
    main()
