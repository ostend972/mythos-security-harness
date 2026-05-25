"""Schema validation tests for task.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("task")


VALID_TASK = {
    "task_id": "T-ABCD",
    "class": "sql-injection",
    "scope": "src/db.py:get_user",
    "subsystem": "persistence",
    "trust_boundary": "HTTP request",
    "priority": 1,
    "status": "pending",
}


def test_valid_task_passes(validator):
    validator.validate(VALID_TASK)


def test_priority_out_of_range_rejected(validator):
    for bad_priority in [0, 6, -1, 100]:
        bad = {**VALID_TASK, "priority": bad_priority}
        with pytest.raises(SchemaValidationError):
            validator.validate(bad)


def test_unknown_status_rejected(validator):
    bad = {**VALID_TASK, "status": "running"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_source_field_optional(validator):
    with_source = {**VALID_TASK, "source": "gapfill"}
    validator.validate(with_source)


def test_invalid_source_rejected(validator):
    bad = {**VALID_TASK, "source": "manual"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
