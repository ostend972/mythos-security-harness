"""validate_bash.py — PreToolUse hook for Bash commands.

Blocks catastrophic / out-of-scope commands by inspecting the command string.
Reads hook JSON from stdin per Claude Code hook protocol; exits with code 2
to block, 0 to allow.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §11 (Threat T13)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import (
    read_hook_input, emit_block, emit_allow, get_tool_input, get_tool_name,
)


# Each entry: (compiled_pattern, human-readable reason)
# Patterns are matched case-insensitively against the full command.
DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+-[rR]?[fF]\s+/(\s|$|\*)"), "rm -rf / (catastrophic)"),
    (re.compile(r"\brm\s+-[rR]?[fF]\s+(~|\$HOME)(\s|$|/)"), "rm -rf ~/ (catastrophic)"),
    (re.compile(r"\brm\s+-[rR]?[fF]\s+/etc"), "rm -rf /etc (catastrophic)"),
    (re.compile(r"\bchmod\s+777\s+/"), "chmod 777 on absolute root paths"),
    (re.compile(r"\bchown\s+root\b"), "chown to root"),
    (re.compile(r"\bsudo\b"), "sudo (out of scope for Mythos)"),
    (re.compile(r"(^|\s)su\s+(-|root)"), "su to root"),
    (re.compile(r"\bsetcap\b"), "setcap (out of scope)"),
    (re.compile(r"docker\s+run\s+[^#\n]*--privileged"), "docker --privileged (sandbox bypass)"),
    (re.compile(r"docker[^#\n]*docker\.sock"), "mounting docker.sock (sandbox bypass)"),
    (re.compile(r"\bcat\s+/etc/shadow"), "reading /etc/shadow"),
    (re.compile(r"\bcat\s+/etc/sudoers"), "reading /etc/sudoers"),
    (re.compile(r"(~|\$HOME)/\.ssh\b"), "accessing ~/.ssh"),
    (re.compile(r"(~|\$HOME)/\.aws\b"), "accessing ~/.aws"),
    (re.compile(r"(~|\$HOME)/\.config/gcloud\b"), "accessing ~/.config/gcloud"),
    (re.compile(r"(~|\$HOME)/\.kube\b"), "accessing ~/.kube"),
    (re.compile(r"(~|\$HOME)/\.docker\b"), "accessing ~/.docker"),
    (re.compile(r"\bssh-add\b"), "ssh-add (key import out of scope)"),
]


def check(command: str) -> tuple[bool, str | None]:
    """Return (allowed, reason). allowed=False means block."""
    cmd = command.strip()
    if not cmd:
        return True, None
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(cmd):
            return False, reason
    return True, None


def main() -> int:
    payload = read_hook_input()
    if get_tool_name(payload) != "Bash":
        return emit_allow()
    cmd = get_tool_input(payload).get("command", "")
    allowed, reason = check(cmd)
    if not allowed:
        return emit_block(
            f"[mythos validate_bash] Blocked dangerous command: {reason}\n"
            f"  Command: {cmd[:200]}"
        )
    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
