"""Smoke tests for invoking worker agents via the `claude` CLI.

These tests are SLOW (each spawns a real `claude --agent` subprocess that calls
the Anthropic API) and require:
- `claude` CLI on PATH
- Active Claude Code subscription (Max 20x in our case)

They're marked with @pytest.mark.slow and SKIPPED by default. Run explicitly:
    pytest tests/integration/test_worker_invocation.py -m slow
"""
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def claude_cli_available():
    if not shutil.which("claude"):
        pytest.skip("claude CLI not on PATH")
    return True


def invoke_claude_agent(agent_name: str, prompt: str, timeout_s: int = 120) -> tuple[int, str, str]:
    """Invoke `claude --agent <name> -p <prompt>` and return (rc, stdout, stderr)."""
    r = subprocess.run(
        ["claude", "--agent", agent_name, "-p", prompt],
        capture_output=True, text=True, timeout=timeout_s,
    )
    return r.returncode, r.stdout, r.stderr


@pytest.mark.slow
@pytest.mark.parametrize("agent_name", ["mythos-scout", "mythos-hunter", "mythos-explorer", "mythos-tracer"])
def test_worker_responds_to_trivial_prompt(agent_name, claude_cli_available):
    """Each worker should respond with a non-empty, non-error message to a trivial prompt.

    Acceptance:
    - exit code 0
    - stdout contains some text (not just whitespace)
    - stdout does NOT contain 'SANDBOX_BREACH', 'UNAUTHORIZED', or similar errors
    """
    prompt = "Reply with the single word: ACK"
    rc, stdout, stderr = invoke_claude_agent(agent_name, prompt, timeout_s=120)

    assert rc == 0, f"agent {agent_name} exited {rc}; stderr={stderr[:500]!r}"
    assert len(stdout.strip()) > 0, f"agent {agent_name} returned empty stdout"
    forbidden = ["SANDBOX_BREACH", "UNAUTHORIZED"]
    for bad in forbidden:
        assert bad not in stdout, f"agent {agent_name} produced forbidden output: {bad}"
