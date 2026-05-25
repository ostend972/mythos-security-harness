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


class TestExplicitStartArgument:
    def test_project_root_accepts_explicit_start(self, tmp_path):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        deep = project / "a" / "b" / "c"
        deep.mkdir(parents=True)
        result = paths.project_root(start=deep)
        assert result == project


class TestMythosSubdirs:
    def test_poc_dir_under_mythos(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.poc_dir() == project / ".mythos" / "poc"

    def test_logs_dir_under_mythos(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.logs_dir() == project / ".mythos" / "logs"

    def test_audit_log_under_mythos(self, tmp_path, monkeypatch):
        project = tmp_path / "myproject"
        (project / ".claude").mkdir(parents=True)
        monkeypatch.chdir(project)
        assert paths.audit_log() == project / ".mythos" / "audit.jsonl"


class TestEnsureDirsVariadic:
    def test_ensure_dirs_creates_multiple(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b" / "c"
        c = tmp_path / "d"
        assert not any(p.exists() for p in (a, b, c))
        paths.ensure_dirs(a, b, c)
        assert a.is_dir() and b.is_dir() and c.is_dir()


class TestSafeWriteBoundary:
    def test_safe_write_path_accepts_base_itself(self, tmp_path):
        # Writing to the base directory itself is permitted (boundary case)
        paths.assert_safe_write(tmp_path, base=tmp_path)
