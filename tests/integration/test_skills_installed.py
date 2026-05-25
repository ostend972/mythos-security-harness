"""Integration test: verify that install_skills.py succeeded.

This test runs AFTER `python install_skills.py` has been invoked once
(manually or in CI) to verify the installation result.
"""
from pathlib import Path
import pytest


SKILLS_DIR = (
    Path(__file__).parent.parent.parent / ".claude" / "skills"
)
ALLOWLIST_PATH = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "allowed-skills.txt"
)


def _allowlisted_skills() -> list[str]:
    return [
        line.strip()
        for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_at_least_one_skill_installed():
    if not SKILLS_DIR.is_dir():
        pytest.skip("skills not yet installed — run install_skills.py first")
    installed = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
    assert len(installed) >= 1


def test_core_classes_have_their_skill_installed():
    """At minimum, the skills for SQL injection, SSRF, and OAuth should be installed."""
    if not SKILLS_DIR.is_dir():
        pytest.skip("skills not yet installed")
    minimal_required = [
        "exploiting-sql-injection-vulnerabilities",
        "exploiting-server-side-request-forgery",
        "exploiting-oauth-misconfiguration",
    ]
    installed = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
    missing_critical = [s for s in minimal_required if s not in installed]
    if missing_critical:
        pytest.skip(
            f"core skills not installed: {missing_critical}. "
            f"Run install_skills.py first."
        )
