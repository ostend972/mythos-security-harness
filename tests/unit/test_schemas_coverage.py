"""Schema validation tests for coverage.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("coverage")


VALID_COVERAGE = {
    "hunter_id": "hunter-07",
    "task_id": "T-A1B2",
    "task_class": "command-injection",
    "task_scope": "src/api/users.py:update_profile",
    "files_read": ["src/api/users.py", "src/utils/shell.py"],
    "functions_analyzed": ["update_profile", "run_shell"],
    "classes_evaluated": ["command-injection"],
    "partial_coverage": [
        {"location": "src/api/users.py:delete_account", "reason": "not analyzed for race"}
    ],
    "findings_produced": ["F-AB1234"],
    "iterations_used": 3,
    "verdict": "completed",
}


def test_valid_coverage_passes(validator):
    validator.validate(VALID_COVERAGE)


def test_partial_coverage_missing_reason_rejected(validator):
    bad = {**VALID_COVERAGE,
           "partial_coverage": [{"location": "src/x.py:foo"}]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_partial_coverage_extra_field_rejected(validator):
    bad = {**VALID_COVERAGE,
           "partial_coverage": [{"location": "x", "reason": "y", "extra": "z"}]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_verdict_rejected(validator):
    bad = {**VALID_COVERAGE, "verdict": "success"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
