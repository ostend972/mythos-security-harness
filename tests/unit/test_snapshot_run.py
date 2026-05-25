"""Tests for snapshot_run.py — hash chain + snapshot helpers."""
import hashlib
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import snapshot_run


class TestComputeHashChain:
    def test_empty_dir_has_stable_hash(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        h1 = snapshot_run.compute_hash_chain(d)
        h2 = snapshot_run.compute_hash_chain(d)
        assert h1 == h2
        assert h1.startswith("sha256:")
        assert len(h1) == len("sha256:") + 64

    def test_different_content_produces_different_hash(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a.txt").write_text("alpha", encoding="utf-8")
        h1 = snapshot_run.compute_hash_chain(d)
        (d / "a.txt").write_text("beta", encoding="utf-8")
        h2 = snapshot_run.compute_hash_chain(d)
        assert h1 != h2

    def test_excludes_snapshots_subdir(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a.txt").write_text("alpha", encoding="utf-8")
        h1 = snapshot_run.compute_hash_chain(d)
        # Creating a snapshot file inside the snapshots/ subdir should not change the chain
        (d / "snapshots").mkdir()
        (d / "snapshots" / "snap.tar.gz").write_bytes(b"\x00\x01\x02")
        h2 = snapshot_run.compute_hash_chain(d)
        assert h1 == h2


class TestSnapshotAndRestore:
    def test_snapshot_creates_tar_gz(self, tmp_path):
        d = tmp_path / "mythos"
        d.mkdir()
        (d / "task-queue.jsonl").write_text('{"task_id":"T-A"}\n', encoding="utf-8")
        snapshot_path = snapshot_run.snapshot_phase(d, "pre-recon")
        assert snapshot_path.exists()
        assert snapshot_path.suffix == ".gz"

    def test_restore_recovers_files(self, tmp_path):
        d = tmp_path / "mythos"
        d.mkdir()
        (d / "task-queue.jsonl").write_text('{"task_id":"T-A"}\n', encoding="utf-8")
        snapshot_path = snapshot_run.snapshot_phase(d, "pre-recon")
        # Mutate the original
        (d / "task-queue.jsonl").write_text('{"task_id":"MUTATED"}\n', encoding="utf-8")
        # Restore
        snapshot_run.restore_phase(d, snapshot_path)
        content = (d / "task-queue.jsonl").read_text(encoding="utf-8")
        assert "T-A" in content
        assert "MUTATED" not in content


class TestUpdateRunJson:
    def test_advances_phase_and_updates_hash(self, tmp_path):
        d = tmp_path / "mythos"
        d.mkdir()
        run_json = d / "run.json"
        run_json.write_text(json.dumps({
            "run_id":"R1","version":"1.0.0","target_path":"/x",
            "started_at":"2026-05-25T13:00:00Z","current_phase":"recon",
            "phases_completed":[]
        }), encoding="utf-8")
        snapshot_run.advance_phase(d, "hunt")
        new = json.loads(run_json.read_text(encoding="utf-8"))
        assert new["current_phase"] == "hunt"
        assert "recon" in new["phases_completed"]
        assert new["hash_chain"].startswith("sha256:")
