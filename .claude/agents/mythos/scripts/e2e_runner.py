"""e2e_runner.py — run /mythos against a fixture and measure outcomes.

Workflow:
1. Verify the fixture exists (and skip if it requires external clone but isn't present).
2. (Optional) Run `claude --skill mythos start <fixture>` to execute the pipeline.
   This is long (potentially hours). Use --dry-run to skip.
3. After the run, read .mythos/validated.jsonl (or the cluster-flattened equivalent)
   and compare against expected-bugs.json via recall_precision.
4. Print a structured report and exit 0 if recall + precision both meet targets,
   1 otherwise.

Typical invocation:
    # Dry-run (CI-friendly, no Claude calls):
    python .claude/agents/mythos/scripts/e2e_runner.py --fixture c-vuln-samples --dry-run

    # Real run (long, real Claude API/CLI):
    python .claude/agents/mythos/scripts/e2e_runner.py --fixture c-vuln-samples --run

    # Measure-only (assumes /mythos already ran):
    python .claude/agents/mythos/scripts/e2e_runner.py --fixture c-vuln-samples --measure
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from recall_precision import compute_metrics, load_expected, load_findings


REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
FIXTURES_DIR = REPO_ROOT / "test-fixtures"


KNOWN_FIXTURES = {
    "c-vuln-samples", "dvwa", "juice-shop", "nodegoat", "webgoat", "vulnado",
}


def locate_expected_bugs(fixture: str) -> Path | None:
    """Find expected-bugs.json for the given fixture."""
    # Internal fixture has its own folder
    inside = FIXTURES_DIR / fixture / "expected-bugs.json"
    if inside.is_file():
        return inside
    # External fixtures' expected files live in test-fixtures/expected/
    external = FIXTURES_DIR / "expected" / f"{fixture}-expected-bugs.json"
    if external.is_file():
        return external
    return None


def fixture_dir(fixture: str) -> Path:
    return FIXTURES_DIR / fixture


def run_mythos(fixture: str, *, timeout_s: int = 14_400) -> int:
    """Run `/mythos start <fixture_path>` via claude CLI. Long-running."""
    target = fixture_dir(fixture)
    if not target.is_dir():
        print(f"error: fixture directory not found: {target}", file=sys.stderr)
        return 2
    cmd = ["claude", "-p", f"/mythos start {target}"]
    try:
        r = subprocess.run(cmd, cwd=REPO_ROOT, timeout=timeout_s)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 124
    except FileNotFoundError:
        print("error: claude CLI not on PATH", file=sys.stderr)
        return 127


def measure(fixture: str) -> dict:
    """Read .mythos/validated.jsonl + expected-bugs.json and compute metrics."""
    expected_path = locate_expected_bugs(fixture)
    if expected_path is None:
        return {"error": f"expected-bugs.json not found for {fixture}"}
    expected = load_expected(expected_path)
    # Findings live at .mythos/findings.jsonl (raw) or validated.jsonl (post-validate)
    findings_path = REPO_ROOT / ".mythos" / "validated.jsonl"
    if not findings_path.is_file():
        findings_path = REPO_ROOT / ".mythos" / "findings.jsonl"
    if not findings_path.is_file():
        return {"error": "no findings.jsonl or validated.jsonl present"}
    actual = load_findings(findings_path)
    return compute_metrics(expected, actual)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="e2e_runner")
    p.add_argument("--fixture", required=True, help="Fixture name")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--run", action="store_true", help="Execute /mythos start (long)")
    g.add_argument("--measure", action="store_true", help="Only measure (assumes prior run)")
    g.add_argument("--dry-run", action="store_true", help="Print plan, do nothing")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fixture not in KNOWN_FIXTURES:
        print(f"error: unknown fixture {args.fixture!r}", file=sys.stderr)
        return 2

    expected = locate_expected_bugs(args.fixture)
    if expected is None:
        print(f"error: no expected-bugs.json for {args.fixture}", file=sys.stderr)
        return 2

    fixture_path = fixture_dir(args.fixture)

    if args.dry_run:
        print(json.dumps({
            "action": "dry-run",
            "fixture": args.fixture,
            "fixture_path": str(fixture_path),
            "fixture_exists": fixture_path.is_dir(),
            "expected_bugs_path": str(expected),
            "would_invoke": f"claude -p '/mythos start {fixture_path}'",
            "would_measure": "yes",
        }, indent=2))
        return 0

    if args.run:
        if not fixture_path.is_dir():
            print(f"error: fixture not fetched. Run fetch_fixtures.py first.", file=sys.stderr)
            return 2
        rc = run_mythos(args.fixture)
        if rc != 0:
            print(f"warning: /mythos exited non-zero ({rc})", file=sys.stderr)
        # Fall through to measure

    metrics = measure(args.fixture)
    print(json.dumps(metrics, indent=2))
    if metrics.get("error"):
        return 2
    if metrics["recall_meets_target"] and metrics["precision_meets_target"]:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
