"""Tests for bug-class-mapping.json."""
import json
import sys
from pathlib import Path
import pytest

MAPPING_PATH = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "bug-class-mapping.json"
)


@pytest.fixture(scope="module")
def mapping():
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def test_mapping_is_dict(mapping):
    assert isinstance(mapping, dict)


def test_all_23_classes_present(mapping):
    expected = {
        "sql-injection", "nosql-injection", "command-injection",
        "ssrf", "deserialization", "race-condition",
        "prototype-pollution", "ssti", "type-juggling",
        "jwt-confusion", "idor", "http-smuggling",
        "mass-assignment", "oauth", "websocket",
        "bfla", "data-exposure-api", "heap-corruption",
        "uaf", "oob-rw", "double-free", "format-string",
        "deeplink",
    }
    assert set(mapping.keys()) == expected


def test_every_value_is_string(mapping):
    for class_name, skill in mapping.items():
        assert isinstance(skill, str), f"{class_name} -> {skill!r} not a string"


def test_skills_match_allowlist():
    """Every skill in the mapping should be in allowed-skills.txt."""
    allowlist_path = (
        Path(__file__).parent.parent.parent
        / ".claude" / "agents" / "mythos" / "allowed-skills.txt"
    )
    allowed_skills = set()
    for raw in allowlist_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            allowed_skills.add(s)
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    for class_name, skill in mapping.items():
        assert skill in allowed_skills, (
            f"bug-class {class_name!r} maps to skill {skill!r} "
            f"which is NOT in allowed-skills.txt"
        )
