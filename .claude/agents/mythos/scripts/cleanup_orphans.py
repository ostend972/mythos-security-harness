"""cleanup_orphans.py — kill orphaned Mythos containers + claude processes.

Triggered:
- Manually: python cleanup_orphans.py
- As Stop hook: settings.json hooks.Stop entry
- Periodically: optional cron entry

Looks for:
- Docker containers whose name starts with 'mythos-' (no live parent attached)
- Python `claude --agent` processes whose parent is no longer the Mythos session
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Iterable

import psutil

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def find_orphan_containers() -> list[str]:
    """Return Docker container IDs whose name starts with 'mythos-'.

    Docker isn't required to be on PATH — if it isn't, return empty.
    """
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=mythos-", "--format", "{{.ID}}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def kill_containers(ids: Iterable[str]) -> int:
    """Force-remove containers. Return count actually removed."""
    removed = 0
    for cid in ids:
        try:
            r = subprocess.run(
                ["docker", "rm", "-f", cid], capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                removed += 1
        except (OSError, subprocess.TimeoutExpired):
            continue
    return removed


def kill_orphan_claude_processes(parent_pid: int) -> int:
    """Kill `claude --agent mythos-*` processes whose ppid is no longer `parent_pid`."""
    killed = 0
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            cmdline = info.get("cmdline") or []
            if "claude" not in name.lower() and not any("claude" in str(a).lower() for a in cmdline):
                continue
            cmd_str = " ".join(str(a) for a in cmdline)
            if "mythos-" not in cmd_str:
                continue
            if info.get("ppid") == parent_pid:
                continue
            proc.kill()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="cleanup_orphans")
    p.add_argument("--parent-pid", type=int, default=os.getppid(),
                   help="Only orphans whose ppid != this are killed (default: ppid of this process)")
    p.add_argument("--dry-run", action="store_true", help="Report what would be done")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    containers = find_orphan_containers()
    if args.dry_run:
        print(f"would remove {len(containers)} container(s): {containers}")
    else:
        removed = kill_containers(containers)
        print(f"removed {removed}/{len(containers)} containers")

    if args.dry_run:
        print(f"would scan for orphan claude processes (parent_pid={args.parent_pid})")
    else:
        killed = kill_orphan_claude_processes(parent_pid=args.parent_pid)
        print(f"killed {killed} orphan claude processes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
