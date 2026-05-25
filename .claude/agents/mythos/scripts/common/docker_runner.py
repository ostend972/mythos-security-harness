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
