"""Schema validation tests for report.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("report")


VALID_REPORT = {
    "run_id": "2026-05-25T13:00:00Z",
    "version": "1.0.0",
    "target_path": "/path/to/target",
    "generated_at": "2026-05-25T18:00:00Z",
    "clusters": [
        {
            "cluster_id": "C-AB1234",
            "severity": "high",
            "reachable": True,
            "primary_finding": "F-AB1234",
            "poc_path": "poc/F-AB1234/",
            "summary": "Command injection via update_profile."
        }
    ],
    "metrics": {"duration_minutes": 78, "tasks_completed": 305}
}


def test_valid_report_passes(validator):
    validator.validate(VALID_REPORT)


def test_invalid_version_format_rejected(validator):
    bad = {**VALID_REPORT, "version": "1.0"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_empty_clusters_passes(validator):
    empty = {**VALID_REPORT, "clusters": []}
    validator.validate(empty)
