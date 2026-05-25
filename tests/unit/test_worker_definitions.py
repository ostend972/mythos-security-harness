"""Structural validation tests for all Mythos worker agent definitions.

Every worker must have:
- YAML frontmatter with required keys (name, description, model, tools, ...)
- The `name` field matching the filename stem
- A non-empty system prompt body
- Reference to TRUST BOUNDARY in the body (anti-injection guardrail)
"""
import re
from pathlib import Path
import pytest
import yaml


WORKERS_DIR = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "workers"
)


def _worker_files() -> list[Path]:
    return sorted(WORKERS_DIR.glob("*.md"))


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{path.name}: must start with ---"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{path.name}: malformed frontmatter"
    return yaml.safe_load(parts[1]) or {}, parts[2]


EXPECTED_WORKERS = {"mythos-scout", "mythos-hunter", "mythos-explorer", "mythos-tracer"}


def test_all_4_workers_present():
    names = {p.stem for p in _worker_files()}
    assert names == EXPECTED_WORKERS, f"missing or extra workers: {names ^ EXPECTED_WORKERS}"


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_required_frontmatter_keys(path):
    fm, _ = _split_frontmatter(path)
    for key in ["name", "description", "version", "model", "effort", "tools", "permissionMode"]:
        assert key in fm, f"{path.name}: missing frontmatter key '{key}'"


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_name_matches_filename(path):
    fm, _ = _split_frontmatter(path)
    assert fm["name"] == path.stem, (
        f"{path.name}: frontmatter name '{fm['name']}' != filename stem '{path.stem}'"
    )


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_model_is_opus(path):
    fm, _ = _split_frontmatter(path)
    assert fm["model"] == "opus", f"{path.name}: workers must use opus, got {fm['model']!r}"


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_effort_is_max(path):
    fm, _ = _split_frontmatter(path)
    assert fm["effort"] == "max", f"{path.name}: workers must use effort=max, got {fm['effort']!r}"


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_trust_boundary_in_body(path):
    _, body = _split_frontmatter(path)
    assert "TRUST BOUNDARY" in body, (
        f"{path.name}: body must contain a TRUST BOUNDARY section "
        "(anti prompt-injection guardrail required by spec §11 T5)"
    )


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_tools_field_is_list_or_csv(path):
    fm, _ = _split_frontmatter(path)
    tools = fm["tools"]
    # Acceptable: comma-separated string OR explicit YAML list
    assert isinstance(tools, (str, list)), (
        f"{path.name}: tools must be a string or list, got {type(tools).__name__}"
    )


@pytest.mark.parametrize("path", _worker_files(), ids=lambda p: p.name)
def test_body_is_non_empty(path):
    _, body = _split_frontmatter(path)
    assert len(body.strip()) > 200, (
        f"{path.name}: body is suspiciously short ({len(body.strip())} chars)"
    )


def test_hunter_can_spawn_explorer():
    """Hunter is the only worker permitted to spawn other sub-agents."""
    hunter = WORKERS_DIR / "mythos-hunter.md"
    fm, _ = _split_frontmatter(hunter)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Agent(mythos-explorer)" in tools_str, (
        "hunter must declare Agent(mythos-explorer) in tools"
    )


def test_scout_does_not_have_write_or_agent():
    """Scout is read-only and may not spawn agents."""
    scout = WORKERS_DIR / "mythos-scout.md"
    fm, _ = _split_frontmatter(scout)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Write" not in tools_str, "scout must not have Write"
    assert "Edit" not in tools_str, "scout must not have Edit"
    assert "Agent" not in tools_str, "scout must not be able to spawn sub-agents"


def test_tracer_only_writes_to_traces_dir():
    """Tracer must declare an allow_pattern restricting writes to .mythos/traces/."""
    tracer = WORKERS_DIR / "mythos-tracer.md"
    _, body = _split_frontmatter(tracer)
    fm, _ = _split_frontmatter(tracer)
    # Hooks field is parsed YAML; serialize to string to check pattern presence
    hooks_str = str(fm.get("hooks", ""))
    assert "traces" in hooks_str, "tracer must restrict writes to .mythos/traces/"


def test_explorer_does_not_have_write():
    """Explorer is read-only (mostly); it cannot Write or Edit."""
    explorer = WORKERS_DIR / "mythos-explorer.md"
    fm, _ = _split_frontmatter(explorer)
    tools = fm["tools"]
    tools_str = tools if isinstance(tools, str) else ", ".join(tools)
    assert "Write" not in tools_str, "explorer must not have Write"
    assert "Edit" not in tools_str, "explorer must not have Edit"
