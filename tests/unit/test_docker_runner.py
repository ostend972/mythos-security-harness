"""Tests for the Docker runner wrapper."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.docker_runner import build_run_kwargs, RunResult


class TestBuildRunKwargs:
    def test_baseline_kwargs_contain_hardening(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_inline="{}",
        )
        # Hardening flags
        assert kwargs["cap_drop"] == ["ALL"]
        assert kwargs["read_only"] is True
        assert kwargs["user"] == "1000:1000"
        assert kwargs["cgroupns"] == "private"
        assert kwargs["pids_limit"] == 100
        assert kwargs["mem_limit"] == "512m"
        assert kwargs["network_mode"] == "none"
        assert kwargs["remove"] is True
        # security_opt contains no-new-privs and seccomp; NOT apparmor on non-linux
        assert any("no-new-privileges=true" in s for s in kwargs["security_opt"])
        assert any("seccomp=" in s for s in kwargs["security_opt"])
        assert not any("apparmor" in s for s in kwargs["security_opt"])

    def test_apparmor_added_when_supported(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=True,
            seccomp_inline="{}",
        )
        assert any("apparmor=mythos-mythos" in s for s in kwargs["security_opt"])

    def test_callback_mode_uses_isolated_network(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=True,
            apparmor=False,
            seccomp_inline="{}",
        )
        assert kwargs["network_mode"] == "mythos-r1-net"

    def test_volume_mount_is_readonly(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_inline="{}",
        )
        # The volume key may be a daemon-style path (e.g., /mnt/c/... on Windows)
        # — check that the single mounted volume is read-only regardless of key format.
        assert len(kwargs["volumes"]) == 1
        mount_info = next(iter(kwargs["volumes"].values()))
        assert mount_info["mode"] == "ro"
        assert mount_info["bind"] == "/work"

    def test_tmpfs_provides_writable_work_rw(self, tmp_path):
        poc_dir = tmp_path / "poc-F-001"
        poc_dir.mkdir()
        kwargs = build_run_kwargs(
            image="mythos-multilang:1.0.0",
            poc_dir=poc_dir,
            run_id="r1",
            hunter_id="h7",
            finding_id="F-001",
            allow_callback=False,
            apparmor=False,
            seccomp_inline="{}",
        )
        assert "/tmp" in kwargs["tmpfs"]
        assert "/work-rw" in kwargs["tmpfs"]
