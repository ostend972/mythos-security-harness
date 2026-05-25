"""Validate the structure of every expected-bugs.json fixture."""
import json
from pathlib import Path
import pytest


EXPECTED_DIR = Path(__file__).parent.parent.parent / "test-fixtures" / "expected"
INTERNAL_DIR = Path(__file__).parent.parent.parent / "test-fixtures" / "c-vuln-samples"
MAPPING_PATH = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "bug-class-mapping.json"
)


def _expected_files() -> list[Path]:
    files = sorted(EXPECTED_DIR.glob("*-expected-bugs.json"))
    # Also include the internal fixture's own expected-bugs.json
    internal = INTERNAL_DIR / "expected-bugs.json"
    if internal.is_file():
        files.append(internal)
    return files


REQUIRED_FIXTURES = {
    "c-vuln-samples", "dvwa", "juice-shop", "nodegoat", "webgoat", "vulnado",
}


def test_all_6_fixtures_have_expected_bugs():
    fixtures = set()
    for f in EXPECTED_DIR.glob("*-expected-bugs.json"):
        # Strip "-expected-bugs.json" suffix
        fixtures.add(f.name.replace("-expected-bugs.json", ""))
    # c-vuln-samples lives in its own directory
    if (INTERNAL_DIR / "expected-bugs.json").is_file():
        fixtures.add("c-vuln-samples")
    assert REQUIRED_FIXTURES.issubset(fixtures), (
        f"missing expected-bugs.json for: {REQUIRED_FIXTURES - fixtures}"
    )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_expected_bugs_has_required_keys(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ["fixture", "language", "expected_bugs", "recall_target", "precision_target"]:
        assert key in data, f"{path.name}: missing key '{key}'"


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_expected_bugs_classes_are_valid(path):
    """Every bug class must exist in bug-class-mapping.json."""
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    valid_classes = set(mapping.keys())
    data = json.loads(path.read_text(encoding="utf-8"))
    for bug in data["expected_bugs"]:
        assert bug["class"] in valid_classes, (
            f"{path.name}: bug class {bug['class']!r} not in bug-class-mapping.json"
        )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_severity_values_valid(path):
    valid = {"critical", "high", "medium", "low", "info"}
    data = json.loads(path.read_text(encoding="utf-8"))
    for bug in data["expected_bugs"]:
        assert bug["severity"] in valid, (
            f"{path.name}: bug severity {bug['severity']!r} not valid"
        )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_recall_target_in_range(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    target = data["recall_target"]
    assert 0.0 <= target <= 1.0


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_precision_target_in_range(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    target = data["precision_target"]
    assert 0.0 <= target <= 1.0


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_at_least_5_bugs_per_fixture(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    n = len(data["expected_bugs"])
    assert n >= 5, f"{path.name}: only {n} bugs; need ≥ 5 for meaningful recall measurement"
