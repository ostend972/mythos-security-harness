"""sanitize_output.py — strip ANSI escape sequences and control characters.

CLI usage:
    cat noisy.log | python sanitize_output.py > clean.log

Library usage:
    from sanitize_output import sanitize
    clean = sanitize(raw, max_bytes=1_000_000)
"""
from __future__ import annotations

import re
import sys

# Strip CSI/OSC ANSI sequences (color, cursor, OSC).
ANSI_PATTERN = re.compile(r"\x1b(?:\[[0-9;]*[A-Za-z]|\][^\x07\x1b]*(?:\x07|\x1b\\))")

# Strip C0 control chars except \n (0x0a) and \t (0x09).
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

DEFAULT_MAX_BYTES = 1_000_000


def sanitize(text: str, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    """Strip ANSI + control chars and truncate to max_bytes."""
    out = ANSI_PATTERN.sub("", text)
    out = CONTROL_PATTERN.sub("", out)
    if len(out) > max_bytes:
        out = out[:max_bytes]
    return out


def main() -> int:
    raw = sys.stdin.read()
    sys.stdout.write(sanitize(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
