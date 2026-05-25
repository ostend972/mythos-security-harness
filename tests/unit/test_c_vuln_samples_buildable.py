"""Verify c-vuln-samples can compile inside the Mythos sandbox."""
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


FIXTURE_DIR = (
    Path(__file__).parent.parent.parent / "test-fixtures" / "c-vuln-samples"
)


def test_source_files_present():
    expected = {"uaf.c", "oob_read.c", "oob_write.c", "double_free.c",
                "format_string.c", "stack_overflow.c"}
    actual = {p.name for p in (FIXTURE_DIR / "src").glob("*.c")}
    assert expected.issubset(actual), f"missing: {expected - actual}"


def test_makefile_present():
    assert (FIXTURE_DIR / "Makefile").is_file()


def test_readme_present():
    assert (FIXTURE_DIR / "README.md").is_file()


def test_expected_bugs_present():
    assert (FIXTURE_DIR / "expected-bugs.json").is_file()


@pytest.mark.docker
def test_compiles_in_sandbox(docker_available):
    """Build c-vuln-samples inside the mythos-multilang sandbox."""
    if not shutil.which("docker"):
        pytest.skip("docker not on PATH")
    # Run: copy source → build → check binaries exist
    docker_path = "docker"  # absolute path resolved by shutil
    cmd = [
        docker_path, "run", "--rm",
        "-v", f"{FIXTURE_DIR}:/work:ro",
        "--tmpfs", "/work-rw:size=50M,exec",
        "--user", "1000:1000",
        "mythos-multilang:1.0.0",
        "bash", "-c",
        "cp -r /work/* /work-rw/ && cd /work-rw && make 2>&1 | tail -5 && ls bin/",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"build failed: stdout={r.stdout}\nstderr={r.stderr}"
    for expected_bin in ["uaf", "oob_read", "oob_write", "double_free", "format_string", "stack_overflow"]:
        assert expected_bin in r.stdout, f"binary {expected_bin!r} missing from output"
