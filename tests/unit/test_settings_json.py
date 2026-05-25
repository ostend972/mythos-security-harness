"""Validate .claude/settings.json structure."""
import json
from pathlib import Path
import pytest


SETTINGS_PATH = Path(__file__).parent.parent.parent / ".claude" / "settings.json"


@pytest.fixture(scope="module")
def settings():
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def test_settings_is_valid_json(settings):
    assert isinstance(settings, dict)


def test_env_section_present(settings):
    assert "env" in settings
    env = settings["env"]
    assert env["CLAUDE_CODE_SUBAGENT_MODEL"] == "claude-opus-4-7"
    assert env["CLAUDE_CODE_EFFORT_LEVEL"] == "max"
    assert env["MYTHOS_PARALLEL_HUNTERS"] == "50"


def test_hooks_section_has_subagent_start(settings):
    hooks = settings.get("hooks", {})
    starts = hooks.get("SubagentStart", [])
    assert any("mythos-" in entry.get("matcher", "") for entry in starts), \
        "SubagentStart hook missing mythos- matcher"


def test_hooks_section_has_stop_with_cleanup(settings):
    hooks = settings.get("hooks", {})
    stops = hooks.get("Stop", [])
    found_cleanup = False
    for entry in stops:
        for h in entry.get("hooks", []):
            if "cleanup_orphans" in h.get("command", ""):
                found_cleanup = True
    assert found_cleanup, "Stop hook missing cleanup_orphans"


def test_permissions_deny_includes_catastrophic(settings):
    deny = settings.get("permissions", {}).get("deny", [])
    deny_str = " ".join(deny)
    for must_block in ["rm -rf /", "sudo", "docker run --privileged"]:
        assert must_block in deny_str, f"deny list missing: {must_block!r}"


def test_iteration_caps_match_spec(settings):
    env = settings["env"]
    assert env["MYTHOS_GAPFILL_MAX_ITER"] == "3"
    assert env["MYTHOS_FEEDBACK_MAX_ITER"] == "1"
