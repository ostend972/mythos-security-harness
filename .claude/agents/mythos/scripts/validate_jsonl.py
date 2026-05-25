"""validate_jsonl.py — CLI to validate a JSONL file against a Mythos schema.

Usage:
    python validate_jsonl.py <path> --schema <schema_name> [--quiet]

Exit codes:
    0 — all records valid
    1 — at least one record invalid
    2 — usage error (unknown schema, missing file, etc.)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `common` importable when run as a script
HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.schema import StrictValidator, SchemaNotFoundError, SchemaValidationError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="validate_jsonl")
    p.add_argument("path", help="Path to the JSONL file to validate")
    p.add_argument("--schema", required=True, help="Schema name (e.g., 'finding', 'task')")
    p.add_argument("--quiet", action="store_true", help="Suppress per-line output")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = Path(args.path)
    if not path.is_file():
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 2

    try:
        validator = StrictValidator(args.schema)
    except SchemaNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    total = 0
    invalid = 0
    for lineno, record, err in validator.validate_jsonl_stream(path):
        total += 1
        if err is None:
            if not args.quiet:
                print(f"  line {lineno}: ok")
        else:
            invalid += 1
            if not args.quiet:
                print(f"  line {lineno}: INVALID — {err}", file=sys.stderr)

    print(f"=== {path.name}: {total - invalid}/{total} valid against schema '{args.schema}'")
    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
