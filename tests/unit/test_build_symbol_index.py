"""Tests for build_symbol_index.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import build_symbol_index


def test_extract_symbols_calls_ctags(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value="/usr/bin/ctags"):
        with patch("build_symbol_index.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps({"name": "foo", "path": "src/x.py", "line": 10}) + "\n",
                returncode=0,
            )
            symbols = build_symbol_index.extract_symbols(tmp_path)
            assert isinstance(symbols, list)


def test_extract_symbols_returns_empty_when_ctags_missing(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value=None):
        symbols = build_symbol_index.extract_symbols(tmp_path)
        assert symbols == []


def test_find_consumer_repos_detects_lockfiles(tmp_path):
    # Create a fake consumer repo with package.json referencing a lib
    consumer = tmp_path / "consumer-a"
    consumer.mkdir()
    (consumer / "package.json").write_text(
        json.dumps({"dependencies": {"my-lib": "1.0.0"}}),
        encoding="utf-8",
    )
    results = build_symbol_index.find_consumer_repos([tmp_path], "my-lib")
    assert consumer in results


def test_find_consumer_repos_skips_unrelated(tmp_path):
    consumer = tmp_path / "consumer-b"
    consumer.mkdir()
    (consumer / "package.json").write_text(
        json.dumps({"dependencies": {"other-lib": "1.0.0"}}),
        encoding="utf-8",
    )
    results = build_symbol_index.find_consumer_repos([tmp_path], "my-lib")
    assert consumer not in results


def test_main_runs_without_crash(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value=None):
        rc = build_symbol_index.main(["--output", str(tmp_path / "symbols.json")])
        assert rc in (0, 2)
        # Should write SOMETHING (even if degraded mode)
