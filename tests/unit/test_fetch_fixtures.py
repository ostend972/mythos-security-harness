"""Tests for test-fixtures/fetch_fixtures.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "test-fixtures"))

import fetch_fixtures


class TestListFixtures:
    def test_lists_all_supported_fixtures(self):
        names = fetch_fixtures.list_fixture_names()
        assert "dvwa" in names
        assert "juice-shop" in names
        assert "nodegoat" in names
        assert "webgoat" in names
        assert "vulnado" in names
        assert "c-vuln-samples" in names

    def test_fixture_metadata_has_required_keys(self):
        for name in fetch_fixtures.list_fixture_names():
            meta = fetch_fixtures.FIXTURE_REGISTRY[name]
            assert "language" in meta
            assert "kind" in meta
            assert meta["kind"] in {"external-clone", "internal"}
            if meta["kind"] == "external-clone":
                assert "url" in meta


class TestFetchOne:
    def test_fetch_one_skips_existing_if_no_force(self, tmp_path):
        target = tmp_path / "dvwa"
        target.mkdir()
        (target / "marker").write_text("existing", encoding="utf-8")
        with patch("fetch_fixtures.subprocess.run") as mock_run:
            result = fetch_fixtures.fetch_one("dvwa", base_dir=tmp_path, force=False)
            assert result["status"] == "exists"
            mock_run.assert_not_called()

    def test_fetch_one_clones_external(self, tmp_path):
        with patch("fetch_fixtures.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = fetch_fixtures.fetch_one("dvwa", base_dir=tmp_path, force=False)
            assert result["status"] in {"cloned", "exists"}
            if result["status"] == "cloned":
                # Verify git clone was called
                assert any("clone" in str(c) for c in mock_run.call_args_list)

    def test_internal_fixture_skipped(self, tmp_path):
        result = fetch_fixtures.fetch_one("c-vuln-samples", base_dir=tmp_path, force=False)
        assert result["status"] == "internal-skipped"


class TestMain:
    def test_main_with_list_flag_prints_fixtures(self, capsys):
        rc = fetch_fixtures.main(["--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "dvwa" in out
        assert "juice-shop" in out
