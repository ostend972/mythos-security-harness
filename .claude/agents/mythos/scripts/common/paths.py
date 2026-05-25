"""Cross-platform path helpers for Mythos Preview.

Resolves project root (directory containing .claude/), state dirs,
and validates paths to prevent traversal attacks.
"""
from __future__ import annotations

from pathlib import Path


class ProjectRootNotFound(RuntimeError):
    """Raised when no .claude/ directory is found in cwd or any parent."""


class UnsafePathError(ValueError):
    """Raised when a path attempts to escape its allowed base directory."""


def project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until a directory containing .claude/ is found.

    The walk is bounded: it will not ascend above the user's home directory.
    This prevents the per-user ~/.claude/ (Claude Code's global config) from being
    mistaken for a project root when running outside any project tree.

    Raises ProjectRootNotFound if no .claude/ is found within the search boundary.
    """
    here = (start or Path.cwd()).resolve()
    home = Path.home().resolve()

    # Build the candidate list: walk from `here` up to (but not including) home's parent.
    # We stop the ascending walk as soon as a candidate is no longer a descendant of home
    # (i.e., once we would go above home).  home itself is excluded from the search so
    # that ~/.claude is never treated as a project root.
    candidates: list[Path] = []
    for candidate in (here, *here.parents):
        if candidate == home or not candidate.is_relative_to(home):
            # We've reached home or gone above it — stop without adding.
            break
        candidates.append(candidate)

    for candidate in candidates:
        if (candidate / ".claude").is_dir():
            return candidate

    raise ProjectRootNotFound(
        f"No .claude/ found in {here} or any parent up to {home}. "
        "Are you running from a Mythos-enabled repo?"
    )


def mythos_dir() -> Path:
    """Return .mythos/ under the project root."""
    return project_root() / ".mythos"


def state_dir() -> Path:
    """Return .mythos/state/ — runtime state shared between concurrent workers."""
    return mythos_dir() / "state"


def poc_dir() -> Path:
    """Return .mythos/poc/ — directory holding hunter-produced PoC code."""
    return mythos_dir() / "poc"


def logs_dir() -> Path:
    """Return .mythos/logs/."""
    return mythos_dir() / "logs"


def audit_log() -> Path:
    """Return .mythos/audit.jsonl — append-only security event log."""
    return mythos_dir() / "audit.jsonl"


def ensure_dirs(*paths: Path) -> None:
    """Create one or more directories with parents=True, exist_ok=True."""
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def assert_safe_write(target: Path, base: Path) -> None:
    """Raise UnsafePathError if `target` is outside `base` after resolution.

    Use this before any Write operation to prevent path traversal.
    """
    try:
        resolved = target.resolve()
        base_resolved = base.resolve()
        resolved.relative_to(base_resolved)
    except ValueError:
        raise UnsafePathError(
            f"Path {target} resolves outside the allowed base {base}"
        )
