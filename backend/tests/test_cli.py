from typer.testing import CliRunner

from quant_copilot.cli import app

runner = CliRunner()


def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("fetch-ohlc", "ingest-news", "refresh-asm", "archive", "backup"):
        assert cmd in result.output
