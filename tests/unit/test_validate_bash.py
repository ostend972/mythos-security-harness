"""Tests for validate_bash.py PreToolUse hook."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "validate_bash.py"


def invoke(hook_input: dict) -> tuple[int, str, str]:
    """Invoke validate_bash.py with the given hook input JSON. Return (rc, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)]
    r = subprocess.run(
        cmd,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def hook(cmd: str) -> dict:
    """Build a minimal PreToolUse hook payload for a Bash command."""
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


@pytest.mark.parametrize("dangerous_cmd", [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf $HOME",
    "rm -rf /etc",
    "chmod 777 /",
    "chmod 777 /etc",
    "chown root /tmp/something",
    "sudo apt install x",
    "sudo bash",
    "su -",
    "su root",
    "setcap cap_net_admin+ep /usr/bin/something",
    "docker run --privileged alpine",
    "docker run -v /var/run/docker.sock:/var/run/docker.sock alpine",
    "cat /etc/shadow",
    "cat /etc/sudoers",
    "cat ~/.ssh/id_rsa",
    "cat ~/.aws/credentials",
    "cat ~/.config/gcloud/credentials.db",
    "cp anything ~/.kube/config",
    "ssh-add ~/.ssh/id_rsa",
])
def test_blocks_dangerous_commands(dangerous_cmd):
    rc, out, err = invoke(hook(dangerous_cmd))
    assert rc == 2, f"Expected block for: {dangerous_cmd!r}\nstdout={out}\nstderr={err}"


@pytest.mark.parametrize("safe_cmd", [
    "ls -la",
    "pytest tests/",
    "git status",
    "python preflight.py",
    "rm -rf .mythos/poc/F-test/",  # under .mythos/ is allowed
    "mkdir -p .mythos/state",
    "docker info",
    "docker ps",
])
def test_allows_safe_commands(safe_cmd):
    rc, out, err = invoke(hook(safe_cmd))
    assert rc == 0, f"Expected allow for: {safe_cmd!r}\nstdout={out}\nstderr={err}"


def test_empty_input_allows():
    """Empty stdin (malformed hook payload) should not block."""
    rc, out, err = invoke({})
    assert rc == 0


def test_non_bash_tool_allows():
    """Hook only applies to Bash. Other tools pass through."""
    rc, out, err = invoke({"tool_name": "Write", "tool_input": {"file_path": "any.txt"}})
    assert rc == 0
