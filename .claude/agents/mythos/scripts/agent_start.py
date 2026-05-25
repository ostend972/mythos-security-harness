"""agent_start.py — SubagentStart hook for Mythos agents.

Logs every Mythos sub-agent invocation to .mythos/audit.jsonl with timestamp,
agent type, and any provided task context. Non-Mythos agents pass through
silently.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §13.3 audit log.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import read_hook_input, emit_allow
from common.paths import project_root, ProjectRootNotFound, mythos_dir, ensure_dirs
from common.locking import AtomicJsonlAppender


def main() -> int:
    payload = read_hook_input()
    agent_type = payload.get("agent_type") or ""
    if not agent_type.startswith("mythos-"):
        return emit_allow()

    try:
        project_root()  # ensure we're in a Mythos repo
    except ProjectRootNotFound:
        return emit_allow()

    audit_dir = mythos_dir()
    ensure_dirs(audit_dir)
    audit_path = audit_dir / "audit.jsonl"

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "event": "agent_start",
        "agent_type": agent_type,
        "session_id": payload.get("session_id"),
    }
    try:
        AtomicJsonlAppender(audit_path, timeout_s=5.0).append(record)
    except Exception as e:
        # Never break the agent start — log only.
        print(f"[mythos agent_start] failed to write audit log: {e}", file=sys.stderr)

    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
