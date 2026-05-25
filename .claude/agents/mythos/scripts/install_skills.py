"""install_skills.py — audit and copy curated cyber skills into the project.

Steps:
1. Parse allowed-skills.txt (whitelist)
2. For each skill, locate it in the source repo
3. Audit: parse SKILL.md frontmatter, scan body for script tags / prompt
   injection patterns / dangerous URLs
4. If audit passes, copy the entire skill directory to .claude/skills/<name>/
5. Produce a JSON report of installed / rejected / missing skills

Reference: spec §11 T10 (malicious skill threat mitigation).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


# Patterns that disqualify a skill from installation.
DANGEROUS_BODY_PATTERNS = [
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"ignore (previous|all|prior) (instructions|directives)", re.IGNORECASE),
    re.compile(r"exfil(trate)?\s+(tokens?|keys?|credentials?|secrets?)", re.IGNORECASE),
]


def parse_allowlist(path: Path) -> list[str]:
    """Read a one-name-per-line file, skipping blanks and # comments."""
    names = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        names.append(stripped)
    return names


def audit_skill(skill_dir: Path) -> tuple[bool, str | None]:
    """Return (ok, reason). ok=False means do not install."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, "no SKILL.md file"
    content = skill_md.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return False, "missing YAML frontmatter (must start with '---')"
    # Extract body after the second '---' marker
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "malformed frontmatter (no closing '---')"
    body = parts[2]
    for pattern in DANGEROUS_BODY_PATTERNS:
        if pattern.search(body):
            return False, f"body matched dangerous pattern: {pattern.pattern!r}"
    return True, None


def install_all(source_root: Path, dest_root: Path, allowlist_path: Path) -> dict:
    """Audit and copy each allowlisted skill. Return JSON-serializable report."""
    report = {
        "source": str(source_root),
        "dest": str(dest_root),
        "installed": [],
        "rejected": [],
        "missing": [],
    }
    names = parse_allowlist(allowlist_path)
    for name in names:
        src = source_root / name
        if not src.is_dir():
            report["missing"].append(name)
            continue
        ok, reason = audit_skill(src)
        if not ok:
            report["rejected"].append(name)
            continue
        dest = dest_root / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        report["installed"].append(name)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="install_skills")
    p.add_argument(
        "--source",
        default="Anthropic-Cybersecurity-Skills-main/skills",
        help="Source directory containing skill subdirectories",
    )
    p.add_argument(
        "--dest",
        default=".claude/skills",
        help="Destination skills directory",
    )
    p.add_argument(
        "--allowlist",
        default=".claude/agents/mythos/allowed-skills.txt",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.source)
    dest = Path(args.dest)
    allowlist = Path(args.allowlist)
    if not source.is_dir():
        print(f"error: source dir not found: {source}", file=sys.stderr)
        return 2
    if not allowlist.is_file():
        print(f"error: allowlist not found: {allowlist}", file=sys.stderr)
        return 2
    dest.mkdir(parents=True, exist_ok=True)
    report = install_all(source, dest, allowlist)
    print(json.dumps(report, indent=2))
    if report["rejected"] or report["missing"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
