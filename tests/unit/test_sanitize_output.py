"""Tests for sanitize_output.py."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from sanitize_output import sanitize


def test_strips_ansi_color_codes():
    text = "\x1b[31mERROR\x1b[0m: something bad"
    assert sanitize(text) == "ERROR: something bad"


def test_strips_ansi_cursor_movement():
    text = "\x1b[2J\x1b[H\x1b[1;1Hclean output"
    assert sanitize(text) == "clean output"


def test_preserves_newlines_and_tabs():
    text = "line1\nline2\twith tab"
    assert sanitize(text) == text


def test_strips_other_control_chars():
    text = "before\x07\x08\x0c\x1eafter"  # BEL, BS, FF, RS
    assert sanitize(text) == "beforeafter"


def test_truncates_at_1mb():
    text = "x" * (2 * 1024 * 1024)
    result = sanitize(text)
    assert len(result) <= 1_000_000


def test_custom_truncation_limit():
    text = "x" * 1000
    result = sanitize(text, max_bytes=500)
    assert len(result) <= 500


def test_empty_string_safe():
    assert sanitize("") == ""


def test_returns_string():
    assert isinstance(sanitize("hello"), str)
