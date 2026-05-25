"""Tests for cross-platform path helpers."""
import os
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common import paths


class TestProjectRoot:
    def test_project_root_returns_directory_containing_dotclaude(self, tmp_path, monkeypatch):
        # Arrange: simulate a project with .claude/
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        (project / "src").mkdir()
        monkeypatch.chdir(project / "src")
        # Act
        result = paths.project_root()
        # Assert
        assert result == project

    def test_project_root_raises_when_no_dotclaude(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(paths.ProjectRootNotFound):
            paths.project_root()


class TestMythosDir:
    def test_mythos_dir_is_under_project_root(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.mythos_dir() == project / ".mythos"

    def test_state_dir_under_mythos(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.state_dir() == project / ".mythos" / "state"


class TestEnsureDirs:
    def test_ensure_dirs_creates_missing(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        assert not target.exists()
        paths.ensure_dirs(target)
        assert target.is_dir()

    def test_ensure_dirs_idempotent(self, tmp_path):
        target = tmp_path / "a"
        paths.ensure_dirs(target)
        paths.ensure_dirs(target)  # should not raise
        assert target.is_dir()


class TestSafeWritePath:
    def test_safe_write_path_rejects_traversal(self, tmp_path):
        with pytest.raises(paths.UnsafePathError):
            paths.assert_safe_write(tmp_path / ".." / "evil.txt", base=tmp_path)

    def test_safe_write_path_rejects_absolute_outside(self, tmp_path):
        outside = Path("/etc/passwd") if os.name != "nt" else Path("C:/Windows/System32/evil.txt")
        with pytest.raises(paths.UnsafePathError):
            paths.assert_safe_write(outside, base=tmp_path)

    def test_safe_write_path_accepts_inside(self, tmp_path):
        good = tmp_path / "subdir" / "file.txt"
        # Should not raise
        paths.assert_safe_write(good, base=tmp_path)
