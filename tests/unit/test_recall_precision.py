"""Tests for recall_precision.py."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import recall_precision


SAMPLE_EXPECTED = {
    "fixture": "test-fixture",
    "language": "c",
    "expected_bugs": [
        {"file": "src/a.c", "function": "main", "class": "uaf", "severity": "critical"},
        {"file": "src/b.c", "function": "process", "class": "oob-rw", "severity": "high"},
        {"file": "src/c.c", "function": "handler", "class": "double-free", "severity": "high"},
    ],
    "recall_target": 0.7,
    "precision_target": 0.7,
}


def make_finding(file: str, function: str, cls: str) -> dict:
    return {
        "finding_id": "F-TEST1",
        "task_id": "T-T1",
        "class": cls,
        "file": file,
        "line": 1,
        "function": function,
        "severity": "high",
        "hypothesis": "test hypothesis",
        "poc_dir": "poc/F-TEST1/",
        "poc_log": "ok",
        "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-01",
        "confidence": "poc-confirmed",
        "created_at": "2026-05-25T00:00:00Z",
    }


class TestMatchFindings:
    def test_exact_match_counted(self):
        actual = [make_finding("src/a.c", "main", "uaf")]
        matched, unmatched = recall_precision.match_findings(SAMPLE_EXPECTED, actual)
        assert len(matched) == 1
        assert matched[0]["expected"]["file"] == "src/a.c"

    def test_unmatched_actual_is_potential_fp(self):
        actual = [make_finding("src/x.c", "fn", "uaf")]
        matched, unmatched = recall_precision.match_findings(SAMPLE_EXPECTED, actual)
        assert len(matched) == 0
        assert len(unmatched) == 1

    def test_wrong_class_does_not_match(self):
        actual = [make_finding("src/a.c", "main", "sql-injection")]
        matched, _ = recall_precision.match_findings(SAMPLE_EXPECTED, actual)
        assert len(matched) == 0

    def test_partial_file_path_match(self):
        """Match if the actual.file ENDS WITH the expected.file path."""
        actual = [make_finding("/absolute/path/to/src/a.c", "main", "uaf")]
        matched, _ = recall_precision.match_findings(SAMPLE_EXPECTED, actual)
        assert len(matched) == 1


class TestComputeMetrics:
    def test_perfect_recall_perfect_precision(self):
        actual = [
            make_finding("src/a.c", "main", "uaf"),
            make_finding("src/b.c", "process", "oob-rw"),
            make_finding("src/c.c", "handler", "double-free"),
        ]
        m = recall_precision.compute_metrics(SAMPLE_EXPECTED, actual)
        assert m["recall"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall_meets_target"]
        assert m["precision_meets_target"]

    def test_partial_recall(self):
        actual = [make_finding("src/a.c", "main", "uaf")]
        m = recall_precision.compute_metrics(SAMPLE_EXPECTED, actual)
        assert m["recall"] == pytest.approx(1 / 3)
        assert m["precision"] == 1.0

    def test_zero_findings(self):
        m = recall_precision.compute_metrics(SAMPLE_EXPECTED, [])
        assert m["recall"] == 0.0
        # precision undefined → reported as 1.0 (vacuous)
        assert m["precision"] == 1.0
        assert not m["recall_meets_target"]

    def test_target_thresholds_respected(self):
        # 2/3 ≈ 0.667 < 0.7 target
        actual = [
            make_finding("src/a.c", "main", "uaf"),
            make_finding("src/b.c", "process", "oob-rw"),
        ]
        m = recall_precision.compute_metrics(SAMPLE_EXPECTED, actual)
        assert m["recall"] == pytest.approx(2 / 3)
        assert not m["recall_meets_target"]
