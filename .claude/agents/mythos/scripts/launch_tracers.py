"""launch_tracers.py — spawn one `claude --agent mythos-tracer` per
(cluster, consumer_repo) pair in parallel.

Inputs:
- .mythos/dedup-clusters.json
- .mythos/symbols.json

Outputs:
- One trace.json per (cluster, repo) in .mythos/traces/

Same pattern as launch_hunters.py but with different dispatch logic.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def build_tracer_prompt(cluster: dict, consumer_repo: str, symbols: dict) -> str:
    return (
        f"You are tracing reachability of a Mythos cluster.\n\n"
        f"Cluster:\n{json.dumps(cluster, indent=2)}\n\n"
        f"Consumer repo: {consumer_repo}\n\n"
        f"Symbol index excerpt:\n{json.dumps(symbols.get('symbols', [])[:50], indent=2)}\n"
    )


def spawn_one_tracer(cluster: dict, consumer_repo: str, symbols: dict, work_dir: Path) -> dict:
    cluster_id = cluster.get("cluster_id", "C-unknown")
    start = time.monotonic()
    try:
        p = subprocess.run(
            ["claude", "--agent", "mythos-tracer", "-p",
             build_tracer_prompt(cluster, consumer_repo, symbols)],
            cwd=work_dir, capture_output=True, text=True, timeout=300,
        )
        return {
            "cluster_id": cluster_id, "consumer_repo": consumer_repo,
            "exit_code": p.returncode, "duration_s": time.monotonic() - start,
            "status": "completed" if p.returncode == 0 else "failed",
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {
            "cluster_id": cluster_id, "consumer_repo": consumer_repo,
            "exit_code": -1, "duration_s": time.monotonic() - start,
            "status": "failed", "error": str(e),
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="launch_tracers")
    p.add_argument("--clusters", default=".mythos/dedup-clusters.json")
    p.add_argument("--symbols", default=".mythos/symbols.json")
    p.add_argument("--consumers", nargs="*", default=[],
                   help="List of consumer repo paths to trace against")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    clusters_path = Path(args.clusters)
    symbols_path = Path(args.symbols)
    if not clusters_path.is_file() or not symbols_path.is_file():
        print(f"missing clusters or symbols input", file=sys.stderr)
        return 2
    clusters_doc = json.loads(clusters_path.read_text(encoding="utf-8"))
    symbols_doc = json.loads(symbols_path.read_text(encoding="utf-8"))
    pairs = []
    for cluster in clusters_doc.get("clusters", []):
        for repo in args.consumers:
            pairs.append((cluster, repo))

    if not pairs:
        print("no cluster/consumer pairs to trace")
        return 0

    print(f"dispatching {len(pairs)} tracers")
    if args.dry_run:
        for c, r in pairs:
            print(f"  would trace: cluster={c.get('cluster_id')} consumer={r}")
        return 0

    work_dir = Path.cwd()
    outcomes = []
    with ThreadPoolExecutor(max_workers=min(len(pairs), 20)) as pool:
        futures = [
            pool.submit(spawn_one_tracer, c, r, symbols_doc, work_dir)
            for c, r in pairs
        ]
        for fut in as_completed(futures):
            outcomes.append(fut.result())

    completed = sum(1 for o in outcomes if o.get("status") == "completed")
    failed = sum(1 for o in outcomes if o.get("status") == "failed")
    print(f"trace done: {completed} completed, {failed} failed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
