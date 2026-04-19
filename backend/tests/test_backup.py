import gzip
import sqlite3
from pathlib import Path

import pytest

from quant_copilot.jobs.backup import backup_sqlite, prune_backups


def test_backup_sqlite_creates_compressed_copy(tmp_path):
    src = tmp_path / "db.sqlite"
    # Real sqlite file so the backup API works
    conn = sqlite3.connect(src)
    conn.execute("CREATE TABLE t(x INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    out = backup_sqlite(src, backup_dir, date_str="2026-04-20")

    assert out.exists()
    assert out.name == "2026-04-20.sqlite.gz"
    # Decompress and verify content
    with gzip.open(out, "rb") as fh:
        raw = fh.read()
    assert raw.startswith(b"SQLite format 3")


def test_prune_keeps_last_n(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    for d in ["2026-04-10", "2026-04-15", "2026-04-20", "2026-04-22"]:
        (bdir / f"{d}.sqlite.gz").write_bytes(b"x")
    prune_backups(bdir, keep_days=2)
    remaining = sorted(p.name for p in bdir.iterdir())
    assert remaining == ["2026-04-20.sqlite.gz", "2026-04-22.sqlite.gz"]
