"""Validate that every bug-class .md has a consistent frontmatter."""
import json
import re
from pathlib import Path
import pytest
import yaml


BUG_CLASSES_DIR = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "bug-classes"
)
MAPPING_PATH = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "bug-class-mapping.json"
)


def _bug_class_files() -> list[Path]:
    return sorted(BUG_CLASSES_DIR.glob("*.md"))


def _frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{path.name}: must start with ---"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{path.name}: malformed frontmatter"
    return yaml.safe_load(parts[1]) or {}


def test_all_23_classes_present():
    classes = {p.stem for p in _bug_class_files()}
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
    assert classes == expected


@pytest.mark.parametrize("path", _bug_class_files(), ids=lambda p: p.name)
def test_required_frontmatter_keys(path):
    fm = _frontmatter(path)
    for key in ["class_id", "name", "applicable_languages", "severity_default",
                "fp_rate_expected", "skill"]:
        assert key in fm, f"{path.name}: missing frontmatter key '{key}'"


@pytest.mark.parametrize("path", _bug_class_files(), ids=lambda p: p.name)
def test_class_id_matches_filename(path):
    fm = _frontmatter(path)
    assert fm["class_id"] == path.stem, (
        f"{path.name}: class_id '{fm['class_id']}' != filename stem '{path.stem}'"
    )


@pytest.mark.parametrize("path", _bug_class_files(), ids=lambda p: p.name)
def test_severity_is_valid_enum(path):
    fm = _frontmatter(path)
    assert fm["severity_default"] in {"critical", "high", "medium", "low", "info"}


@pytest.mark.parametrize("path", _bug_class_files(), ids=lambda p: p.name)
def test_fp_rate_is_in_range(path):
    fm = _frontmatter(path)
    rate = fm["fp_rate_expected"]
    assert isinstance(rate, (int, float)), f"{path.name}: fp_rate must be numeric"
    assert 0.0 <= rate <= 1.0, f"{path.name}: fp_rate {rate} not in [0,1]"


def test_every_class_in_mapping():
    """Every bug-class .md must have an entry in bug-class-mapping.json."""
    classes = {p.stem for p in _bug_class_files()}
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    missing = classes - set(mapping.keys())
    assert not missing, f"classes missing from mapping: {missing}"


def test_every_skill_in_mapping_matches_class_frontmatter():
    """The 'skill' frontmatter of each class must equal its mapping entry."""
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    for path in _bug_class_files():
        fm = _frontmatter(path)
        expected_skill = mapping[path.stem]
        assert fm["skill"] == expected_skill, (
            f"{path.name}: frontmatter skill='{fm['skill']}' "
            f"!= mapping value='{expected_skill}'"
        )
