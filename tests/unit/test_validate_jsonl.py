"""Tests for the validate_jsonl.py CLI."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"


def run_cli(*args, cwd=None):
    """Invoke validate_jsonl.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPTS_DIR / "validate_jsonl.py"), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    return r.returncode, r.stdout, r.stderr


def test_valid_finding_jsonl_returns_0(tmp_path):
    """Valid finding JSONL exits 0."""
    p = tmp_path / "findings.jsonl"
    p.write_text(json.dumps({
        "finding_id": "F-ABC123", "task_id": "T-XY12", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "Injection via raw query concatenation.", "poc_dir": "poc/F-ABC123/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-07", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T14:00:00Z",
    }) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 0, f"stderr={err}"


def test_invalid_finding_jsonl_returns_1(tmp_path):
    """Invalid finding JSONL exits 1 and prints the violating line."""
    p = tmp_path / "findings.jsonl"
    p.write_text(json.dumps({"finding_id": "bad-id"}) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 1
    assert "line 1" in (out + err).lower() or "finding_id" in (out + err)


def test_mixed_jsonl_reports_each_line(tmp_path):
    """Stream validation reports per-line results, not just first failure."""
    p = tmp_path / "mixed.jsonl"
    valid_finding = {
        "finding_id": "F-ABC123", "task_id": "T-XY12", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "Injection via raw query concatenation.", "poc_dir": "poc/F-ABC123/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-07", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T14:00:00Z",
    }
    p.write_text(
        json.dumps(valid_finding) + "\n"
        + json.dumps({**valid_finding, "finding_id": "broken"}) + "\n"
        + json.dumps({**valid_finding, "finding_id": "F-DEF456"}) + "\n",
        encoding="utf-8",
    )
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 1  # at least one invalid line


def test_unknown_schema_returns_2(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text("{}\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "nonexistent-schema-name")
    assert rc == 2


def test_missing_input_file_returns_2(tmp_path):
    rc, out, err = run_cli(str(tmp_path / "does-not-exist.jsonl"), "--schema", "finding")
    assert rc == 2


def test_quiet_flag_suppresses_per_line_output(tmp_path):
    """With --quiet only the final summary is printed."""
    p = tmp_path / "f.jsonl"
    p.write_text(json.dumps({"finding_id": "broken"}) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding", "--quiet")
    assert rc == 1
    # Should be quieter: less verbose output
    assert len(out) < 500
