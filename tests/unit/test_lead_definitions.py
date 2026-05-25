"""Structural validation tests for all 8 Mythos lead agents."""
import re
from pathlib import Path
import pytest
import yaml


LEADS_DIR = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "leads"
)


def _lead_files() -> list[Path]:
    return sorted(LEADS_DIR.glob("*.md"))


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{path.name}: must start with ---"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{path.name}: malformed frontmatter"
    return yaml.safe_load(parts[1]) or {}, parts[2]


EXPECTED_LEADS = {
    "mythos-recon", "mythos-hunt-lead", "mythos-validate", "mythos-gapfill",
    "mythos-dedupe", "mythos-trace", "mythos-feedback", "mythos-report",
}


def test_all_8_leads_present():
    names = {p.stem for p in _lead_files()}
    assert names == EXPECTED_LEADS, f"missing or extra: {names ^ EXPECTED_LEADS}"


@pytest.mark.parametrize("path", _lead_files(), ids=lambda p: p.name)
def test_required_frontmatter_keys(path):
    fm, _ = _split_frontmatter(path)
    for key in ["name", "description", "version", "model", "effort", "tools", "permissionMode"]:
        assert key in fm, f"{path.name}: missing frontmatter key '{key}'"


@pytest.mark.parametrize("path", _lead_files(), ids=lambda p: p.name)
def test_name_matches_filename(path):
    fm, _ = _split_frontmatter(path)
    assert fm["name"] == path.stem


@pytest.mark.parametrize("path", _lead_files(), ids=lambda p: p.name)
def test_model_is_opus(path):
    fm, _ = _split_frontmatter(path)
    assert fm["model"] == "opus"


@pytest.mark.parametrize("path", _lead_files(), ids=lambda p: p.name)
def test_effort_is_max(path):
    fm, _ = _split_frontmatter(path)
    assert fm["effort"] == "max"


@pytest.mark.parametrize("path", _lead_files(), ids=lambda p: p.name)
def test_trust_boundary_in_body(path):
    _, body = _split_frontmatter(path)
    assert "TRUST BOUNDARY" in body, f"{path.name}: must include TRUST BOUNDARY section"


def test_validate_lead_does_not_have_agent_tool():
    """Validate must NOT have Agent tool — it cannot spawn helpers."""
    validate = LEADS_DIR / "mythos-validate.md"
    fm, _ = _split_frontmatter(validate)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Agent" not in tools_str, "validate MUST NOT have Agent tool (anti-correlation)"


def test_recon_can_spawn_scouts():
    """Recon needs Agent(mythos-scout) to dispatch parallel scouts."""
    recon = LEADS_DIR / "mythos-recon.md"
    fm, _ = _split_frontmatter(recon)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Agent(mythos-scout)" in tools_str


def test_hunt_lead_does_not_have_agent_tool():
    """Hunt-lead orchestrates via launch_hunters.py subprocess, not Agent tool."""
    hunt_lead = LEADS_DIR / "mythos-hunt-lead.md"
    fm, _ = _split_frontmatter(hunt_lead)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Agent" not in tools_str


def test_report_forbidden_words_documented():
    """Report agent must explicitly list forbidden vague-language words."""
    report = LEADS_DIR / "mythos-report.md"
    _, body = _split_frontmatter(report)
    for word in ["potentially", "possibly", "could", "appears to"]:
        assert word in body, (
            f"report body must mention '{word}' as forbidden vague language"
        )


def test_gapfill_has_iteration_cap():
    """Gapfill must reference its 3-iteration cap."""
    gf = LEADS_DIR / "mythos-gapfill.md"
    _, body = _split_frontmatter(gf)
    assert "3" in body and "ITERATIONS" in body.upper()


def test_feedback_has_iteration_cap():
    """Feedback must reference its 1-iteration cap."""
    fb = LEADS_DIR / "mythos-feedback.md"
    _, body = _split_frontmatter(fb)
    assert "1" in body and "ITERATIONS" in body.upper()
