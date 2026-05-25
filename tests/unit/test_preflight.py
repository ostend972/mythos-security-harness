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
