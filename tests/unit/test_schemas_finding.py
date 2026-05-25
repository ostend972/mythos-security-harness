"""Schema validation tests for finding.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("finding")


VALID_FINDING = {
    "finding_id": "F-ABC123",
    "task_id": "T-XY12",
    "class": "sql-injection",
    "file": "src/db.py",
    "line": 42,
    "function": "get_user",
    "severity": "high",
    "hypothesis": "User input concatenated into SQL query without parameterization.",
    "poc_dir": "poc/F-ABC123/",
    "poc_log": "Query returned admin row when injection payload sent.",
    "docker_image": "mythos-multilang:1.0.0",
    "hunter_id": "hunter-07",
    "confidence": "poc-confirmed",
    "created_at": "2026-05-25T14:00:00Z",
}


def test_valid_finding_passes(validator):
    validator.validate(VALID_FINDING)


def test_missing_finding_id_rejected(validator):
    bad = {k: v for k, v in VALID_FINDING.items() if k != "finding_id"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_finding_id_pattern_rejected(validator):
    bad = {**VALID_FINDING, "finding_id": "bad-id"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_unknown_class_rejected(validator):
    bad = {**VALID_FINDING, "class": "made-up-class"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_extra_property_rejected(validator):
    bad = {**VALID_FINDING, "extra_field": "no thanks"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_confidence_must_be_poc_confirmed(validator):
    """Schema-level enforcement of strict 'no PoC = drop' policy."""
    for bad_value in ["suspected", "theoretical", "high", "low"]:
        bad = {**VALID_FINDING, "confidence": bad_value}
        with pytest.raises(SchemaValidationError):
            validator.validate(bad)


def test_invalid_created_at_format_rejected(validator):
    bad = {**VALID_FINDING, "created_at": "not-a-date"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_chain_field_optional(validator):
    with_chain = {**VALID_FINDING, "chain": ["F-PRIM01", "F-PRIM02"]}
    validator.validate(with_chain)


def test_invalid_chain_member_rejected(validator):
    bad = {**VALID_FINDING, "chain": ["not-a-finding-id"]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
