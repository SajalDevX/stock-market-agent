from typer.testing import CliRunner

from quant_copilot.cli import app

runner = CliRunner()


def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("fetch-ohlc", "ingest-news", "refresh-asm", "archive", "backup",
                "analyze-technical", "analyze-fundamental"):
        assert cmd in result.output


def test_analyze_technical_help():
    result = runner.invoke(app, ["analyze-technical", "--help"])
    assert result.exit_code == 0
    assert "TICKER" in result.output.upper()
    assert "--timeframe" in result.output


def test_analyze_fundamental_help():
    result = runner.invoke(app, ["analyze-fundamental", "--help"])
    assert result.exit_code == 0
    assert "TICKER" in result.output.upper()
