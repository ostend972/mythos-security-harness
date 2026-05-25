"""Schema validation tests for run.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("run")


VALID_RUN = {
    "run_id": "2026-05-25T13:00:00Z",
    "version": "1.0.0",
    "target_path": "/path/to/target",
    "started_at": "2026-05-25T13:00:00Z",
    "current_phase": "hunt"
}


def test_valid_run_passes(validator):
    validator.validate(VALID_RUN)


def test_invalid_phase_rejected(validator):
    bad = {**VALID_RUN, "current_phase": "scanning"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_hash_chain_rejected(validator):
    bad = {**VALID_RUN, "hash_chain": "not-a-hash"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_valid_hash_chain_accepted(validator):
    ok = {**VALID_RUN, "hash_chain": "sha256:" + "a" * 64}
    validator.validate(ok)
