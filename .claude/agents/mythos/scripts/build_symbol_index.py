"""build_symbol_index.py — build a cross-repo symbol index for the Trace phase.

Uses universal-ctags (preferred) or ripgrep fallback. Outputs symbols.json
that maps each vulnerable symbol to its call sites in consumer repos.

Degrades gracefully when ctags/rg are missing — Trace phase falls back to
best-effort with an explicit warning.

Reference: spec §11 T19 (symbol index poisoning mitigations).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


# Lockfile name → key path within parsed JSON/TOML/etc that lists deps
LOCKFILE_SCAN: dict[str, list[str]] = {
    "package.json": ["dependencies", "devDependencies"],
    "Cargo.toml": ["dependencies"],
    "requirements.txt": [],  # parsed line-by-line
    "go.mod": [],  # parsed differently
    "Gemfile": [],
    "pom.xml": [],
    "composer.json": ["require", "require-dev"],
}


def extract_symbols(repo: Path) -> list[dict]:
    """Run ctags on `repo` and return list of symbol dicts.

    If ctags isn't available, return [].
    """
    ctags = shutil.which("ctags")
    if not ctags:
        return []
    try:
        r = subprocess.run(
            [ctags, "-R", "--output-format=json", "--fields=+n", "-f", "-", str(repo)],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    symbols = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        try:
            symbols.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return symbols


def find_consumer_repos(search_roots: Iterable[Path], lib_name: str) -> list[Path]:
    """Return repos under search_roots that reference `lib_name` in a known lockfile."""
    results = []
    for root in search_roots:
        if not root.is_dir():
            continue
        for lockname in LOCKFILE_SCAN:
            for path in root.rglob(lockname):
                if "node_modules" in path.parts or ".git" in path.parts:
                    continue
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if lib_name in content:
                    results.append(path.parent)
                    break
    return list(set(results))


def find_call_sites(repo: Path, symbol: str) -> list[dict]:
    """Use ripgrep to find call sites of a symbol in a repo."""
    rg = shutil.which("rg")
    if not rg:
        return []
    try:
        r = subprocess.run(
            [rg, "--json", "--no-heading", "-w", symbol, str(repo)],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    sites = []
    for line in r.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "match":
            d = obj.get("data", {})
            sites.append({
                "file": d.get("path", {}).get("text", ""),
                "line": d.get("line_number"),
                "text": d.get("lines", {}).get("text", "").strip()[:200],
            })
    return sites


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="build_symbol_index")
    p.add_argument("--output", default=".mythos/symbols.json", help="Output JSON path")
    p.add_argument("--target", default=".", help="Repo to index (for own symbols)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.target).resolve()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    symbols = extract_symbols(target)
    index = {
        "target": str(target),
        "ctags_available": shutil.which("ctags") is not None,
        "rg_available": shutil.which("rg") is not None,
        "symbols": symbols,
        "note": "Cross-repo consumer lookup is done lazily by mythos-trace per cluster.",
    }
    output.write_text(json.dumps(index, indent=2), encoding="utf-8")
    if not (shutil.which("ctags") and shutil.which("rg")):
        print(
            "warning: ctags and/or ripgrep not on PATH — symbol index is degraded",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
