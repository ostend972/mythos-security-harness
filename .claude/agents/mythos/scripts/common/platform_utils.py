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
    if not shutil.which("apparmor_status"):
        return False
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
