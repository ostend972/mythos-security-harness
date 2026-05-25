"""Shared helpers for Claude Code hook scripts.

Claude Code passes hook input as JSON on stdin and reads JSON output from
stdout. Hooks exit with:
- 0: allow (default)
- 1: warn (printed to user but tool continues)
- 2: block (tool call rejected)

Schema reference: https://code.claude.com/docs/fr/hooks
"""
from __future__ import annotations

import json
import sys
from typing import Any


def read_hook_input() -> dict[str, Any]:
    """Read JSON from stdin. Return empty dict if stdin is empty/malformed."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_block(reason: str) -> int:
    """Print a blocking reason to stderr and return exit code 2."""
    print(reason, file=sys.stderr)
    return 2


def emit_warn(reason: str) -> int:
    """Print a warning to stderr and return exit code 1."""
    print(reason, file=sys.stderr)
    return 1


def emit_allow() -> int:
    """Allow the tool call. Return exit code 0."""
    return 0


def get_tool_input(hook_input: dict[str, Any]) -> dict[str, Any]:
    """Extract tool_input dict from the hook payload, defensive against missing keys."""
    return hook_input.get("tool_input") or {}


def get_tool_name(hook_input: dict[str, Any]) -> str:
    """Extract the tool name (e.g., 'Bash', 'Write')."""
    return hook_input.get("tool_name") or ""
