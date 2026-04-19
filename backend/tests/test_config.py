from pathlib import Path

from quant_copilot.config import Settings


def test_settings_load_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-test"
    assert s.data_dir == Path(tmp_path / "data")
    assert s.daily_llm_budget_inr == 500
    assert s.market_tz == "Asia/Kolkata"


def test_settings_require_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        Settings(_env_file=None)
    except Exception as e:
        assert "anthropic_api_key" in str(e).lower()
    else:
        raise AssertionError("Settings should have failed without ANTHROPIC_API_KEY")
