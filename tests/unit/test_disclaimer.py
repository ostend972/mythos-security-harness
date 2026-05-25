"""Tests for disclaimer.py."""
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "disclaimer.py"


def run_cli(*args: str, cwd: Path) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                       capture_output=True, text=True, timeout=10)
    return r.returncode, r.stdout, r.stderr


def test_check_returns_2_when_no_acknowledgment(tmp_path):
    # Run from a fresh dir without the acknowledgment file
    rc, _, _ = run_cli("--check", cwd=tmp_path)
    assert rc == 2


def test_accept_creates_acknowledgment(tmp_path):
    rc, out, _ = run_cli("--accept", cwd=tmp_path)
    assert rc == 0
    ack = tmp_path / ".claude" / "agents" / "mythos" / ".acknowledged"
    assert ack.is_file()
    content = ack.read_text(encoding="utf-8")
    assert content.startswith("ACKNOWLEDGED")


def test_check_returns_0_after_accept(tmp_path):
    run_cli("--accept", cwd=tmp_path)
    rc, _, _ = run_cli("--check", cwd=tmp_path)
    assert rc == 0


def test_default_invocation_prints_disclaimer_and_returns_2(tmp_path):
    rc, _, err = run_cli(cwd=tmp_path)
    assert rc == 2
    assert "Dual-Use" in err or "dual-use" in err.lower()
