"""Hardened Docker runner wrapper for executing untrusted PoC code.

Builds the kwargs for `docker.client.containers.run()` with maximum hardening:
seccomp + AppArmor (Linux) + cap-drop=ALL + non-root + read-only FS + no network
by default.

The wrapper is split into build_run_kwargs (pure function, testable) and
run_poc_sandboxed (actually invokes Docker).
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Optional

import docker
from docker.types import Ulimit

from common import platform_utils


def _to_daemon_path(p: Path) -> str:
    """Convert a host path to one the Docker daemon can read.

    On Windows with Docker Desktop (WSL2 backend), the daemon runs inside a
    Linux VM and accesses Windows files via /mnt/c/... — passing a raw
    `C:\\path\\to\\file` makes the daemon mis-parse the value as inline JSON.
    On Linux/Mac native, no conversion is needed.
    """
    resolved = str(p.resolve())
    if platform_utils.is_windows_host():
        m = re.match(r"^([A-Za-z]):[\\/](.*)$", resolved)
        if m:
            drive = m.group(1).lower()
            rest = m.group(2).replace("\\", "/")
            return f"/mnt/{drive}/{rest}"
    return resolved


@dataclasses.dataclass
class RunResult:
    """Outcome of a sandboxed PoC execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    killed: bool = False
    error: Optional[str] = None


def load_seccomp_inline(profile_path: Path) -> str:
    """Read and compact a seccomp JSON profile for inline embedding.

    Docker Desktop on Windows (WSL2 backend) does not reliably read seccomp
    profile files from Windows paths or /mnt/c/... — it returns
    "Decoding seccomp profile failed: invalid character ..." errors. We pass
    the JSON content inline (Docker accepts both forms; inline is portable).
    """
    import json as _json
    content = profile_path.read_text(encoding="utf-8")
    return _json.dumps(_json.loads(content), separators=(",", ":"))


def build_run_kwargs(
    image: str,
    poc_dir: Path,
    run_id: str,
    hunter_id: str,
    finding_id: str,
    allow_callback: bool,
    apparmor: bool,
    seccomp_profile_path: Path | None = None,
    seccomp_inline: str | None = None,
) -> dict:
    """Build the kwargs for docker-py containers.run() with hardening applied.

    Pure function — no side effects, no Docker API calls. Safe to test in isolation.

    Provide ONE of:
        seccomp_profile_path: path to a JSON file (read and inlined)
        seccomp_inline: pre-computed compact JSON string

    Both default to None which results in an empty seccomp profile reference
    (`seccomp=`) — only useful for tests that don't exercise the daemon.
    """
    if seccomp_inline is None and seccomp_profile_path is not None:
        seccomp_inline = load_seccomp_inline(seccomp_profile_path)
    security_opt = [
        "no-new-privileges=true",
        f"seccomp={seccomp_inline or ''}",
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
        "user": "1000:1000",
        "cgroupns": "private",

        # Resource limits
        "mem_limit": "512m",
        "memswap_limit": "512m",
        "cpu_period": 100000,
        "cpu_quota": 100000,  # = 1 CPU
        "pids_limit": 100,
        "ulimits": [
            # nproc=200 still protects against fork-bombs while allowing the
            # normal shell-toolchain (bash + timeout + gcc + ...) to function.
            # nofile=256 is enough for typical compiles; pids_limit=100 provides
            # the harder cgroup-level bound.
            Ulimit(name="nofile", soft=256, hard=256),
            Ulimit(name="nproc", soft=200, hard=200),
        ],

        # Network
        "network_mode": network_mode,

        # Mounts — bind source uses host path (Docker Desktop translates to WSL2
        # mounts automatically). Only `seccomp` needs special daemon-path
        # handling because it's parsed by the daemon directly, not bind-mounted.
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
        # Use detach=True so we can read stdout AND stderr independently,
        # regardless of exit code. Then wait for completion and collect logs.
        # We must NOT pass remove=True here because the container is removed
        # by Docker before we can read its logs; we remove manually after.
        kwargs_detached = dict(kwargs)
        kwargs_detached["remove"] = False
        kwargs_detached["detach"] = True
        # Drop sync-only kwargs (stdout/stderr) that aren't accepted in detached mode
        kwargs_detached.pop("stdout", None)
        kwargs_detached.pop("stderr", None)

        container = client.containers.run(**kwargs_detached)
        try:
            wait_result = container.wait(timeout=timeout_s)
            exit_code = int(wait_result.get("StatusCode", -1)) if isinstance(wait_result, dict) else int(wait_result)
            stdout_bytes = container.logs(stdout=True, stderr=False)
            stderr_bytes = container.logs(stdout=False, stderr=True)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        finally:
            try:
                container.remove(v=True, force=True)
            except Exception:
                pass

        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
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
