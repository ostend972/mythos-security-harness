"""disclaimer.py — dual-use acknowledgment check.

On first run, the operator must explicitly accept that Mythos generates
weaponized exploit code. Subsequent runs check for the acknowledgment file.

Reference: spec §15 dual-use disclaimer.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


DISCLAIMER_TEXT = """\
=== Mythos Preview — Dual-Use Acknowledgment ===

Mythos Preview produces FUNCTIONAL, WEAPONIZED exploit code.

Use is permitted ONLY on:
  1. Code you own
  2. Code in scope of a bug bounty program that explicitly authorizes testing
  3. Code under a signed penetration testing engagement
  4. Code used in authorized security research

Use against third-party code without authorization is illegal in most
jurisdictions and may constitute computer fraud or unauthorized access.

By proceeding, you affirm that the target you are about to scan falls
into one of the categories above.

To acknowledge, create the file:
    .claude/agents/mythos/.acknowledged
with the single line: ACKNOWLEDGED <YYYY-MM-DD>

Or run:
    python .claude/agents/mythos/scripts/disclaimer.py --accept
"""


def acknowledgment_path() -> Path:
    return Path(".claude/agents/mythos/.acknowledged")


def is_acknowledged() -> bool:
    p = acknowledgment_path()
    if not p.is_file():
        return False
    content = p.read_text(encoding="utf-8").strip()
    return content.startswith("ACKNOWLEDGED")


def accept() -> None:
    p = acknowledgment_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    p.write_text(f"ACKNOWLEDGED {today}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="disclaimer")
    parser.add_argument("--accept", action="store_true",
                       help="Write the acknowledgment file")
    parser.add_argument("--check", action="store_true",
                       help="Exit 0 if acknowledged, 2 otherwise")
    args = parser.parse_args(argv)

    if args.accept:
        accept()
        print("Acknowledgment recorded.")
        return 0

    if args.check:
        return 0 if is_acknowledged() else 2

    if not is_acknowledged():
        print(DISCLAIMER_TEXT, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
