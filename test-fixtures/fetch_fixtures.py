"""fetch_fixtures.py — clone or set up vulnerable application fixtures.

External fixtures live at known upstream repos and are fetched on demand.
Internal fixtures (like c-vuln-samples) ship with this repo — they're skipped.

Usage:
    python test-fixtures/fetch_fixtures.py --list
    python test-fixtures/fetch_fixtures.py --fetch dvwa juice-shop
    python test-fixtures/fetch_fixtures.py --all
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


FIXTURE_REGISTRY: dict[str, dict] = {
    "dvwa": {
        "kind": "external-clone",
        "url": "https://github.com/digininja/DVWA.git",
        "language": "php",
        "framework": "raw-php",
        "size_mb": 5,
    },
    "juice-shop": {
        "kind": "external-clone",
        "url": "https://github.com/juice-shop/juice-shop.git",
        "language": "typescript",
        "framework": "express",
        "size_mb": 200,
        "branch": "master",
    },
    "nodegoat": {
        "kind": "external-clone",
        "url": "https://github.com/OWASP/NodeGoat.git",
        "language": "javascript",
        "framework": "express",
        "size_mb": 30,
    },
    "webgoat": {
        "kind": "external-clone",
        "url": "https://github.com/WebGoat/WebGoat.git",
        "language": "java",
        "framework": "spring-boot",
        "size_mb": 80,
    },
    "vulnado": {
        "kind": "external-clone",
        "url": "https://github.com/ScaleSec/vulnado.git",
        "language": "java",
        "framework": "spring-boot",
        "size_mb": 15,
    },
    "c-vuln-samples": {
        "kind": "internal",
        "language": "c",
        "framework": None,
        "size_mb": 0.1,
    },
}


def list_fixture_names() -> list[str]:
    return list(FIXTURE_REGISTRY.keys())


def fetch_one(name: str, *, base_dir: Path, force: bool = False) -> dict:
    """Fetch a single fixture. Return outcome dict."""
    if name not in FIXTURE_REGISTRY:
        return {"name": name, "status": "unknown"}
    meta = FIXTURE_REGISTRY[name]
    if meta["kind"] == "internal":
        return {"name": name, "status": "internal-skipped"}
    target = base_dir / name
    if target.exists() and not force:
        return {"name": name, "status": "exists", "path": str(target)}
    if target.exists() and force:
        shutil.rmtree(target)
    base_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if meta.get("branch"):
        cmd += ["--branch", meta["branch"]]
    cmd += [meta["url"], str(target)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "timeout"}
    except FileNotFoundError:
        return {"name": name, "status": "git-not-found"}
    if r.returncode != 0:
        return {"name": name, "status": "clone-failed", "error": r.stderr[-500:]}
    return {"name": name, "status": "cloned", "path": str(target)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="fetch_fixtures")
    p.add_argument("--list", action="store_true", help="List available fixtures")
    p.add_argument("--fetch", nargs="*", default=[], help="Fixture names to fetch")
    p.add_argument("--all", action="store_true", help="Fetch all external fixtures")
    p.add_argument("--force", action="store_true", help="Re-clone even if exists")
    p.add_argument("--base-dir", default="test-fixtures", help="Base directory")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        print("Available fixtures:")
        for name, meta in FIXTURE_REGISTRY.items():
            kind = meta["kind"]
            lang = meta["language"]
            size = meta.get("size_mb", "?")
            print(f"  - {name:<18} [{kind:<14}] {lang:<10} ({size} MB)")
        return 0

    base_dir = Path(args.base_dir)
    names_to_fetch: list[str] = list(args.fetch)
    if args.all:
        names_to_fetch = [n for n, m in FIXTURE_REGISTRY.items() if m["kind"] == "external-clone"]
    if not names_to_fetch:
        print("No fixtures specified. Use --list, --fetch <name>, or --all.")
        return 2

    overall_ok = True
    for name in names_to_fetch:
        result = fetch_one(name, base_dir=base_dir, force=args.force)
        print(json.dumps(result))
        if result["status"] in ("clone-failed", "timeout", "git-not-found", "unknown"):
            overall_ok = False
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
