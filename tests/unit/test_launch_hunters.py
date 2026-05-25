"""Tests for launch_hunters.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import launch_hunters


@pytest.fixture
def task_queue(tmp_path):
    """Create a fake task-queue.jsonl with 5 pending tasks."""
    q = tmp_path / "task-queue.jsonl"
    lines = []
    for i in range(5):
        lines.append(json.dumps({
            "task_id": f"T-T{i:03d}",
            "class": "sql-injection",
            "scope": f"src/x.py:func{i}",
            "subsystem": "api",
            "trust_boundary": "HTTP",
            "priority": 1,
            "status": "pending",
        }))
    q.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return q


def test_read_pending_tasks_returns_pending_only(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=10)
    assert len(tasks) == 5
    assert all(t["status"] == "pending" for t in tasks)


def test_read_pending_tasks_honors_limit(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=3)
    assert len(tasks) == 3


def test_build_hunter_prompt_includes_task_json():
    task = {"task_id": "T-T001", "class": "sql-injection", "scope": "src/x.py:foo",
            "subsystem": "api", "trust_boundary": "HTTP", "priority": 1, "status": "pending"}
    prompt = launch_hunters.build_hunter_prompt(task, architecture_md="ARCH HERE")
    assert "T-T001" in prompt
    assert "sql-injection" in prompt
    assert "ARCH HERE" in prompt


def test_mark_tasks_in_progress(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=2)
    launch_hunters.mark_tasks_status(task_queue, [t["task_id"] for t in tasks], "in_progress")
    new_tasks = launch_hunters.read_pending_tasks(task_queue, limit=10)
    assert len(new_tasks) == 3  # 5 - 2 that we just claimed


def test_dispatch_dry_run_does_not_invoke_subprocess(tmp_path, task_queue):
    with patch("launch_hunters.subprocess.run") as mock_popen:
        rc = launch_hunters.main([
            "--queue", str(task_queue),
            "--architecture", str(tmp_path / "arch.md"),
            "--batch-size", "2",
            "--dry-run",
        ])
        assert rc == 0
        mock_popen.assert_not_called()
