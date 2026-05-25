"""Schema validation tests for trace.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("trace")


VALID_TRACE = {
    "cluster_id": "C-AB1234",
    "consumer_repo": "/path/to/consumer-a",
    "reachable": True,
    "entry_points": ["POST /api/users/:id"],
    "call_chain": ["handler -> service -> lib_call"],
    "constraints": ["requires auth"],
    "confidence": "high",
    "traced_at": "2026-05-25T17:00:00Z"
}


def test_valid_trace_passes(validator):
    validator.validate(VALID_TRACE)


def test_unreachable_trace_passes(validator):
    unreachable = {**VALID_TRACE, "reachable": False, "entry_points": [], "call_chain": []}
    validator.validate(unreachable)


def test_invalid_confidence_rejected(validator):
    bad = {**VALID_TRACE, "confidence": "absolute"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
