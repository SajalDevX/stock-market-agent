from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path


def backup_sqlite(src: Path, backup_dir: Path, date_str: str | None = None) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    date_str = date_str or date.today().isoformat()
    raw_tmp = backup_dir / f".{date_str}.sqlite.tmp"
    final = backup_dir / f"{date_str}.sqlite.gz"

    # Use SQLite's online backup API so we don't need to pause writers
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(raw_tmp))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()

    with open(raw_tmp, "rb") as f_in, gzip.open(final, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    raw_tmp.unlink()
    return final


def prune_backups(backup_dir: Path, keep_days: int = 30) -> None:
    backups = sorted(backup_dir.glob("*.sqlite.gz"))
    if len(backups) <= keep_days:
        return
    for old in backups[:-keep_days]:
        old.unlink()
