"""Agent instruction files stay in sync, and the Documentation map covers docs/."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_claude_and_agents_differ_only_in_header():
    claude = (ROOT / "CLAUDE.md").read_text().splitlines()
    agents = (ROOT / "AGENTS.md").read_text().splitlines()
    assert claude[3:] == agents[3:]


def test_every_doc_is_in_the_documentation_map():
    text = (ROOT / "CLAUDE.md").read_text()
    section = text.split("## Documentation map", 1)[1].split("\n## ", 1)[0]
    # Top level only: subdirectories hold task records, not product docs.
    docs = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md"))
    assert docs
    missing = [d for d in docs if f"`{d}`" not in section]
    assert not missing, f"not in CLAUDE.md's Documentation map: {missing}"
