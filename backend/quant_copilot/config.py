from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    data_dir: Path = Field(Path("./data"), alias="DATA_DIR")
    backup_dir: Path = Field(Path("./backups"), alias="BACKUP_DIR")
    daily_llm_budget_inr: int = Field(500, alias="DAILY_LLM_BUDGET_INR")
    yfinance_rpm: int = Field(120, alias="YFINANCE_RPM")
    screener_rpm: int = Field(20, alias="SCREENER_RPM")
    rss_poll_interval_min: int = Field(15, alias="RSS_POLL_INTERVAL_MIN")
    market_tz: str = Field("Asia/Kolkata", alias="MARKET_TZ")

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "quant_copilot.db"

    @property
    def parquet_root(self) -> Path:
        return self.data_dir / "ohlc"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
