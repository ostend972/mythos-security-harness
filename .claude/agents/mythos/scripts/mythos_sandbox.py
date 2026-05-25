"""Mythos Preview sandbox CLI and library.

Library usage:
    from mythos_sandbox import run_in_sandbox
    result = run_in_sandbox(poc_dir=Path("..."), run_id="r1", hunter_id="h7", finding_id="F-001")

CLI usage:
    python mythos_sandbox.py run <finding_id>
    python mythos_sandbox.py replay <finding_id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `common` importable when run as a script
HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.docker_runner import RunResult, run_poc_sandboxed
from common.paths import poc_dir as get_poc_dir


def run_in_sandbox(
    poc_dir: Path,
    run_id: str,
    hunter_id: str,
    finding_id: str,
    allow_callback: bool = False,
) -> RunResult:
    """Run a PoC in the sandbox. Thin wrapper over run_poc_sandboxed."""
    return run_poc_sandboxed(
        poc_dir=poc_dir,
        run_id=run_id,
        hunter_id=hunter_id,
        finding_id=finding_id,
        allow_callback=allow_callback,
    )


def cmd_run(args: argparse.Namespace) -> int:
    poc_root = get_poc_dir()
    poc = poc_root / args.finding_id
    if not poc.is_dir():
        print(f"PoC directory not found: {poc}", file=sys.stderr)
        return 2

    result = run_in_sandbox(
        poc_dir=poc,
        run_id=args.run_id or "manual",
        hunter_id=args.hunter_id or "cli",
        finding_id=args.finding_id,
        allow_callback=args.allow_callback,
    )

    print(json.dumps({
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "killed": result.killed,
        "error": result.error,
        "stdout_preview": result.stdout[:500],
        "stderr_preview": result.stderr[:500],
    }, indent=2))
    return 0 if result.exit_code == 0 else 1


def cmd_replay(args: argparse.Namespace) -> int:
    # Replay = same as run, kept distinct for symmetry with Validate's needs
    return cmd_run(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mythos_sandbox")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a PoC in the sandbox")
    p_run.add_argument("finding_id")
    p_run.add_argument("--run-id", default=None)
    p_run.add_argument("--hunter-id", default=None)
    p_run.add_argument("--allow-callback", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_replay = sub.add_parser("replay", help="Replay a previously-saved PoC")
    p_replay.add_argument("finding_id")
    p_replay.add_argument("--run-id", default=None)
    p_replay.add_argument("--hunter-id", default=None)
    p_replay.add_argument("--allow-callback", action="store_true")
    p_replay.set_defaults(func=cmd_replay)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
