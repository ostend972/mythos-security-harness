"""Tests for agent_start.py SubagentStart hook."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "agent_start.py"


def invoke(payload: dict) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def test_non_mythos_agent_passes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, _, _ = invoke({"agent_type": "general-purpose"})
    assert rc == 0


def test_mythos_agent_creates_audit_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Project root needs a .claude/ dir for paths.project_root() to succeed
    (tmp_path / ".claude").mkdir()
    rc, _, _ = invoke({"agent_type": "mythos-hunter"})
    assert rc == 0
    audit = tmp_path / ".mythos" / "audit.jsonl"
    if audit.exists():
        content = audit.read_text(encoding="utf-8")
        assert "agent_start" in content
        assert "mythos-hunter" in content


def test_empty_input_safe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, _, _ = invoke({})
    assert rc == 0
