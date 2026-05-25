"""redact.py — strip secrets from text and JSON structures.

CLI usage:
    cat raw.txt | python redact.py > clean.txt

Library usage:
    from redact import redact_text, redact_dict
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.redact_patterns import PATTERNS


def redact_text(text: str) -> str:
    """Replace each matched secret with `[REDACTED <kind>]`."""
    out = text
    for kind, pattern in PATTERNS:
        out = pattern.sub(f"[REDACTED {kind}]", out)
    return out


def redact_dict(data: Any) -> Any:
    """Recursively redact strings inside a JSON-like structure."""
    if isinstance(data, str):
        return redact_text(data)
    if isinstance(data, dict):
        return {k: redact_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data


def main() -> int:
    raw = sys.stdin.read()
    sys.stdout.write(redact_text(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
