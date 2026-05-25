"""recall_precision.py — match Mythos findings against expected-bugs.json
and compute recall/precision/F1 metrics.

A match requires:
- Same bug class (exact string match)
- File path: actual.file ENDS WITH expected.file (allows absolute vs relative paths)
- Function name: exact OR expected.function == "n/a"/"various" (loose match)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _is_file_match(actual_file: str, expected_file: str) -> bool:
    """Match if actual ends with expected (handles absolute vs relative paths)."""
    actual = actual_file.replace("\\", "/")
    expected = expected_file.replace("\\", "/")
    if actual == expected:
        return True
    if actual.endswith("/" + expected):
        return True
    if actual.endswith(expected) and expected.startswith("/"):
        return True
    # Also accept the case where expected is a directory prefix (WebGoat lesson packages)
    if expected.endswith("/") and expected.rstrip("/") in actual:
        return True
    return False


def _is_function_match(actual_fn: str, expected_fn: str) -> bool:
    """Match if exact OR expected is a wildcard."""
    if expected_fn in {"n/a", "various", "*"}:
        return True
    return actual_fn == expected_fn


def match_findings(expected: dict, actual: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (matched, unmatched_actual).

    `matched` is a list of dicts with keys "expected" and "actual" for each pair.
    `unmatched_actual` is the list of actual findings that didn't match anything.
    """
    matched: list[dict] = []
    used_expected: set[int] = set()
    used_actual: set[int] = set()

    for i, exp in enumerate(expected["expected_bugs"]):
        for j, act in enumerate(actual):
            if j in used_actual:
                continue
            if act["class"] != exp["class"]:
                continue
            if not _is_file_match(act["file"], exp["file"]):
                continue
            if not _is_function_match(act.get("function", ""), exp.get("function", "")):
                continue
            matched.append({"expected": exp, "actual": act})
            used_expected.add(i)
            used_actual.add(j)
            break

    unmatched_actual = [a for j, a in enumerate(actual) if j not in used_actual]
    return matched, unmatched_actual


def compute_metrics(expected: dict, actual: list[dict]) -> dict:
    """Compute recall, precision, F1, plus target-met booleans."""
    matched, unmatched = match_findings(expected, actual)
    n_expected = len(expected["expected_bugs"])
    n_actual = len(actual)
    n_matched = len(matched)
    recall = n_matched / n_expected if n_expected > 0 else 0.0
    precision = n_matched / n_actual if n_actual > 0 else 1.0  # vacuous
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0.0
    return {
        "fixture": expected.get("fixture"),
        "n_expected": n_expected,
        "n_actual": n_actual,
        "n_matched": n_matched,
        "n_unmatched_actual": len(unmatched),
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "recall_target": expected.get("recall_target", 0.0),
        "precision_target": expected.get("precision_target", 0.0),
        "recall_meets_target": recall >= expected.get("recall_target", 0.0),
        "precision_meets_target": precision >= expected.get("precision_target", 0.0),
    }


def load_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_findings(path: Path) -> list[dict]:
    """Load findings.jsonl into a list."""
    findings = []
    if not path.is_file():
        return findings
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            findings.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return findings
