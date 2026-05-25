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
        f"found {sys.version_info[0]}.{sys.version_info[1]}"
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
    lines.append(f"  Python: {'OK' if py['ok'] else 'FAIL'} {py['message'] or ''}")
    imp = summary["imports"]
    if imp["ok"]:
        lines.append("  Python packages: OK")
    else:
        lines.append(f"  Python packages: FAIL missing: {', '.join(imp['missing'])}")
        lines.append("    -> pip install -r .claude/agents/mythos/scripts/requirements.txt")
    tools = summary["external_tools"]
    if tools["ok"]:
        lines.append("  External tools: OK")
    else:
        lines.append(f"  External tools: FAIL missing: {', '.join(tools['missing'])}")
        lines.append("    -> Windows: winget install BurntSushi.ripgrep.MSVC universal-ctags.universal-ctags")
        lines.append("    -> Mac:     brew install ripgrep ctags")
        lines.append("    -> Linux:   apt install ripgrep universal-ctags")
    dock = summary["docker_daemon"]
    lines.append(f"  Docker daemon: {'OK' if dock['ok'] else 'FAIL'} {dock['message'] or ''}")
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
