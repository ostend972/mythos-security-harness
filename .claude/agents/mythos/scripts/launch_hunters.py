"""launch_hunters.py — script that spawns N `claude --agent mythos-hunter` processes
in parallel from the task queue.

Each hunter receives its task JSON + the architecture context as user input,
runs in detached mode, writes its findings/coverage to .mythos/ via locks, and
exits. This script waits for all hunters in the batch and reports outcomes.

Reference: spec §5.1.2 (mythos-hunt-lead orchestration), §11 T15 (rate limit backoff).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.locking import AtomicJsonlAppender


def read_pending_tasks(queue_path: Path, limit: int) -> list[dict]:
    """Read up to `limit` tasks with status='pending' from the JSONL queue."""
    if not queue_path.is_file():
        return []
    tasks = []
    for raw in queue_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            t = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if t.get("status") == "pending":
            tasks.append(t)
            if len(tasks) >= limit:
                break
    return tasks


def mark_tasks_status(queue_path: Path, task_ids: list[str], status: str) -> None:
    """Rewrite the queue file with given tasks' status updated."""
    if not queue_path.is_file():
        return
    ids = set(task_ids)
    new_lines = []
    for raw in queue_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            t = json.loads(raw)
        except json.JSONDecodeError:
            new_lines.append(raw)
            continue
        if t.get("task_id") in ids:
            t["status"] = status
        new_lines.append(json.dumps(t))
    tmp = queue_path.with_suffix(queue_path.suffix + ".tmp")
    tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.replace(tmp, queue_path)


def build_hunter_prompt(task: dict, architecture_md: str) -> str:
    """Build the -p prompt for a single hunter invocation."""
    return (
        "You are starting Mythos hunt task.\n\n"
        f"Task: {json.dumps(task, indent=2)}\n\n"
        "Architecture context:\n"
        f"{architecture_md}\n"
    )


def spawn_one_hunter(task: dict, prompt: str, work_dir: Path) -> dict:
    """Spawn `claude --agent mythos-hunter -p <prompt>` and wait. Return outcome dict."""
    task_id = task.get("task_id", "T-unknown")
    start = time.monotonic()
    try:
        p = subprocess.run(
            ["claude", "--agent", "mythos-hunter", "-p", prompt],
            cwd=work_dir, capture_output=True, text=True, timeout=600,
        )
        return {
            "task_id": task_id,
            "exit_code": p.returncode,
            "duration_s": time.monotonic() - start,
            "stdout_tail": p.stdout[-2000:],
            "stderr_tail": p.stderr[-2000:],
            "status": "completed" if p.returncode == 0 else "failed",
        }
    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id, "exit_code": -1,
            "duration_s": time.monotonic() - start,
            "status": "timeout",
        }
    except FileNotFoundError:
        return {
            "task_id": task_id, "exit_code": -1,
            "duration_s": time.monotonic() - start,
            "status": "failed", "stderr_tail": "claude CLI not on PATH",
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="launch_hunters")
    p.add_argument("--queue", default=".mythos/task-queue.jsonl")
    p.add_argument("--architecture", default=".mythos/architecture.md")
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    queue_path = Path(args.queue)
    arch_path = Path(args.architecture)

    if not queue_path.is_file():
        print(f"queue not found: {queue_path}", file=sys.stderr)
        return 2

    arch_md = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else ""
    tasks = read_pending_tasks(queue_path, args.batch_size)
    if not tasks:
        print("no pending tasks — nothing to dispatch")
        return 0

    print(f"dispatching {len(tasks)} hunters (batch_size={args.batch_size})")
    if args.dry_run:
        for t in tasks:
            print(f"  would spawn: task={t.get('task_id')} class={t.get('class')}")
        return 0

    mark_tasks_status(queue_path, [t["task_id"] for t in tasks], "in_progress")

    work_dir = Path.cwd()
    outcomes = []
    with ThreadPoolExecutor(max_workers=args.batch_size) as pool:
        future_to_task = {
            pool.submit(spawn_one_hunter, t, build_hunter_prompt(t, arch_md), work_dir): t
            for t in tasks
        }
        for fut in as_completed(future_to_task):
            outcomes.append(fut.result())

    # Update task statuses based on outcomes
    completed = [o["task_id"] for o in outcomes if o.get("status") == "completed"]
    failed = [o["task_id"] for o in outcomes if o.get("status") in ("failed", "timeout")]
    mark_tasks_status(queue_path, completed, "completed")
    mark_tasks_status(queue_path, failed, "failed")

    print(f"batch done: {len(completed)} completed, {len(failed)} failed/timeout")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
