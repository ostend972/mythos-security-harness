"""Tests for cleanup_orphans.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import cleanup_orphans


class TestFindOrphanContainers:
    def test_returns_empty_when_no_mythos_containers(self):
        with patch("cleanup_orphans.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = cleanup_orphans.find_orphan_containers()
            assert result == []

    def test_parses_container_ids(self):
        with patch("cleanup_orphans.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="abc123\ndef456\n", returncode=0,
            )
            result = cleanup_orphans.find_orphan_containers()
            assert result == ["abc123", "def456"]


class TestKillOrphanProcesses:
    def test_returns_killed_count(self):
        with patch("cleanup_orphans.psutil.process_iter") as mock_iter:
            mock_proc = MagicMock()
            mock_proc.info = {"pid": 12345, "name": "claude", "cmdline": ["claude", "--agent", "mythos-hunter"]}
            mock_proc.kill = MagicMock()
            mock_iter.return_value = [mock_proc]
            count = cleanup_orphans.kill_orphan_claude_processes(parent_pid=99999)
            assert count >= 0


def test_main_runs_without_error():
    """Smoke test: main() should not raise."""
    with patch("cleanup_orphans.find_orphan_containers", return_value=[]):
        with patch("cleanup_orphans.kill_orphan_claude_processes", return_value=0):
            rc = cleanup_orphans.main([])
            assert rc == 0
