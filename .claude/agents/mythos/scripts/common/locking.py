"""Cross-platform thread/process-safe JSONL appender.

Uses `filelock` (validated by context7, benchmark 98/100) which wraps:
- LockFileEx on Windows
- fcntl on Linux/Mac

Pattern: every append acquires an OS-level lock on `<path>.lock`, writes one
line + newline + flush, then releases. Survives process crashes (lock is
released by the OS).
"""
from __future__ import annotations

import json
from pathlib import Path
from filelock import FileLock, Timeout


class LockTimeoutError(RuntimeError):
    """Raised when the JSONL append could not acquire the file lock within timeout."""


class AtomicJsonlAppender:
    """Append-only writer for JSONL files, safe across threads and processes.

    Example:
        appender = AtomicJsonlAppender(Path(".mythos/findings.jsonl"), timeout_s=30)
        appender.append({"finding_id": "F-001", ...})
    """

    def __init__(self, path: Path, timeout_s: float = 30.0):
        self.path = path
        self.timeout_s = timeout_s
        self._lock_path = path.with_suffix(path.suffix + ".lock")
        # Ensure parent dir exists so the lock file can be created
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        """Append `record` as a single JSON line to the target file.

        Raises LockTimeoutError if the lock is unavailable within `timeout_s`.
        """
        line = json.dumps(record, ensure_ascii=False, sort_keys=False)
        lock = FileLock(str(self._lock_path), timeout=self.timeout_s)
        try:
            with lock:
                with self.path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(line + "\n")
                    f.flush()
        except Timeout as e:
            raise LockTimeoutError(
                f"Could not acquire lock on {self._lock_path} within {self.timeout_s}s"
            ) from e
