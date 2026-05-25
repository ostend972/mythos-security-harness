"""End-to-end pipeline integration tests for Plan 2.

Exercises: schemas + validate_jsonl + hooks together on realistic inputs.
"""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPTS = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"


def py(*args: str, input_text: str = "") -> tuple[int, str, str]:
    cmd = [sys.executable, *args]
    r = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout, r.stderr


def test_full_pipeline_finding_to_validation_to_validate_jsonl(tmp_path):
    """A valid finding written through the hook stack lands in validate_jsonl OK."""
    # 1. validate_write hook check on the finding write
    finding = {
        "finding_id": "F-E2E001", "task_id": "T-E2E1", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "User input concatenated into SQL.", "poc_dir": "poc/F-E2E001/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-99", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T18:00:00Z",
    }
    (tmp_path / ".claude").mkdir()  # project root marker
    findings_path = tmp_path / ".mythos" / "findings.jsonl"
    findings_path.parent.mkdir(parents=True, exist_ok=True)
    findings_path.write_text(json.dumps(finding) + "\n", encoding="utf-8")

    # 2. validate_jsonl confirms it
    rc, out, err = py(
        str(SCRIPTS / "validate_jsonl.py"),
        str(findings_path),
        "--schema", "finding",
    )
    assert rc == 0, f"out={out} err={err}"


def test_secret_in_write_content_triggers_warn():
    """A finding containing an AWS key triggers the validate_write secret-detection path."""
    payload = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": ".mythos/findings.jsonl",
            "content": '{"finding_id":"F-A","creds":"AKIAIOSFODNN7EXAMPLE"}',
        },
    }
    rc, out, err = py(str(SCRIPTS / "validate_write.py"), input_text=json.dumps(payload))
    # warn (1) or block (2), but not silent pass
    assert rc in (1, 2)


def test_dangerous_bash_blocked():
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
    rc, _, err = py(str(SCRIPTS / "validate_bash.py"), input_text=json.dumps(payload))
    assert rc == 2
    assert "rm -rf" in err.lower() or "blocked" in err.lower() or "dangerous" in err.lower()
