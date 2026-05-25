"""Tests for e2e_runner.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import e2e_runner


def test_dry_run_does_not_invoke_mythos(tmp_path):
    """Dry-run mode prints what would happen but doesn't call /mythos."""
    with patch("e2e_runner.subprocess.run") as mock_run:
        rc = e2e_runner.main([
            "--fixture", "c-vuln-samples",
            "--dry-run",
        ])
        assert rc == 0
        # No subprocess invocations
        mock_run.assert_not_called()


def test_unknown_fixture_returns_2():
    rc = e2e_runner.main(["--fixture", "nonexistent-fixture", "--dry-run"])
    assert rc == 2


def test_resolves_expected_bugs_paths():
    """The runner finds expected-bugs.json for known fixtures."""
    # c-vuln-samples has expected-bugs.json inside its own dir
    p = e2e_runner.locate_expected_bugs("c-vuln-samples")
    assert p is not None
    assert p.name == "expected-bugs.json"

    # dvwa has it in test-fixtures/expected/
    p = e2e_runner.locate_expected_bugs("dvwa")
    assert p is not None
    assert "dvwa-expected-bugs.json" == p.name
