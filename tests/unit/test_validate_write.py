"""Tests for validate_write.py PostToolUse hook."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "validate_write.py"


def invoke(hook_input: dict, *extra_args: str) -> tuple[int, str, str]:
    cmd = [sys.executable, str(SCRIPT), *extra_args]
    r = subprocess.run(
        cmd, input=json.dumps(hook_input), capture_output=True, text=True, timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def write_hook(path: str, content: str = "") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_hook(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


class TestPathTraversal:
    def test_blocks_parent_dir_traversal(self):
        rc, out, err = invoke(write_hook(".mythos/poc/../../../etc/passwd"))
        assert rc == 2, f"stderr={err}"

    def test_blocks_absolute_path_outside_project(self):
        rc, out, err = invoke(write_hook("/etc/passwd"))
        assert rc == 2

    def test_allows_normal_path_inside_mythos(self):
        rc, out, err = invoke(write_hook(".mythos/poc/F-test/run.sh"))
        assert rc == 0


class TestAllowPattern:
    def test_allow_pattern_restricts_writes(self):
        # With --allow-pattern, writes outside the allowed regex are blocked
        rc, out, err = invoke(
            write_hook(".claude/agents/mythos/scripts/oops.py"),
            "--allow-pattern", r"^\.mythos/findings\.jsonl$",
        )
        assert rc == 2

    def test_allow_pattern_permits_matching(self):
        rc, out, err = invoke(
            write_hook(".mythos/findings.jsonl"),
            "--allow-pattern", r"^\.mythos/findings\.jsonl$",
        )
        assert rc == 0


class TestSecretLeakage:
    def test_blocks_aws_key_in_write_content(self):
        rc, out, err = invoke(write_hook(
            ".mythos/findings.jsonl",
            content='{"finding_id":"F-A","creds":"AKIAIOSFODNN7EXAMPLE"}',
        ))
        # Either block (2) or warn (1) — but must not silently allow
        assert rc != 0


class TestNonWriteToolPassthrough:
    def test_read_passes_through(self):
        rc, out, err = invoke({"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}})
        assert rc == 0

    def test_bash_passes_through(self):
        rc, out, err = invoke({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert rc == 0


def test_empty_input_allows():
    rc, out, err = invoke({})
    assert rc == 0
