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
