"""validate_write.py — PostToolUse hook for Write/Edit operations.

Two enforcement layers:
1. Path traversal: blocks writes that resolve outside the project root.
2. Allow-list pattern: if --allow-pattern is given, only writes whose
   file_path matches the regex are allowed.
3. Secret leakage: blocks/warns if the written content contains common
   secret patterns.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §11 T4, T6.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import (
    read_hook_input, emit_block, emit_warn, emit_allow,
    get_tool_input, get_tool_name,
)
from common.paths import project_root, ProjectRootNotFound, UnsafePathError, assert_safe_write
from common.redact_patterns import find_secrets


WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="validate_write")
    p.add_argument(
        "--allow-pattern",
        action="append",
        default=[],
        help="Regex that file_path must match (can be given multiple times; OR'd)",
    )
    return p.parse_args(argv)


def check_path_traversal(file_path: str) -> tuple[bool, str | None]:
    """Return (ok, error). file_path must stay inside project_root."""
    try:
        root = project_root()
    except ProjectRootNotFound:
        # Outside any Mythos project — pass through (hook is a no-op).
        return True, None
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    try:
        assert_safe_write(target, base=root)
        return True, None
    except UnsafePathError as e:
        return False, str(e)


def check_allow_patterns(file_path: str, patterns: list[str]) -> tuple[bool, str | None]:
    if not patterns:
        return True, None
    for raw in patterns:
        if re.search(raw, file_path):
            return True, None
    return False, (
        f"path '{file_path}' did not match any allow pattern "
        f"({len(patterns)} pattern(s) tried)"
    )


def check_secrets(content: str) -> tuple[bool, str | None]:
    hits = find_secrets(content or "")
    if not hits:
        return True, None
    summary = ", ".join({kind for kind, _ in hits})
    return False, f"detected secret patterns in content: {summary}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = read_hook_input()
    tool = get_tool_name(payload)
    if tool not in WRITE_TOOLS:
        return emit_allow()

    tool_input = get_tool_input(payload)
    file_path = tool_input.get("file_path") or ""
    content = tool_input.get("content") or tool_input.get("new_string") or ""

    ok, reason = check_path_traversal(file_path)
    if not ok:
        return emit_block(f"[mythos validate_write] path traversal blocked: {reason}")

    ok, reason = check_allow_patterns(file_path, args.allow_pattern)
    if not ok:
        return emit_block(f"[mythos validate_write] {reason}")

    ok, reason = check_secrets(content)
    if not ok:
        # Warn instead of hard-block so hunters who legitimately include
        # high-entropy strings in PoC payloads can still proceed.
        return emit_warn(f"[mythos validate_write] {reason}")

    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
