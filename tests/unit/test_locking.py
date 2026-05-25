"""Tests for cross-platform file locking."""
import json
import sys
import threading
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.locking import AtomicJsonlAppender, LockTimeoutError


class TestAtomicJsonlAppender:
    def test_appends_single_record(self, tmp_path):
        target = tmp_path / "findings.jsonl"
        appender = AtomicJsonlAppender(target, timeout_s=5.0)
        appender.append({"id": "F-001"})
        lines = target.read_text(encoding="utf-8").strip().split("\n")
        assert lines == ['{"id": "F-001"}']

    def test_appends_multiple_records_sequentially(self, tmp_path):
        target = tmp_path / "findings.jsonl"
        appender = AtomicJsonlAppender(target, timeout_s=5.0)
        for i in range(5):
            appender.append({"id": f"F-{i:03d}"})
        lines = target.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5
        assert all(json.loads(line)["id"] == f"F-{i:03d}" for i, line in enumerate(lines))

    def test_concurrent_appends_are_serialized(self, tmp_path):
        """Multiple threads appending simultaneously must produce well-formed lines."""
        target = tmp_path / "findings.jsonl"
        appender = AtomicJsonlAppender(target, timeout_s=10.0)
        n_threads = 20
        records_per_thread = 5

        def worker(thread_id: int):
            for i in range(records_per_thread):
                appender.append({"thread": thread_id, "i": i})

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify every line is valid JSON and we have the right count
        lines = target.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == n_threads * records_per_thread
        for line in lines:
            parsed = json.loads(line)
            assert "thread" in parsed and "i" in parsed

    def test_timeout_raises_lock_timeout(self, tmp_path):
        """If a lock is held forever, append() must raise LockTimeoutError."""
        from filelock import FileLock

        target = tmp_path / "findings.jsonl"
        lock_path = target.with_suffix(target.suffix + ".lock")
        # Acquire the lock externally and hold it
        external = FileLock(str(lock_path), timeout=-1)
        external.acquire()
        try:
            appender = AtomicJsonlAppender(target, timeout_s=0.5)
            with pytest.raises(LockTimeoutError):
                appender.append({"id": "F-blocked"})
        finally:
            external.release()
