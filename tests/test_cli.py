from click.testing import CliRunner

from maxscriber.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "MaXScriber v2.0 | Universal Medical PDF Extractor" in result.output
    assert "run" in result.output
    assert "schema" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "MaxScriber, version 0.1.0" in result.output
