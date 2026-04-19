from pathlib import Path

from quant_copilot.config import Settings


def ensure_dirs(settings: Settings) -> None:
    for p in [settings.data_dir, settings.backup_dir, settings.parquet_root]:
        Path(p).mkdir(parents=True, exist_ok=True)
