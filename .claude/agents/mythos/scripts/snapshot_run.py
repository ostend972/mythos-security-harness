"""snapshot_run.py — hash chain + tar snapshots for the Mythos state directory.

Used between phases to:
- Snapshot .mythos/ before each phase (for /mythos resume)
- Compute a deterministic hash of the state to detect tampering
- Advance run.json from one phase to the next, recording the hash

Reference: spec §11 T11 (state tampering), T20 (snapshot tampering).
"""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


SNAPSHOTS_SUBDIR = "snapshots"


def compute_hash_chain(mythos_dir: Path) -> str:
    """Compute a deterministic sha256 hash over all files under mythos_dir,
    EXCLUDING the snapshots/ subdir (which would change when we write a snapshot).
    """
    h = hashlib.sha256()
    if not mythos_dir.is_dir():
        return "sha256:" + h.hexdigest()

    files_to_hash = []
    for path in sorted(mythos_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(mythos_dir)
        if rel.parts and rel.parts[0] == SNAPSHOTS_SUBDIR:
            continue
        files_to_hash.append((str(rel).replace("\\", "/"), path))

    for rel_name, path in files_to_hash:
        h.update(rel_name.encode("utf-8"))
        h.update(b"\x00")
        try:
            h.update(path.read_bytes())
        except OSError:
            continue
        h.update(b"\x00")
    return "sha256:" + h.hexdigest()


def snapshot_phase(mythos_dir: Path, phase_label: str) -> Path:
    """Create a tar.gz snapshot of mythos_dir at the given phase label.

    Returns the path to the snapshot file.
    """
    snapshots = mythos_dir / SNAPSHOTS_SUBDIR
    snapshots.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    snapshot_path = snapshots / f"{phase_label}-{ts}.tar.gz"
    with tarfile.open(snapshot_path, "w:gz") as tar:
        for item in mythos_dir.iterdir():
            if item.name == SNAPSHOTS_SUBDIR:
                continue
            tar.add(item, arcname=item.name)
    return snapshot_path


def restore_phase(mythos_dir: Path, snapshot_path: Path) -> None:
    """Restore the mythos_dir contents (except snapshots/) from a tar.gz.

    Existing files outside snapshots/ are removed first to avoid mixed state.
    """
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"snapshot not found: {snapshot_path}")

    # Remove existing non-snapshot content
    for item in mythos_dir.iterdir():
        if item.name == SNAPSHOTS_SUBDIR:
            continue
        if item.is_dir():
            import shutil
            shutil.rmtree(item)
        else:
            item.unlink()

    with tarfile.open(snapshot_path, "r:gz") as tar:
        # Python 3.12+ requires filter arg; use 'data' for safe extraction
        try:
            tar.extractall(mythos_dir, filter="data")
        except TypeError:
            # Older Pythons
            tar.extractall(mythos_dir)


def advance_phase(mythos_dir: Path, next_phase: str) -> dict:
    """Move run.json forward: mark current phase as completed, set next_phase,
    refresh hash_chain. Return the updated run dict.
    """
    run_path = mythos_dir / "run.json"
    if not run_path.is_file():
        raise FileNotFoundError(f"run.json not found: {run_path}")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    current = run.get("current_phase")
    if current and current not in run.setdefault("phases_completed", []):
        run["phases_completed"].append(current)
    run["current_phase"] = next_phase
    run["current_phase_started_at"] = datetime.now(timezone.utc).isoformat()
    run["hash_chain"] = compute_hash_chain(mythos_dir)
    # Atomic write
    tmp = run_path.with_suffix(run_path.suffix + ".tmp")
    tmp.write_text(json.dumps(run, indent=2), encoding="utf-8")
    os.replace(tmp, run_path)
    return run
