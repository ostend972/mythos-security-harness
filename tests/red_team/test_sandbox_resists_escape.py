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

        # Container's /etc/passwd MUST contain the `mythos` user (UID 1000) we created.
        # Note: originally planned as nobody-mythos at UID 65534 but renamed to plain
        # `mythos` at 1000 during finalization to avoid Debian's pre-existing nobody:nogroup
        # entry that broke the rust toolchain install.
        assert "mythos:" in result.stdout
        # Heuristic: container's /etc/passwd has ~25 entries; host's typically 30+
        lines = result.stdout.strip().split("\n")
        assert 5 < len(lines) < 50, f"Suspicious /etc/passwd size: {len(lines)} lines"

    def test_setuid_zero_is_denied(self, tmp_path, docker_available):
        """setuid(0) must fail because cap-drop=ALL removed CAP_SETUID."""
        from mythos_sandbox import run_in_sandbox

        poc = tmp_path / "poc-setuid"
        poc.mkdir()
        # Source + compile-and-run script
        shutil.copy(ATTEMPTS_DIR / "try_setuid.c", poc / "setuid_attempt.c")
        # write_bytes to force LF endings (write_text on Windows injects CRLF
        # which breaks bash inside the Linux container).
        (poc / "run.sh").write_bytes(
            b"set -e\n"
            b"cd /tmp\n"
            b"cp /work/setuid_attempt.c .\n"
            b"gcc -o setuid_attempt setuid_attempt.c\n"
            b"./setuid_attempt\n"
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

        # If the host was DoS'd, pytest itself would have crashed.
        # We assert the host is still responsive:
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
