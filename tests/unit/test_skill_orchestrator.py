"""Validate the /mythos SKILL.md structure."""
import yaml
from pathlib import Path
import pytest


SKILL_PATH = (
    Path(__file__).parent.parent.parent / ".claude" / "skills" / "mythos" / "SKILL.md"
)


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---")
    parts = content.split("---", 2)
    return yaml.safe_load(parts[1]) or {}, parts[2]


def test_skill_file_exists():
    assert SKILL_PATH.is_file(), f"missing: {SKILL_PATH}"


def test_frontmatter_has_name_and_description():
    fm, _ = _split_frontmatter(SKILL_PATH)
    assert fm["name"] == "mythos"
    assert "description" in fm
    assert len(fm["description"]) > 50


def test_body_describes_all_8_phases():
    _, body = _split_frontmatter(SKILL_PATH)
    for phase in ["Recon", "Hunt", "Validate", "Gapfill", "Dedupe", "Trace", "Feedback", "Report"]:
        assert phase in body, f"phase '{phase}' missing from skill body"


def test_body_mentions_all_8_leads():
    _, body = _split_frontmatter(SKILL_PATH)
    leads = ["mythos-recon", "mythos-hunt-lead", "mythos-validate",
             "mythos-gapfill", "mythos-dedupe", "mythos-trace",
             "mythos-feedback", "mythos-report"]
    for lead in leads:
        assert lead in body, f"lead {lead!r} missing from skill body"


def test_body_lists_5_subcommands():
    _, body = _split_frontmatter(SKILL_PATH)
    for cmd in ["start", "status", "resume", "abort", "clean"]:
        assert f"/mythos {cmd}" in body, f"subcommand /mythos {cmd!r} missing"


def test_body_references_disclaimer():
    _, body = _split_frontmatter(SKILL_PATH)
    assert "disclaimer" in body.lower()
    assert "dual-use" in body.lower() or "acknowledgment" in body.lower()


def test_body_references_hash_chain():
    _, body = _split_frontmatter(SKILL_PATH)
    assert "hash chain" in body.lower() or "hash_chain" in body


def test_body_describes_iteration_caps():
    _, body = _split_frontmatter(SKILL_PATH)
    assert "3" in body  # gapfill cap
    assert "1" in body  # feedback cap


def test_trust_boundary_present():
    _, body = _split_frontmatter(SKILL_PATH)
    assert "TRUST BOUNDARY" in body
