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
