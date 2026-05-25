"""Tests for platform detection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common import platform_utils


def test_is_linux_returns_bool():
    assert isinstance(platform_utils.is_linux_host(), bool)


def test_is_windows_returns_bool():
    assert isinstance(platform_utils.is_windows_host(), bool)


def test_is_macos_returns_bool():
    assert isinstance(platform_utils.is_macos_host(), bool)


def test_exactly_one_os_is_true():
    flags = [
        platform_utils.is_linux_host(),
        platform_utils.is_windows_host(),
        platform_utils.is_macos_host(),
    ]
    assert sum(flags) == 1, f"Expected exactly one OS flag, got {flags}"


def test_apparmor_supported_only_on_linux():
    if platform_utils.is_linux_host():
        assert isinstance(platform_utils.apparmor_supported(), bool)
    else:
        assert platform_utils.apparmor_supported() is False
