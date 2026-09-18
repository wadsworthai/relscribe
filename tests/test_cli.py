"""Smoke tests for the CLI skeleton: version, usage errors, exit codes."""

from __future__ import annotations

from importlib.metadata import version


def test_version_text(cli):
    result = cli("--version")
    assert result.code == 0
    assert result.out.strip() == version("relscribe")


def test_version_json(cli):
    result = cli("--json", "--version")
    assert result.code == 0
    assert result.json() == {"version": version("relscribe")}


def test_no_command_is_a_usage_error(cli):
    result = cli()
    assert result.code == 2
    assert "relscribe: error: a command is required" in result.err


def test_unknown_command_is_a_usage_error(cli):
    result = cli("no-such-command")
    assert result.code == 2
    assert "relscribe: error:" in result.err
