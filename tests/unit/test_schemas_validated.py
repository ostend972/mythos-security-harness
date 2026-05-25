"""Schema validation tests for validated.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("validated")


VALID_KEEP = {
    "finding_id": "F-AB1234",
    "verdict": "keep",
    "validator_notes": "Independent PoC reproduced the bug.",
    "independent_poc_path": ".mythos/validate-pocs/V-F-AB1234/",
    "replayed_hunter_poc": True,
    "validated_at": "2026-05-25T15:00:00Z",
}

VALID_DROP = {
    "finding_id": "F-AB1234",
    "verdict": "drop",
    "validator_notes": "PoC did not reproduce; spec hypothesis was incorrect.",
    "drop_reason": "PoC failed to trigger the bug independently.",
    "validated_at": "2026-05-25T15:00:00Z",
}


def test_valid_keep_passes(validator):
    validator.validate(VALID_KEEP)


def test_valid_drop_passes(validator):
    validator.validate(VALID_DROP)


def test_unknown_verdict_rejected(validator):
    bad = {**VALID_KEEP, "verdict": "maybe"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_missing_required_rejected(validator):
    bad = {k: v for k, v in VALID_KEEP.items() if k != "verdict"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
