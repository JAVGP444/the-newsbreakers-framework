"""Copia de seguridad de tnb.db (SQLite WAL-safe). Conserva las últimas 7."""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from bootstrap import DATA_DIR, DB_PATH, ensure_paths

BACKUP_DIR = DATA_DIR / "backups"
KEEP = 7


def backup_sqlite(db_path: Path | str | None = None, dest_dir: Path | None = None, keep: int = KEEP) -> Path | None:
    """Copia tnb.db → data/backups/tnb-YYYYMMDD-HHMM.db y borra copias viejas."""
    ensure_paths()
    src = Path(db_path or DB_PATH)
    if not src.is_file():
        return None
    folder = Path(dest_dir or BACKUP_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    dest = folder / f"tnb-{stamp}.db"
    src_conn = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()
    rotate_backups(folder, keep=keep)
    return dest


def rotate_backups(folder: Path, keep: int = KEEP) -> list[Path]:
    files = sorted(
        [p for p in folder.glob("tnb-*.db") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for old in files[max(0, keep) :]:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            continue
    return removed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Backup SQLite tnb.db")
    parser.add_argument("--keep", type=int, default=KEEP)
    args = parser.parse_args(argv)
    path = backup_sqlite(keep=args.keep)
    if path:
        print(f"backup {path}")
    else:
        print("no db")


if __name__ == "__main__":
    main()
