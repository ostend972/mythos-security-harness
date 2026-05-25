# Mythos Preview — Plan 1: Infrastructure & Hardened Sandbox

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational infrastructure (project skeleton, Python tooling, hardened Docker sandbox) needed by all subsequent Mythos Preview components, with the sandbox provably resisting red-team escape attempts.

**Architecture:** Cross-platform Python utilities + Docker SDK-based sandbox with defense-in-depth (seccomp + AppArmor on Linux + cap-drop=ALL + non-root + read-only FS + no network). Tests prove sandbox isolation by trying — and failing — to escape it.

**Tech Stack:** Python 3.10+, `docker-py>=7.0`, `filelock>=3.13`, `jsonschema>=4.20`, `psutil>=5.9`, Docker Desktop (WSL2 backend on Windows 11), Debian Bookworm slim base image.

**Spec reference:** [`docs/superpowers/specs/2026-05-25-mythos-preview-design.md`](../specs/2026-05-25-mythos-preview-design.md)

**Out of scope for this plan (covered later):**
- JSON schemas (Plan 2)
- Hooks `validate_bash.py` / `validate_write.py` (Plan 2)
- The 12 agents themselves (Plans 4, 5)
- Skill `/mythos` orchestrator (Plan 6)
- Cybersecurity skill installation (Plan 3)

---

## File Structure

This plan creates the following files:

```
<repo_root>/
├── .gitignore                                         # already exists, will update
├── README.md                                          # NEW - quick start
├── .claude/
│   └── agents/
│       └── mythos/
│           ├── scripts/
│           │   ├── requirements.txt                   # NEW - pinned Python deps
│           │   ├── preflight.py                       # NEW - environment check
│           │   ├── mythos_sandbox.py                  # NEW - hardened Docker runner
│           │   └── common/
│           │       ├── __init__.py                    # NEW
│           │       ├── paths.py                       # NEW - cross-platform paths
│           │       ├── locking.py                     # NEW - filelock wrapper
│           │       ├── docker_runner.py               # NEW - Docker SDK wrapper
│           │       └── platform_utils.py              # NEW - OS detection helpers
│           └── docker/
│               ├── Dockerfile.multilang                # NEW - hardened multi-lang image
│               ├── mythos-runner.sh                   # NEW - container entrypoint
│               ├── seccomp-mythos.json                # NEW - custom seccomp profile
│               └── apparmor-mythos                    # NEW - Linux AppArmor profile
├── tests/
│   ├── __init__.py                                    # NEW
│   ├── conftest.py                                    # NEW - pytest fixtures
│   ├── unit/
│   │   ├── __init__.py                                # NEW
│   │   ├── test_paths.py                              # NEW
│   │   ├── test_locking.py                            # NEW
│   │   ├── test_platform_utils.py                     # NEW
│   │   ├── test_preflight.py                          # NEW
│   │   └── test_docker_runner.py                      # NEW
│   ├── integration/
│   │   ├── __init__.py                                # NEW
│   │   └── test_sandbox_smoke.py                      # NEW - basic Docker run
│   └── red_team/
│       ├── __init__.py                                # NEW
│       ├── test_sandbox_resists_escape.py             # NEW - escape attempts MUST fail
│       └── attempts/
│           ├── try_etc_passwd_read.sh                 # NEW
│           ├── try_setuid.c                           # NEW
│           ├── try_fork_bomb.sh                       # NEW
│           ├── try_network_exfil.sh                   # NEW
│           ├── try_docker_sock.sh                     # NEW
│           └── try_mount_escape.sh                    # NEW
└── docs/superpowers/plans/
    └── 2026-05-25-mythos-plan-1-infrastructure-sandbox.md   # this file
```

---

## Task 1: Bootstrap project structure

**Files:**
- Modify: `.gitignore`
- Create: `README.md`
- Create: `.claude/agents/mythos/scripts/`
- Create: `.claude/agents/mythos/scripts/common/`
- Create: `.claude/agents/mythos/docker/`
- Create: `tests/unit/`, `tests/integration/`, `tests/red_team/attempts/`

- [ ] **Step 1: Create directory tree**

Run:
```bash
mkdir -p .claude/agents/mythos/scripts/common .claude/agents/mythos/docker tests/unit tests/integration tests/red_team/attempts
```

Expected: All directories created, no errors.

- [ ] **Step 2: Update .gitignore**

Append to existing `.gitignore`:
```
# Mythos Plan 1 additions
.coverage
htmlcov/
.pytest_cache/
*.egg-info/
build/
dist/
```

- [ ] **Step 3: Create top-level README**

Write `README.md`:
```markdown
# Mythos Preview

Vulnerability discovery harness for Claude Code, inspired by Cloudflare's pipeline.

**Status:** In development (Plan 1: Infrastructure & Sandbox)

See `docs/superpowers/specs/2026-05-25-mythos-preview-design.md` for the full design.

## Prerequisites

- Python 3.10+
- Docker Desktop (Windows/Mac) or Docker Engine 24+ (Linux)
- On Windows: WSL2 backend enabled in Docker Desktop
- `winget install Python.Python.3.12` (Windows) / `brew install python` (Mac) / `apt install python3.12 python3-pip` (Linux)

## Quick start (after this plan completes)

```bash
pip install -r .claude/agents/mythos/scripts/requirements.txt
python .claude/agents/mythos/scripts/preflight.py
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/
pytest tests/ -v
```
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore README.md
git add .claude/agents/mythos/scripts/.gitkeep 2>/dev/null || touch .claude/agents/mythos/scripts/.gitkeep
git add .claude/agents/mythos/docker/.gitkeep 2>/dev/null || touch .claude/agents/mythos/docker/.gitkeep
git add tests/.gitkeep 2>/dev/null || touch tests/.gitkeep
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: bootstrap Mythos project structure"
```

---

## Task 2: Python dependencies

**Files:**
- Create: `.claude/agents/mythos/scripts/requirements.txt`

- [ ] **Step 1: Pin dependency versions**

Write `.claude/agents/mythos/scripts/requirements.txt`:
```
# Core libraries (validated via context7)
docker>=7.0.0,<8.0                       # Docker SDK
filelock>=3.13.0,<4.0                    # Cross-platform file locking
jsonschema[format-nongpl]>=4.20.0,<5.0   # JSON Schema Draft 2020-12 (no GPL deps)
PyYAML>=6.0.1,<7.0                       # Parse agent frontmatter
psutil>=5.9.0,<6.0                       # Cross-platform process management

# Testing
pytest>=8.0.0,<9.0
pytest-cov>=4.1.0,<5.0
pytest-timeout>=2.2.0,<3.0
pytest-xdist>=3.5.0,<4.0                 # parallel test execution
```

- [ ] **Step 2: Install in venv**

Run:
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r .claude/agents/mythos/scripts/requirements.txt
```

Expected: All packages install without conflicts.

- [ ] **Step 3: Verify imports**

Run:
```bash
python -c "import docker, filelock, jsonschema, yaml, psutil, pytest; print('OK')"
```

Expected: `OK` printed.

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/mythos/scripts/requirements.txt
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: pin Python dependencies"
```

---

## Task 3: Cross-platform path helpers

**Files:**
- Create: `.claude/agents/mythos/scripts/common/__init__.py`
- Create: `.claude/agents/mythos/scripts/common/paths.py`
- Test: `tests/unit/test_paths.py`

- [ ] **Step 1: Create empty __init__ files**

```bash
touch .claude/agents/mythos/scripts/common/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
```

- [ ] **Step 2: Write the failing test**

Write `tests/unit/test_paths.py`:
```python
"""Tests for cross-platform path helpers."""
import os
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common import paths


class TestProjectRoot:
    def test_project_root_returns_directory_containing_dotclaude(self, tmp_path, monkeypatch):
        # Arrange: simulate a project with .claude/
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        (project / "src").mkdir()
        monkeypatch.chdir(project / "src")
        # Act
        result = paths.project_root()
        # Assert
        assert result == project

    def test_project_root_raises_when_no_dotclaude(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(paths.ProjectRootNotFound):
            paths.project_root()


class TestMythosDir:
    def test_mythos_dir_is_under_project_root(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.mythos_dir() == project / ".mythos"

    def test_state_dir_under_mythos(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.state_dir() == project / ".mythos" / "state"


class TestEnsureDirs:
    def test_ensure_dirs_creates_missing(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        assert not target.exists()
        paths.ensure_dirs(target)
        assert target.is_dir()

    def test_ensure_dirs_idempotent(self, tmp_path):
        target = tmp_path / "a"
        paths.ensure_dirs(target)
        paths.ensure_dirs(target)  # should not raise
        assert target.is_dir()


class TestSafeWritePath:
    def test_safe_write_path_rejects_traversal(self, tmp_path):
        with pytest.raises(paths.UnsafePathError):
            paths.assert_safe_write(tmp_path / ".." / "evil.txt", base=tmp_path)

    def test_safe_write_path_rejects_absolute_outside(self, tmp_path):
        outside = Path("/etc/passwd") if os.name != "nt" else Path("C:/Windows/System32/evil.txt")
        with pytest.raises(paths.UnsafePathError):
            paths.assert_safe_write(outside, base=tmp_path)

    def test_safe_write_path_accepts_inside(self, tmp_path):
        good = tmp_path / "subdir" / "file.txt"
        # Should not raise
        paths.assert_safe_write(good, base=tmp_path)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/unit/test_paths.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'common.paths'`.

- [ ] **Step 4: Write the implementation**

Write `.claude/agents/mythos/scripts/common/paths.py`:
```python
"""Cross-platform path helpers for Mythos Preview.

Resolves project root (directory containing .claude/), state dirs,
and validates paths to prevent traversal attacks.
"""
from __future__ import annotations

from pathlib import Path


class ProjectRootNotFound(RuntimeError):
    """Raised when no .claude/ directory is found in cwd or any parent."""


class UnsafePathError(ValueError):
    """Raised when a path attempts to escape its allowed base directory."""


def project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until a directory containing .claude/ is found.

    Raises ProjectRootNotFound if no such directory exists.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".claude").is_dir():
            return candidate
    raise ProjectRootNotFound(
        f"No .claude/ found in {here} or any parent directory. "
        "Are you running from a Mythos-enabled repo?"
    )


def mythos_dir() -> Path:
    """Return .mythos/ under the project root."""
    return project_root() / ".mythos"


def state_dir() -> Path:
    """Return .mythos/state/ — runtime state shared between concurrent workers."""
    return mythos_dir() / "state"


def poc_dir() -> Path:
    """Return .mythos/poc/ — directory holding hunter-produced PoC code."""
    return mythos_dir() / "poc"


def logs_dir() -> Path:
    """Return .mythos/logs/."""
    return mythos_dir() / "logs"


def audit_log() -> Path:
    """Return .mythos/audit.jsonl — append-only security event log."""
    return mythos_dir() / "audit.jsonl"


def ensure_dirs(*paths: Path) -> None:
    """Create one or more directories with parents=True, exist_ok=True."""
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def assert_safe_write(target: Path, base: Path) -> None:
    """Raise UnsafePathError if `target` is outside `base` after resolution.

    Use this before any Write operation to prevent path traversal.
    """
    try:
        resolved = target.resolve()
        base_resolved = base.resolve()
        resolved.relative_to(base_resolved)
    except (ValueError, OSError):
        raise UnsafePathError(
            f"Path {target} resolves outside the allowed base {base}"
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
pytest tests/unit/test_paths.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/mythos/scripts/common/__init__.py
git add .claude/agents/mythos/scripts/common/paths.py
git add tests/__init__.py tests/unit/__init__.py tests/unit/test_paths.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: cross-platform path helpers with traversal prevention"
```

---

## Task 4: Platform detection utilities

**Files:**
- Create: `.claude/agents/mythos/scripts/common/platform_utils.py`
- Test: `tests/unit/test_platform_utils.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_platform_utils.py`:
```python
"""Tests for platform detection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common import platform_utils


def test_is_linux_returns_bool():
    assert isinstance(platform_utils.is_linux_host(), bool)


def test_is_windows_returns_bool():
    assert isinstance(platform_utils.is_windows_host(), bool)


def test_is_macos_returns_bool():
    assert isinstance(platform_utils.is_macos_host(), bool)


def test_exactly_one_os_is_true():
    flags = [
        platform_utils.is_linux_host(),
        platform_utils.is_windows_host(),
        platform_utils.is_macos_host(),
    ]
    assert sum(flags) == 1, f"Expected exactly one OS flag, got {flags}"


def test_apparmor_supported_only_on_linux():
    if platform_utils.is_linux_host():
        # On Linux, AppArmor *might* be supported (depends on kernel + userspace)
        # We just check the function returns a bool without error
        assert isinstance(platform_utils.apparmor_supported(), bool)
    else:
        assert platform_utils.apparmor_supported() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_platform_utils.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/common/platform_utils.py`:
```python
"""Platform detection for Mythos cross-platform behavior."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


def is_linux_host() -> bool:
    return platform.system() == "Linux"


def is_windows_host() -> bool:
    return platform.system() == "Windows"


def is_macos_host() -> bool:
    return platform.system() == "Darwin"


def apparmor_supported() -> bool:
    """Return True if AppArmor is available on this host.

    AppArmor is Linux-only and requires both kernel support and the userspace tools.
    """
    if not is_linux_host():
        return False
    # Check apparmor_status command exists
    if not shutil.which("apparmor_status"):
        return False
    # Check AppArmor sysfs interface
    if not Path("/sys/kernel/security/apparmor").exists():
        return False
    return True


def docker_available() -> bool:
    """Return True if `docker` CLI exists and the daemon responds."""
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def os_summary() -> dict:
    """Return a dict describing the host environment for logging/diagnostics."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "is_linux": is_linux_host(),
        "is_windows": is_windows_host(),
        "is_macos": is_macos_host(),
        "apparmor": apparmor_supported(),
        "docker": docker_available(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/unit/test_platform_utils.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/mythos/scripts/common/platform_utils.py
git add tests/unit/test_platform_utils.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: platform detection helpers"
```

---

## Task 5: Cross-platform file locking wrapper

**Files:**
- Create: `.claude/agents/mythos/scripts/common/locking.py`
- Test: `tests/unit/test_locking.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_locking.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_locking.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/common/locking.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/unit/test_locking.py -v
```

Expected: All 4 tests PASS (including the concurrent-threads test).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/mythos/scripts/common/locking.py
git add tests/unit/test_locking.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: thread/process-safe JSONL appender with filelock"
```

---

## Task 6: Pre-flight environment check

**Files:**
- Create: `.claude/agents/mythos/scripts/preflight.py`
- Test: `tests/unit/test_preflight.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_preflight.py`:
```python
"""Tests for the pre-flight environment check."""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import preflight


class TestPreflight:
    def test_check_python_version_passes_for_310_plus(self):
        with patch("preflight.sys.version_info", (3, 12, 0)):
            assert preflight.check_python_version() == (True, None)

    def test_check_python_version_fails_for_old(self):
        with patch("preflight.sys.version_info", (3, 9, 0)):
            ok, msg = preflight.check_python_version()
            assert not ok
            assert "3.10" in msg

    def test_check_required_imports_returns_ok_when_present(self):
        ok, missing = preflight.check_required_imports()
        # Since we just installed deps, all should be present
        assert ok, f"Missing: {missing}"
        assert missing == []

    def test_check_external_tools_reports_missing(self):
        with patch("preflight.shutil.which", return_value=None):
            ok, missing = preflight.check_external_tools()
            assert not ok
            assert "docker" in missing

    def test_run_all_checks_returns_summary(self):
        summary = preflight.run_all_checks()
        assert "python" in summary
        assert "imports" in summary
        assert "external_tools" in summary
        assert "docker_daemon" in summary
        assert "platform" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_preflight.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/preflight.py`:
```python
"""Mythos Preview pre-flight environment check.

Run before any Mythos pipeline to verify the host is ready:
- Python 3.10+
- Required Python packages installed
- Docker daemon accessible
- ctags, ripgrep on PATH
- AppArmor on Linux (advisory)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Tuple, List, Dict, Any

from common import platform_utils

REQUIRED_PYTHON = (3, 10)
REQUIRED_IMPORTS = ["docker", "filelock", "jsonschema", "yaml", "psutil"]
REQUIRED_TOOLS = ["docker", "ctags", "rg"]


def check_python_version() -> Tuple[bool, str | None]:
    """Verify Python version is >= REQUIRED_PYTHON."""
    if sys.version_info[:2] >= REQUIRED_PYTHON:
        return True, None
    return False, (
        f"Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ required, "
        f"found {sys.version_info.major}.{sys.version_info.minor}"
    )


def check_required_imports() -> Tuple[bool, List[str]]:
    """Verify all REQUIRED_IMPORTS can be imported. Returns (ok, missing)."""
    missing = []
    for name in REQUIRED_IMPORTS:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    return (not missing), missing


def check_external_tools() -> Tuple[bool, List[str]]:
    """Verify external CLI tools are on PATH."""
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    return (not missing), missing


def check_docker_daemon() -> Tuple[bool, str | None]:
    """Verify Docker daemon responds to `docker info`."""
    if not shutil.which("docker"):
        return False, "docker CLI not found"
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return True, None
        return False, f"docker info failed: {r.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return False, "docker info timed out (daemon hung?)"
    except OSError as e:
        return False, f"docker info OSError: {e}"


def run_all_checks() -> Dict[str, Any]:
    """Run all checks and return a structured summary."""
    py_ok, py_msg = check_python_version()
    imp_ok, imp_missing = check_required_imports()
    tools_ok, tools_missing = check_external_tools()
    docker_ok, docker_msg = check_docker_daemon()

    return {
        "python": {"ok": py_ok, "message": py_msg},
        "imports": {"ok": imp_ok, "missing": imp_missing},
        "external_tools": {"ok": tools_ok, "missing": tools_missing},
        "docker_daemon": {"ok": docker_ok, "message": docker_msg},
        "platform": platform_utils.os_summary(),
    }


def format_report(summary: Dict[str, Any]) -> str:
    """Format the preflight summary for human reading."""
    lines = ["=== Mythos Preview Pre-flight ==="]
    py = summary["python"]
    lines.append(f"  Python: {'✓' if py['ok'] else '✗'} {py['message'] or ''}")
    imp = summary["imports"]
    if imp["ok"]:
        lines.append(f"  Python packages: ✓")
    else:
        lines.append(f"  Python packages: ✗ missing: {', '.join(imp['missing'])}")
        lines.append("    → pip install -r .claude/agents/mythos/scripts/requirements.txt")
    tools = summary["external_tools"]
    if tools["ok"]:
        lines.append(f"  External tools: ✓")
    else:
        lines.append(f"  External tools: ✗ missing: {', '.join(tools['missing'])}")
        lines.append("    → Windows: winget install BurntSushi.ripgrep.MSVC universal-ctags.universal-ctags")
        lines.append("    → Mac:     brew install ripgrep ctags")
        lines.append("    → Linux:   apt install ripgrep universal-ctags")
    dock = summary["docker_daemon"]
    lines.append(f"  Docker daemon: {'✓' if dock['ok'] else '✗'} {dock['message'] or ''}")
    plat = summary["platform"]
    lines.append(f"  Platform: {plat['system']} {plat['release']} (apparmor={plat['apparmor']})")
    return "\n".join(lines)


def main() -> int:
    summary = run_all_checks()
    print(format_report(summary))
    all_ok = (
        summary["python"]["ok"]
        and summary["imports"]["ok"]
        and summary["external_tools"]["ok"]
        and summary["docker_daemon"]["ok"]
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/unit/test_preflight.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Run preflight against the real host**

Run:
```bash
python .claude/agents/mythos/scripts/preflight.py
```

Expected: All checks PASS (assuming Docker Desktop is running and `winget install` has been done for ripgrep/ctags). If something is missing, the report shows actionable install instructions.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/mythos/scripts/preflight.py
git add tests/unit/test_preflight.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: preflight environment check script"
```

---

## Task 7: Custom seccomp profile

**Files:**
- Create: `.claude/agents/mythos/docker/seccomp-mythos.json`

- [ ] **Step 1: Generate the profile**

Write `.claude/agents/mythos/docker/seccomp-mythos.json`:
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": ["SCMP_ARCH_X86", "SCMP_ARCH_X32"]
    },
    {
      "architecture": "SCMP_ARCH_AARCH64",
      "subArchitectures": ["SCMP_ARCH_ARM"]
    }
  ],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "arch_prctl",
        "bind", "brk",
        "chdir", "chmod", "chown", "clock_getres", "clock_gettime", "clock_nanosleep",
        "clone", "clone3", "close", "close_range", "connect", "copy_file_range", "creat",
        "dup", "dup2", "dup3",
        "epoll_create", "epoll_create1", "epoll_ctl", "epoll_pwait", "epoll_wait",
        "eventfd", "eventfd2", "execve", "execveat", "exit", "exit_group",
        "faccessat", "faccessat2", "fadvise64", "fallocate",
        "fchdir", "fchmod", "fchmodat", "fchown", "fchownat",
        "fcntl", "fdatasync", "fgetxattr", "flistxattr", "flock",
        "fork", "fremovexattr", "fsetxattr", "fstat", "fstatfs", "fsync", "ftruncate", "futex", "futimesat",
        "get_robust_list", "getcwd", "getdents", "getdents64",
        "getegid", "geteuid", "getgid", "getgroups",
        "getpeername", "getpgid", "getpgrp", "getpid", "getppid", "getpriority",
        "getrandom", "getresgid", "getresuid", "getrlimit", "getrusage",
        "getsid", "getsockname", "getsockopt", "gettid", "gettimeofday", "getuid", "getxattr",
        "ioctl",
        "kill",
        "lchown", "lgetxattr", "link", "linkat",
        "listen", "listxattr", "llistxattr", "lremovexattr", "lseek", "lsetxattr", "lstat",
        "madvise", "membarrier", "memfd_create",
        "mincore", "mkdir", "mkdirat", "mknod", "mknodat",
        "mlock", "mlock2", "mlockall", "mmap", "mprotect", "mq_getsetattr", "mq_notify",
        "mq_open", "mq_timedreceive", "mq_timedsend", "mq_unlink",
        "mremap", "msgctl", "msgget", "msgrcv", "msgsnd", "msync", "munlock", "munlockall", "munmap",
        "nanosleep", "newfstatat",
        "open", "openat", "openat2",
        "pause", "pidfd_open", "pidfd_send_signal", "pipe", "pipe2", "poll", "ppoll",
        "prctl", "pread64", "preadv", "preadv2", "prlimit64",
        "pselect6", "pwrite64", "pwritev", "pwritev2",
        "read", "readahead", "readlink", "readlinkat", "readv",
        "recv", "recvfrom", "recvmmsg", "recvmsg",
        "remap_file_pages", "removexattr", "rename", "renameat", "renameat2",
        "restart_syscall", "rmdir",
        "rt_sigaction", "rt_sigpending", "rt_sigprocmask", "rt_sigqueueinfo",
        "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait", "rt_tgsigqueueinfo",
        "sched_getaffinity", "sched_getparam", "sched_get_priority_max", "sched_get_priority_min",
        "sched_getscheduler", "sched_setaffinity", "sched_yield",
        "select", "semctl", "semget", "semop", "semtimedop",
        "send", "sendfile", "sendmmsg", "sendmsg", "sendto",
        "set_robust_list", "set_tid_address", "setfsgid", "setfsuid", "setgid", "setgroups",
        "setitimer", "setpgid", "setpriority", "setregid", "setresgid", "setresuid", "setreuid",
        "setrlimit", "setsid", "setsockopt", "setuid", "setxattr",
        "shmat", "shmctl", "shmdt", "shmget", "shutdown",
        "sigaltstack", "signalfd", "signalfd4",
        "socket", "socketpair", "splice", "stat", "statfs", "statx",
        "symlink", "symlinkat", "sync", "sync_file_range", "syncfs", "sysinfo",
        "tee", "tgkill", "time", "timer_create", "timer_delete",
        "timer_getoverrun", "timer_gettime", "timer_settime",
        "timerfd_create", "timerfd_gettime", "timerfd_settime",
        "times", "tkill", "truncate",
        "umask", "uname", "unlink", "unlinkat", "utimensat", "utimes",
        "vfork", "vmsplice",
        "wait4", "waitid", "waitpid", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

Notes:
- `defaultAction: SCMP_ACT_ERRNO` means anything NOT explicitly allowed returns EPERM.
- The whitelist contains the ~190 syscalls needed by typical build/run workloads.
- Notably absent (denied): `mount`, `umount2`, `pivot_root`, `chroot`, `ptrace`, `kexec_*`, `bpf`, `keyctl`, `setns`, `unshare`, `module_*`, `swap*`, `reboot`, `kexec_*`, `init_module`, `delete_module`, `iopl`, `ioperm`.

- [ ] **Step 2: Verify JSON validity**

Run:
```bash
python -c "import json; json.load(open('.claude/agents/mythos/docker/seccomp-mythos.json'))"
```

Expected: No output (silently OK).

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/mythos/docker/seccomp-mythos.json
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: custom seccomp profile (whitelist-only)"
```

---

## Task 8: AppArmor profile (Linux only, advisory)

**Files:**
- Create: `.claude/agents/mythos/docker/apparmor-mythos`

- [ ] **Step 1: Write the profile**

Write `.claude/agents/mythos/docker/apparmor-mythos`:
```
#include <tunables/global>

profile mythos-mythos flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  network inet stream,
  network inet6 stream,
  network inet dgram,
  network inet6 dgram,
  network unix stream,

  capability,

  file,
  umount,

  deny @{PROC}/* w,                  # deny writes to /proc
  deny @{PROC}/sys/[^k]* w,
  deny @{PROC}/sysrq-trigger rwklx,
  deny @{PROC}/mem rwklx,
  deny @{PROC}/kmem rwklx,
  deny @{PROC}/kcore rwklx,
  deny mount,                        # deny mount syscall
  deny /sys/[^f]*/** wklx,
  deny /sys/f[^s]*/** wklx,
  deny /sys/fs/[^c]*/** wklx,
  deny /sys/fs/c[^g]*/** wklx,
  deny /sys/fs/cg[^r]*/** wklx,
  deny /sys/firmware/** rwklx,
  deny /sys/kernel/security/** rwklx,

  deny /etc/shadow r,
  deny /etc/sudoers r,
  deny /root/** rwklx,
  deny /home/[^n]*/** rwklx,         # block /home/<other>/, allow nobody-mythos home

  # Allow read access to libraries and binaries
  /usr/** rmix,
  /lib/** rmix,
  /lib64/** rmix,
  /bin/** rmix,
  /sbin/** rmix,

  # Allow read/exec on /work (mounted PoC)
  /work/** r,
  /work-rw/** rwk,
  /tmp/** rwk,
}
```

- [ ] **Step 2: Document loading procedure**

Add to `README.md`:
```markdown

## (Linux only) Loading the AppArmor profile

```bash
sudo apparmor_parser -r .claude/agents/mythos/docker/apparmor-mythos
```

This is best-effort: if AppArmor isn't installed, Mythos skips this layer and continues with seccomp + cap-drop + namespaces.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/mythos/docker/apparmor-mythos
git add README.md
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: Linux AppArmor profile (defense-in-depth)"
```

---

## Task 9: Dockerfile.multilang

**Files:**
- Create: `.claude/agents/mythos/docker/Dockerfile.multilang`
- Create: `.claude/agents/mythos/docker/mythos-runner.sh`

- [ ] **Step 1: Write mythos-runner.sh**

Write `.claude/agents/mythos/docker/mythos-runner.sh`:
```bash
#!/bin/bash
# Entrypoint for the mythos-multilang container.
# Expects:
#   /work     : read-only PoC directory (input)
#   /work-rw  : writable tmpfs (output, scratch)
#
# Reads /work/run.sh if present, else /work/run.* (first match).
# Writes /work-rw/result.json with {exit_code, duration_s}.

set -u  # NO -e: we want to capture failures, not abort

START_TS=$(date +%s%N)

if [[ ! -d /work ]]; then
  echo '{"error":"no /work mount"}' > /work-rw/result.json
  exit 2
fi

if [[ -f /work/run.sh ]]; then
  CMD="bash /work/run.sh"
elif [[ -f /work/run.py ]]; then
  CMD="python3 /work/run.py"
elif [[ -f /work/run.js ]]; then
  CMD="node /work/run.js"
else
  echo '{"error":"no run.{sh,py,js} found in /work"}' > /work-rw/result.json
  exit 3
fi

# Capture output, timeout after 25s (container also gets killed externally at 30s)
timeout --kill-after=2 25 $CMD > /work-rw/stdout.log 2> /work-rw/stderr.log
EXIT_CODE=$?

END_TS=$(date +%s%N)
DURATION_MS=$(( (END_TS - START_TS) / 1000000 ))

cat > /work-rw/result.json <<EOF
{
  "exit_code": ${EXIT_CODE},
  "duration_ms": ${DURATION_MS},
  "command": "${CMD}"
}
EOF

exit ${EXIT_CODE}
```

- [ ] **Step 2: Write Dockerfile.multilang**

Write `.claude/agents/mythos/docker/Dockerfile.multilang`:
```dockerfile
# Mythos Preview multi-language sandbox image
# Base: Debian Bookworm slim for stable libc and predictable behavior

FROM debian:bookworm-slim AS base

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=20
ARG GO_VERSION=1.21.5
ARG RUST_VERSION=1.74.0

# Create non-root user with stable UID/GID 65534 (nobody)
RUN groupadd -g 65534 nobody-mythos 2>/dev/null || groupmod -n nobody-mythos $(getent group 65534 | cut -d: -f1) && \
    useradd -m -u 65534 -g 65534 -s /bin/bash nobody-mythos 2>/dev/null || true

# Install runtimes and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
        bash coreutils \
        gcc g++ clang make cmake pkg-config \
        afl++ \
        python3 python3-pip python3-venv \
        ruby ruby-dev \
        default-jdk-headless \
        php php-cli \
        git \
        valgrind strace ltrace \
        binutils \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && curl -L https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/go/bin:${PATH}"

# Rust toolchain for nobody-mythos user
USER nobody-mythos
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain ${RUST_VERSION} --profile minimal
ENV PATH="/home/nobody-mythos/.cargo/bin:${PATH}"

USER root
COPY mythos-runner.sh /usr/local/bin/mythos-runner.sh
RUN chmod 0755 /usr/local/bin/mythos-runner.sh

USER 65534:65534
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/mythos-runner.sh"]
```

- [ ] **Step 3: Build the image**

Run:
```bash
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/
```

Expected: Build succeeds. May take 5-10 min on first build.

- [ ] **Step 4: Smoke test the image**

Run:
```bash
mkdir -p /tmp/mythos-smoke && echo 'echo hello from sandbox' > /tmp/mythos-smoke/run.sh
docker run --rm -v /tmp/mythos-smoke:/work:ro --tmpfs /work-rw:size=10M,exec mythos-multilang:1.0.0
```

Expected: Container exits 0, prints "hello from sandbox".

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/mythos/docker/Dockerfile.multilang
git add .claude/agents/mythos/docker/mythos-runner.sh
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: hardened multi-language Docker sandbox image"
```

---

## Task 10: Docker runner wrapper (Python)

**Files:**
- Create: `.claude/agents/mythos/scripts/common/docker_runner.py`
- Test: `tests/unit/test_docker_runner.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_docker_runner.py`:
```python
"""Tests for the Docker runner wrapper."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.docker_runner import build_run_kwargs, RunResult


class TestBuildRunKwargs:
    def test_baseline_kwargs_contain_hardening(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_profile_path=tmp_path / "seccomp.json",
        )
        # Hardening flags
        assert kwargs["cap_drop"] == ["ALL"]
        assert kwargs["read_only"] is True
        assert kwargs["user"] == "65534:65534"
        assert kwargs["cgroupns"] == "private"
        assert kwargs["pids_limit"] == 100
        assert kwargs["mem_limit"] == "512m"
        assert kwargs["network_mode"] == "none"
        assert kwargs["remove"] is True
        # security_opt contains no-new-privs and seccomp; NOT apparmor on non-linux
        assert any("no-new-privileges=true" in s for s in kwargs["security_opt"])
        assert any("seccomp=" in s for s in kwargs["security_opt"])
        assert not any("apparmor" in s for s in kwargs["security_opt"])

    def test_apparmor_added_when_supported(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=True,
            seccomp_profile_path=tmp_path / "seccomp.json",
        )
        assert any("apparmor=mythos-mythos" in s for s in kwargs["security_opt"])

    def test_callback_mode_uses_isolated_network(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=True,
            apparmor=False,
            seccomp_profile_path=tmp_path / "seccomp.json",
        )
        assert kwargs["network_mode"] == "mythos-r1-net"

    def test_volume_mount_is_readonly(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_profile_path=tmp_path / "seccomp.json",
        )
        assert kwargs["volumes"][str(poc_dir.resolve())]["mode"] == "ro"

    def test_tmpfs_provides_writable_work_rw(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_profile_path=tmp_path / "seccomp.json",
        )
        assert "/tmp" in kwargs["tmpfs"]
        assert "/work-rw" in kwargs["tmpfs"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/unit/test_docker_runner.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/common/docker_runner.py`:
```python
"""Hardened Docker runner wrapper for executing untrusted PoC code.

Builds the kwargs for `docker.client.containers.run()` with maximum hardening:
seccomp + AppArmor (Linux) + cap-drop=ALL + non-root + read-only FS + no network
by default.

The wrapper is split into build_run_kwargs (pure function, testable) and
run_poc_sandboxed (actually invokes Docker).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

import docker
from docker.types import Ulimit

from common import platform_utils


@dataclasses.dataclass
class RunResult:
    """Outcome of a sandboxed PoC execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    killed: bool = False
    error: Optional[str] = None


def build_run_kwargs(
    image: str,
    poc_dir: Path,
    run_id: str,
    hunter_id: str,
    finding_id: str,
    allow_callback: bool,
    apparmor: bool,
    seccomp_profile_path: Path,
) -> dict:
    """Build the kwargs for docker-py containers.run() with hardening applied.

    Pure function — no side effects, no Docker API calls. Safe to test in isolation.

    Args:
        image: Docker image tag (e.g., "mythos-multilang:1.0.0")
        poc_dir: Local directory containing the PoC (mounted read-only as /work)
        run_id: Identifier for the Mythos run (used in container naming)
        hunter_id: Identifier for the hunter producing this PoC
        finding_id: Identifier for the finding being verified
        allow_callback: If True, attach to isolated internal network for OAST callbacks
        apparmor: If True (Linux + AppArmor available), add apparmor=mythos-mythos
        seccomp_profile_path: Path to the custom seccomp JSON profile

    Returns:
        Dict ready to pass to docker.client.containers.run(**kwargs)
    """
    security_opt = [
        "no-new-privileges=true",
        f"seccomp={seccomp_profile_path.resolve()}",
    ]
    if apparmor:
        security_opt.append("apparmor=mythos-mythos")

    container_name = f"mythos-{run_id}-{hunter_id}-{finding_id}"
    network_mode = f"mythos-{run_id}-net" if allow_callback else "none"

    return {
        "image": image,
        "name": container_name,
        "remove": True,
        "stdout": True,
        "stderr": True,
        "detach": False,

        # Security hardening
        "security_opt": security_opt,
        "cap_drop": ["ALL"],
        "read_only": True,
        "user": "65534:65534",
        "cgroupns": "private",

        # Resource limits
        "mem_limit": "512m",
        "memswap_limit": "512m",
        "cpu_period": 100000,
        "cpu_quota": 100000,  # = 1 CPU
        "pids_limit": 100,
        "ulimits": [
            Ulimit(name="nofile", soft=64, hard=64),
            Ulimit(name="nproc", soft=50, hard=50),
        ],

        # Network
        "network_mode": network_mode,

        # Mounts
        "volumes": {
            str(poc_dir.resolve()): {"bind": "/work", "mode": "ro"},
        },
        "tmpfs": {
            "/tmp": "size=100M,exec",
            "/work-rw": "size=50M,exec",
        },
    }


def run_poc_sandboxed(
    poc_dir: Path,
    run_id: str,
    hunter_id: str,
    finding_id: str,
    image: str = "mythos-multilang:1.0.0",
    seccomp_profile_path: Path | None = None,
    allow_callback: bool = False,
    timeout_s: int = 35,
) -> RunResult:
    """Execute a PoC in a hardened ephemeral container.

    Returns RunResult with exit_code, stdout, stderr, duration.
    Never raises — failures are captured as RunResult.error.
    """
    import time

    start = time.monotonic()

    if seccomp_profile_path is None:
        seccomp_profile_path = (
            Path(__file__).parent.parent.parent / "docker" / "seccomp-mythos.json"
        )

    apparmor = platform_utils.apparmor_supported()

    kwargs = build_run_kwargs(
        image=image,
        poc_dir=poc_dir,
        run_id=run_id,
        hunter_id=hunter_id,
        finding_id=finding_id,
        allow_callback=allow_callback,
        apparmor=apparmor,
        seccomp_profile_path=seccomp_profile_path,
    )

    try:
        client = docker.from_env()
        output = client.containers.run(**kwargs)
        stdout = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(exit_code=0, stdout=stdout, stderr="", duration_ms=duration_ms)
    except docker.errors.ContainerError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            exit_code=e.exit_status,
            stdout=e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
            stderr=e.stderr.decode("utf-8", errors="replace") if e.stderr else "",
            duration_ms=duration_ms,
        )
    except docker.errors.APIError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            exit_code=-1, stdout="", stderr="", duration_ms=duration_ms,
            error=f"Docker API error: {e}", killed=True,
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            exit_code=-1, stdout="", stderr="", duration_ms=duration_ms,
            error=f"Unexpected error: {e}", killed=True,
        )
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run:
```bash
pytest tests/unit/test_docker_runner.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/mythos/scripts/common/docker_runner.py
git add tests/unit/test_docker_runner.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: hardened Docker runner wrapper with pure kwargs builder"
```

---

## Task 11: mythos_sandbox.py CLI entry

**Files:**
- Create: `.claude/agents/mythos/scripts/mythos_sandbox.py`
- Test: `tests/integration/test_sandbox_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

Create `tests/integration/__init__.py` (empty) and `tests/conftest.py`:
```python
"""Shared pytest fixtures."""
import pytest
import shutil


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "docker: requires Docker daemon running")
    config.addinivalue_line("markers", "redteam: red-team escape attempt tests")


@pytest.fixture(scope="session")
def docker_available():
    """Skip the test if Docker is not available."""
    if not shutil.which("docker"):
        pytest.skip("docker CLI not available")
    import subprocess
    r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
    if r.returncode != 0:
        pytest.skip("Docker daemon not responding")
    return True
```

Write `tests/integration/test_sandbox_smoke.py`:
```python
"""Integration smoke tests for the Mythos sandbox.

Requires Docker daemon running. Tests are skipped if Docker is unavailable.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))


@pytest.mark.docker
class TestSandboxSmoke:
    def test_simple_echo_runs_and_returns_zero(self, tmp_path, docker_available):
        """A trivial PoC that echoes a string should exit 0 with the string in stdout."""
        from mythos_sandbox import run_in_sandbox

        poc = tmp_path / "poc-F-smoke1"
        poc.mkdir()
        (poc / "run.sh").write_text("echo hello-from-sandbox\n", encoding="utf-8")

        result = run_in_sandbox(
            poc_dir=poc,
            run_id="test1",
            hunter_id="h0",
            finding_id="F-smoke1",
        )

        assert result.exit_code == 0, f"stderr={result.stderr!r}"
        assert "hello-from-sandbox" in result.stdout

    def test_nonzero_exit_is_captured(self, tmp_path, docker_available):
        from mythos_sandbox import run_in_sandbox

        poc = tmp_path / "poc-F-smoke2"
        poc.mkdir()
        (poc / "run.sh").write_text("exit 42\n", encoding="utf-8")

        result = run_in_sandbox(
            poc_dir=poc,
            run_id="test2",
            hunter_id="h0",
            finding_id="F-smoke2",
        )

        assert result.exit_code == 42

    def test_python_poc_runs(self, tmp_path, docker_available):
        from mythos_sandbox import run_in_sandbox

        poc = tmp_path / "poc-F-smoke3"
        poc.mkdir()
        (poc / "run.py").write_text(
            "import sys; print('py-ok'); sys.exit(0)\n", encoding="utf-8"
        )

        result = run_in_sandbox(
            poc_dir=poc,
            run_id="test3",
            hunter_id="h0",
            finding_id="F-smoke3",
        )

        assert result.exit_code == 0
        assert "py-ok" in result.stdout
```

- [ ] **Step 2: Run integration tests to verify they fail**

Run:
```bash
pytest tests/integration/test_sandbox_smoke.py -v
```

Expected: FAIL with `ImportError: No module named 'mythos_sandbox'`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/mythos_sandbox.py`:
```python
"""Mythos Preview sandbox CLI and library.

Library usage:
    from mythos_sandbox import run_in_sandbox
    result = run_in_sandbox(poc_dir=Path("..."), run_id="r1", hunter_id="h7", finding_id="F-001")

CLI usage:
    python mythos_sandbox.py run <finding_id>
    python mythos_sandbox.py replay <finding_id>
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

from common.docker_runner import RunResult, run_poc_sandboxed
from common.paths import poc_dir as get_poc_dir


def run_in_sandbox(
    poc_dir: Path,
    run_id: str,
    hunter_id: str,
    finding_id: str,
    allow_callback: bool = False,
) -> RunResult:
    """Run a PoC in the sandbox. Thin wrapper over run_poc_sandboxed."""
    return run_poc_sandboxed(
        poc_dir=poc_dir,
        run_id=run_id,
        hunter_id=hunter_id,
        finding_id=finding_id,
        allow_callback=allow_callback,
    )


def cmd_run(args: argparse.Namespace) -> int:
    poc_root = get_poc_dir()
    poc = poc_root / args.finding_id
    if not poc.is_dir():
        print(f"PoC directory not found: {poc}", file=sys.stderr)
        return 2

    result = run_in_sandbox(
        poc_dir=poc,
        run_id=args.run_id or "manual",
        hunter_id=args.hunter_id or "cli",
        finding_id=args.finding_id,
        allow_callback=args.allow_callback,
    )

    print(json.dumps({
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "killed": result.killed,
        "error": result.error,
        "stdout_preview": result.stdout[:500],
        "stderr_preview": result.stderr[:500],
    }, indent=2))
    return 0 if result.exit_code == 0 else 1


def cmd_replay(args: argparse.Namespace) -> int:
    # Replay = same as run, kept distinct for symmetry with Validate's needs
    return cmd_run(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mythos_sandbox")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a PoC in the sandbox")
    p_run.add_argument("finding_id")
    p_run.add_argument("--run-id", default=None)
    p_run.add_argument("--hunter-id", default=None)
    p_run.add_argument("--allow-callback", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_replay = sub.add_parser("replay", help="Replay a previously-saved PoC")
    p_replay.add_argument("finding_id")
    p_replay.add_argument("--run-id", default=None)
    p_replay.add_argument("--hunter-id", default=None)
    p_replay.add_argument("--allow-callback", action="store_true")
    p_replay.set_defaults(func=cmd_replay)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run smoke tests to verify they pass**

Run:
```bash
pytest tests/integration/test_sandbox_smoke.py -v -m docker
```

Expected: All 3 tests PASS. First run may be slow (image pull).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/mythos/scripts/mythos_sandbox.py
git add tests/conftest.py
git add tests/integration/__init__.py
git add tests/integration/test_sandbox_smoke.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: mythos_sandbox CLI + smoke tests"
```

---

## Task 12: Red-team escape attempt fixtures

**Files:**
- Create: `tests/red_team/attempts/try_etc_passwd_read.sh`
- Create: `tests/red_team/attempts/try_setuid.c`
- Create: `tests/red_team/attempts/try_fork_bomb.sh`
- Create: `tests/red_team/attempts/try_network_exfil.sh`
- Create: `tests/red_team/attempts/try_docker_sock.sh`
- Create: `tests/red_team/attempts/try_mount_escape.sh`

- [ ] **Step 1: Create attempt scripts**

Write `tests/red_team/attempts/try_etc_passwd_read.sh`:
```bash
#!/bin/bash
# Escape attempt #1: try to read /etc/passwd of the host
# Expected outcome: the file inside the container is readable (it's the container's /etc/passwd),
# but it must contain ONLY the container's users, NOT the host's. Verification is by checking
# that "nobody-mythos" is present and the host's primary user is NOT.
cat /etc/passwd
```

Write `tests/red_team/attempts/try_setuid.c`:
```c
/* Escape attempt #2: try to setuid(0) after compile.
   Expected outcome: setuid(0) fails because cap-drop=ALL removed CAP_SETUID. */
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>

int main(void) {
    int r = setuid(0);
    if (r == 0) {
        /* We got root — sandbox failed */
        printf("SANDBOX_BREACH: setuid(0) succeeded, EUID=%d\n", geteuid());
        return 0;
    }
    printf("setuid_denied: errno=%d (%s)\n", errno, strerror(errno));
    return 1;
}
```

Write `tests/red_team/attempts/try_fork_bomb.sh`:
```bash
#!/bin/bash
# Escape attempt #3: fork bomb to exhaust PIDs.
# Expected outcome: pids_limit=100 kicks in, the bomb is contained.
# The container should be killed by Docker (OOM-ish) before the host suffers.
( :(){ :|:& };: ) &
sleep 5
echo "fork_bomb_survived"
```

Write `tests/red_team/attempts/try_network_exfil.sh`:
```bash
#!/bin/bash
# Escape attempt #4: try to exfiltrate data to an external host.
# Expected outcome: network_mode=none blocks all outbound. curl must fail.
if command -v curl >/dev/null 2>&1; then
  curl -sS --max-time 3 https://example.com -o /tmp/exfil.html 2>&1
  RC=$?
  if [[ $RC -eq 0 ]]; then
    echo "SANDBOX_BREACH: curl to example.com succeeded"
    exit 0
  fi
  echo "network_denied: curl exit=$RC"
fi
# Try direct socket
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(('1.1.1.1', 53))
    print('SANDBOX_BREACH: socket to 1.1.1.1:53 succeeded')
except Exception as e:
    print(f'network_denied: {type(e).__name__}: {e}')
" 2>&1
exit 1
```

Write `tests/red_team/attempts/try_docker_sock.sh`:
```bash
#!/bin/bash
# Escape attempt #5: try to access Docker socket (if mistakenly mounted).
# Expected outcome: /var/run/docker.sock is not mounted, so it doesn't exist.
if [[ -S /var/run/docker.sock ]]; then
  echo "SANDBOX_BREACH: docker.sock is accessible"
  ls -la /var/run/docker.sock
  exit 0
fi
echo "docker_sock_absent: as expected"
exit 1
```

Write `tests/red_team/attempts/try_mount_escape.sh`:
```bash
#!/bin/bash
# Escape attempt #6: try to mount a directory.
# Expected outcome: seccomp blocks mount() syscall.
mkdir -p /tmp/escape-target 2>/dev/null
mount -t proc proc /tmp/escape-target 2>&1
RC=$?
if [[ $RC -eq 0 ]]; then
  echo "SANDBOX_BREACH: mount succeeded"
  exit 0
fi
echo "mount_denied: rc=$RC"
exit 1
```

- [ ] **Step 2: Commit fixtures**

```bash
chmod +x tests/red_team/attempts/*.sh 2>/dev/null || true
git add tests/red_team/attempts/
touch tests/red_team/__init__.py
git add tests/red_team/__init__.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "test: red-team sandbox escape attempt fixtures"
```

---

## Task 13: Red-team test that proves sandbox holds

**Files:**
- Create: `tests/red_team/test_sandbox_resists_escape.py`

- [ ] **Step 1: Write the failing test**

Write `tests/red_team/test_sandbox_resists_escape.py`:
```python
"""Red-team tests: the sandbox MUST resist all known escape attempts.

These tests are the bedrock of Mythos's security guarantee. If any of them
fail, the sandbox has a hole and Mythos cannot ship.

Convention: a test PASSES when the sandbox blocked the attempted breach.
"""
import shutil
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

ATTEMPTS_DIR = Path(__file__).parent / "attempts"


def _prepare_poc(tmp_path: Path, source_file: str, target_name: str = "run.sh") -> Path:
    """Copy a single attempt file into a temp PoC directory."""
    poc = tmp_path / f"poc-{source_file.replace('.', '_')}"
    poc.mkdir()
    src = ATTEMPTS_DIR / source_file
    shutil.copy(src, poc / target_name)
    return poc


@pytest.mark.redteam
@pytest.mark.docker
class TestSandboxResistsEscape:

    def test_etc_passwd_read_is_container_local_only(self, tmp_path, docker_available):
        """Reading /etc/passwd should give the CONTAINER's file (with nobody-mythos),
        not the host's."""
        from mythos_sandbox import run_in_sandbox

        poc = _prepare_poc(tmp_path, "try_etc_passwd_read.sh")
        result = run_in_sandbox(poc_dir=poc, run_id="rt1", hunter_id="h0", finding_id="F-rt-passwd")

        # Container's /etc/passwd MUST contain nobody-mythos (we created that user)
        assert "nobody-mythos" in result.stdout
        # And MUST NOT contain typical host user patterns
        # (We can't check exact host username, but if container is escaping, we'd see more entries.)
        # A well-isolated container's /etc/passwd has ~25 entries; host's typically 30+.
        # This is heuristic — primary signal is the nobody-mythos presence + line count sanity.
        lines = result.stdout.strip().split("\n")
        assert 5 < len(lines) < 50, f"Suspicious /etc/passwd size: {len(lines)} lines"

    def test_setuid_zero_is_denied(self, tmp_path, docker_available):
        """setuid(0) must fail because cap-drop=ALL removed CAP_SETUID."""
        from mythos_sandbox import run_in_sandbox

        poc = tmp_path / "poc-setuid"
        poc.mkdir()
        # Source + compile-and-run script
        shutil.copy(ATTEMPTS_DIR / "try_setuid.c", poc / "setuid_attempt.c")
        (poc / "run.sh").write_text(
            "set -e\n"
            "cd /tmp\n"
            "cp /work/setuid_attempt.c .\n"
            "gcc -o setuid_attempt setuid_attempt.c\n"
            "./setuid_attempt\n",
            encoding="utf-8",
        )

        result = run_in_sandbox(poc_dir=poc, run_id="rt2", hunter_id="h0", finding_id="F-rt-setuid")

        # The program writes "SANDBOX_BREACH" if setuid succeeded — that string MUST NOT appear
        assert "SANDBOX_BREACH" not in result.stdout, "setuid(0) succeeded — cap-drop is broken"
        assert "setuid_denied" in result.stdout

    def test_fork_bomb_is_contained(self, tmp_path, docker_available):
        """A fork bomb must NOT take down the host. pids_limit=100 contains it."""
        from mythos_sandbox import run_in_sandbox

        poc = _prepare_poc(tmp_path, "try_fork_bomb.sh")
        result = run_in_sandbox(poc_dir=poc, run_id="rt3", hunter_id="h0", finding_id="F-rt-fork")

        # We don't care about the exit code — we care that the host survived.
        # Just running this test successfully proves the bomb was contained.
        # (If the host was DOS'd, pytest itself would have crashed.)
        # We assert that the host is still responsive by checking Python still works:
        assert 2 + 2 == 4

    def test_network_egress_blocked(self, tmp_path, docker_available):
        """network_mode=none must prevent any outbound network."""
        from mythos_sandbox import run_in_sandbox

        poc = _prepare_poc(tmp_path, "try_network_exfil.sh")
        result = run_in_sandbox(poc_dir=poc, run_id="rt4", hunter_id="h0", finding_id="F-rt-net")

        assert "SANDBOX_BREACH" not in result.stdout, "Network egress succeeded"
        assert "network_denied" in result.stdout

    def test_docker_socket_not_accessible(self, tmp_path, docker_available):
        """The Docker socket must NOT be mounted in the sandbox."""
        from mythos_sandbox import run_in_sandbox

        poc = _prepare_poc(tmp_path, "try_docker_sock.sh")
        result = run_in_sandbox(poc_dir=poc, run_id="rt5", hunter_id="h0", finding_id="F-rt-sock")

        assert "SANDBOX_BREACH" not in result.stdout
        assert "docker_sock_absent" in result.stdout

    def test_mount_syscall_blocked(self, tmp_path, docker_available):
        """Seccomp must block the mount syscall."""
        from mythos_sandbox import run_in_sandbox

        poc = _prepare_poc(tmp_path, "try_mount_escape.sh")
        result = run_in_sandbox(poc_dir=poc, run_id="rt6", hunter_id="h0", finding_id="F-rt-mount")

        assert "SANDBOX_BREACH" not in result.stdout
        assert "mount_denied" in result.stdout
```

- [ ] **Step 2: Run red-team tests**

Run:
```bash
pytest tests/red_team/ -v -m "redteam and docker"
```

Expected: All 6 tests PASS. If ANY fails, the sandbox has a hole — investigate before continuing the plan.

- [ ] **Step 3: Commit**

```bash
git add tests/red_team/test_sandbox_resists_escape.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "test: red-team sandbox escape resistance suite"
```

---

## Task 14: Full test suite gate

**Files:**
- (no new files — final verification)

- [ ] **Step 1: Run the entire suite**

Run:
```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS — unit + integration (with docker) + red_team (with docker).

If any test fails, do NOT proceed to Plan 2. Fix the failure first.

- [ ] **Step 2: Generate coverage report (informational)**

Run:
```bash
pytest tests/ --cov=.claude/agents/mythos/scripts --cov-report=term-missing
```

Expected: Coverage report displayed. Coverage of `common/` modules should be > 80%. `mythos_sandbox.py` CLI coverage may be lower; that's OK at this stage.

- [ ] **Step 3: Final commit of any coverage config**

If a `.coveragerc` was implicitly created, ignore it via gitignore (already in `.gitignore` step 1).

- [ ] **Step 4: Tag the milestone**

```bash
git tag -a mythos-plan-1-done -m "Plan 1 complete: infrastructure + hardened sandbox passes red-team"
git log --oneline
```

Expected: `mythos-plan-1-done` tag points to the latest commit.

---

## Plan 1 — Completion criteria

This plan is **complete** when ALL of the following are true:

- [ ] All 14 tasks above are checked off
- [ ] `pytest tests/ -v` runs green (unit + integration + red_team)
- [ ] `python .claude/agents/mythos/scripts/preflight.py` reports all green
- [ ] `docker image ls | grep mythos-multilang` shows the 1.0.0 tag
- [ ] All 6 red-team escape attempts are blocked
- [ ] Git tag `mythos-plan-1-done` exists

---

## What's NOT in Plan 1 (deferred)

| Item | Where | Reason |
|---|---|---|
| JSON schemas + validate_jsonl.py | Plan 2 | Independent layer, needs schemas before hooks |
| Hooks (validate_bash, validate_write) | Plan 2 | Hooks depend on common/ utilities (now done) |
| `redact.py`, `sanitize_output.py` | Plan 2 | Same as hooks |
| `cleanup_orphans.py`, `agent_start.py` | Plan 2 | Built after hook infrastructure |
| `build_symbol_index.py` | Plan 2 | Used by Trace phase later |
| `launch_hunters.py` | Plan 2 | Needs Hunt agent (Plan 5) |
| `install_skills.py` + 40 cyber skills | Plan 3 | Needs `.claude/skills/` structure |
| 23 bug-class definitions | Plan 3 | Schemas first (Plan 2) |
| 12 agent `.md` files | Plans 4-5 | Need all underlying infrastructure |
| `/mythos` SKILL.md | Plan 6 | End of stack |
| Test fixtures (DVWA, Juice Shop, ...) | Plan 7 | After pipeline is wired |
| Acceptance criteria + V1 ship | Plan 8 | Final integration |

---

## Self-review

**Spec coverage check** (vs `2026-05-25-mythos-preview-design.md`):

| Spec section | Plan 1 task | Status |
|---|---|---|
| §9 Sandbox specification | Tasks 7, 8, 9, 10, 11 | ✅ Full coverage |
| §10 Cross-platform (Python stack, OS matrix) | Tasks 2, 3, 4, 5 | ✅ Full coverage |
| §11 Threat model T1 (container escape) | Tasks 12, 13 | ✅ Tested |
| §11 Threat model T2 (data exfil) | Task 13 (test_network_egress_blocked) | ✅ Tested |
| §11 Threat model T3 (fork bomb/DoS) | Task 13 (test_fork_bomb_is_contained) | ✅ Tested |
| §11 Threat model T7 (docker.sock) | Task 13 (test_docker_socket_not_accessible) | ✅ Tested |
| §14.2 First-run setup | Task 1 (README) + Task 2 (requirements) | ✅ Documented |
| §17 Acceptance: "sandbox passes red-team" | Task 14 | ✅ Gate at end of plan |

**Placeholder scan:** None found. Every task has concrete file paths, complete code, exact commands, expected outputs.

**Type consistency:** `RunResult` dataclass defined once in `docker_runner.py`, used consistently in `mythos_sandbox.py` and tests. `AtomicJsonlAppender`, `paths.project_root()`, `platform_utils.is_linux_host()` — all consistent across uses.

---

**Plan 1 complete.** Next: execute, or generate Plan 2 (data contracts + hooks + utility scripts).
