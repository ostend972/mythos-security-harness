"""Schema validation tests for dedup-cluster.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("dedup-cluster")


VALID_CLUSTERS = {
    "clusters": [
        {
            "cluster_id": "C-AB1234",
            "root_cause": "Unsafe shell_exec wrapper called from 3 entry points.",
            "primary_finding": "F-AB1234",
            "variant_findings": ["F-CD5678"],
            "highest_severity": "high"
        }
    ],
    "generated_at": "2026-05-25T16:00:00Z"
}


def test_valid_clusters_passes(validator):
    validator.validate(VALID_CLUSTERS)


def test_empty_clusters_passes(validator):
    validator.validate({"clusters": [], "generated_at": "2026-05-25T16:00:00Z"})


def test_short_root_cause_rejected(validator):
    bad = {
        "clusters": [{
            "cluster_id": "C-AB1234",
            "root_cause": "short",
            "primary_finding": "F-AB1234",
            "highest_severity": "high"
        }],
        "generated_at": "2026-05-25T16:00:00Z"
    }
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_cluster_id_rejected(validator):
    bad = dict(VALID_CLUSTERS)
    bad["clusters"] = [{**bad["clusters"][0], "cluster_id": "C-too-short"}]
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
