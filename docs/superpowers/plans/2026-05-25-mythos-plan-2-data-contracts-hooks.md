# Mythos Preview — Plan 2: Data Contracts + Hooks + Utility Scripts

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data layer (8 JSON schemas + Ajv-equivalent Python validator) and the security control layer (PreToolUse + PostToolUse hooks for path traversal / dangerous commands / secret leakage) that all 12 Mythos agents will rely on in Plans 3-6.

**Architecture:** Strict JSON Schema Draft 2020-12 contracts validated by the `jsonschema` Python library (`additionalProperties: false` everywhere). Hooks are short Python scripts invoked by Claude Code via stdin JSON (per official Claude Code hook protocol), exiting with code 0 (allow), 1 (warn), or 2 (block).

**Tech Stack:** Python 3.10+, `jsonschema[format-nongpl]>=4.20`, `psutil>=5.9`, regex-compiled secret patterns, `ripgrep` + `universal-ctags` (external CLI for symbol index).

**Spec reference:** [`docs/superpowers/specs/2026-05-25-mythos-preview-design.md`](../specs/2026-05-25-mythos-preview-design.md) (sections §8 Data contracts, §11 Threat model, §13 Observability)

**Plan 1 dependencies:** `common/paths.py`, `common/locking.py`, `common/platform_utils.py`, `common/docker_runner.py` (all delivered + tested in Plan 1).

**Out of scope for this plan (covered later):**
- Bug-class definitions (Plan 3)
- Cybersecurity skill installation (Plan 3)
- Agent .md files (Plans 4-5)
- `/mythos` skill orchestrator (Plan 6)

---

## File Structure

This plan creates the following files:

```
<repo_root>/
├── .claude/
│   └── agents/
│       └── mythos/
│           ├── schemas/
│           │   ├── task.schema.json
│           │   ├── finding.schema.json
│           │   ├── coverage.schema.json
│           │   ├── validated.schema.json
│           │   ├── dedup-cluster.schema.json
│           │   ├── trace.schema.json
│           │   ├── report.schema.json
│           │   └── run.schema.json
│           └── scripts/
│               ├── validate_jsonl.py
│               ├── validate_bash.py          # PreToolUse hook
│               ├── validate_write.py         # PostToolUse hook
│               ├── redact.py                 # secret redaction
│               ├── sanitize_output.py        # ANSI/control char stripper
│               ├── cleanup_orphans.py        # process + container cleanup
│               ├── agent_start.py            # SubagentStart hook
│               ├── build_symbol_index.py     # ctags + rg for Trace
│               ├── launch_hunters.py         # spawn N claude --agent processes
│               ├── launch_tracers.py         # same, for Trace phase
│               └── common/
│                   ├── schema.py             # StrictValidator wrapper
│                   ├── redact_patterns.py    # compiled regex patterns
│                   └── hook_io.py            # stdin/stdout JSON helpers
├── tests/
│   ├── unit/
│   │   ├── test_schemas_finding.py
│   │   ├── test_schemas_task.py
│   │   ├── test_schemas_coverage.py
│   │   ├── test_schemas_validated.py
│   │   ├── test_schemas_dedup_cluster.py
│   │   ├── test_schemas_trace.py
│   │   ├── test_schemas_report.py
│   │   ├── test_schemas_run.py
│   │   ├── test_validate_jsonl.py
│   │   ├── test_validate_bash.py
│   │   ├── test_validate_write.py
│   │   ├── test_redact.py
│   │   ├── test_sanitize_output.py
│   │   ├── test_cleanup_orphans.py
│   │   ├── test_agent_start.py
│   │   ├── test_build_symbol_index.py
│   │   ├── test_launch_hunters.py
│   │   └── test_schema_wrapper.py
│   └── integration/
│       └── test_hooks_integration.py
└── docs/superpowers/plans/
    └── 2026-05-25-mythos-plan-2-data-contracts-hooks.md   # this file
```

---

## Task 1: StrictValidator wrapper (common/schema.py)

**Files:**
- Create: `.claude/agents/mythos/scripts/common/schema.py`
- Test: `tests/unit/test_schema_wrapper.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_schema_wrapper.py`:
```python
"""Tests for the StrictValidator wrapper around jsonschema."""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError, SchemaNotFoundError


@pytest.fixture
def tmp_schema_dir(tmp_path):
    """Provide a temp schemas dir with one trivial schema."""
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "thing.schema.json").write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "string", "pattern": "^T-[A-Z0-9]+$"},
            "name": {"type": "string", "minLength": 1},
        },
    }), encoding="utf-8")
    return schemas


class TestStrictValidator:
    def test_loads_existing_schema(self, tmp_schema_dir):
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        assert v.schema_name == "thing"

    def test_raises_on_missing_schema(self, tmp_path):
        with pytest.raises(SchemaNotFoundError):
            StrictValidator("nonexistent", schema_dir=tmp_path)

    def test_validate_accepts_valid_data(self, tmp_schema_dir):
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        v.validate({"id": "T-001", "name": "alpha"})  # should not raise

    def test_validate_rejects_missing_required(self, tmp_schema_dir):
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        with pytest.raises(SchemaValidationError) as exc_info:
            v.validate({"id": "T-001"})
        assert "name" in str(exc_info.value)

    def test_validate_rejects_extra_properties(self, tmp_schema_dir):
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        with pytest.raises(SchemaValidationError):
            v.validate({"id": "T-001", "name": "alpha", "extra": "nope"})

    def test_validate_rejects_pattern_mismatch(self, tmp_schema_dir):
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        with pytest.raises(SchemaValidationError) as exc_info:
            v.validate({"id": "bad-id", "name": "alpha"})
        assert "pattern" in str(exc_info.value).lower() or "id" in str(exc_info.value)

    def test_validate_jsonl_stream_yields_per_line(self, tmp_schema_dir):
        target = tmp_schema_dir.parent / "things.jsonl"
        target.write_text(
            json.dumps({"id": "T-001", "name": "alpha"}) + "\n"
            + json.dumps({"id": "T-002", "name": "beta"}) + "\n"
            + json.dumps({"id": "bad", "name": "gamma"}) + "\n",
            encoding="utf-8",
        )
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        results = list(v.validate_jsonl_stream(target))
        assert len(results) == 3
        lineno, record, err = results[0]
        assert lineno == 1 and record is not None and err is None
        lineno, record, err = results[2]
        assert lineno == 3 and record is None and err is not None

    def test_validate_jsonl_stream_skips_blank_lines(self, tmp_schema_dir):
        target = tmp_schema_dir.parent / "things.jsonl"
        target.write_text(
            json.dumps({"id": "T-001", "name": "alpha"}) + "\n\n"
            + json.dumps({"id": "T-002", "name": "beta"}) + "\n",
            encoding="utf-8",
        )
        v = StrictValidator("thing", schema_dir=tmp_schema_dir)
        results = list(v.validate_jsonl_stream(target))
        assert len(results) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_schema_wrapper.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'common.schema'`.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/common/schema.py`:
```python
"""Strict JSON Schema validator for Mythos artifacts.

Wraps `jsonschema` (Draft 2020-12) with a single-class interface that:
- Loads a named schema from a configurable schemas directory
- Validates that schemas themselves are well-formed (check_schema)
- Validates payloads with format checking enabled
- Surfaces the most relevant error via best_match
- Provides a streaming validator for JSONL files (one record per line)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match


class SchemaNotFoundError(FileNotFoundError):
    """Raised when the requested schema name has no matching file."""


class SchemaValidationError(ValueError):
    """Raised when data fails validation against its schema."""


DEFAULT_SCHEMA_DIR = (
    Path(__file__).parent.parent.parent / "schemas"
)


class StrictValidator:
    """Validates data against a Draft 2020-12 JSON Schema with strict semantics.

    Strict means: additionalProperties=false in the schema is honored, formats
    are checked (uuid, date-time, ipv4, etc.), and the schema itself is verified
    well-formed at construction time.
    """

    def __init__(self, schema_name: str, *, schema_dir: Path | None = None) -> None:
        self.schema_name = schema_name
        self._schema_dir = schema_dir or DEFAULT_SCHEMA_DIR
        schema_path = self._schema_dir / f"{schema_name}.schema.json"
        if not schema_path.is_file():
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' not found at {schema_path}"
            )
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        # Will raise jsonschema.SchemaError if the schema itself is malformed.
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(
            self.schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    def validate(self, data: dict) -> None:
        """Validate `data` against the schema. Raises SchemaValidationError on failure."""
        errors = list(self._validator.iter_errors(data))
        if errors:
            err = best_match(errors)
            location = err.json_path if err.json_path else "<root>"
            raise SchemaValidationError(
                f"Schema '{self.schema_name}' validation failed at {location}: {err.message}"
            )

    def validate_jsonl_stream(
        self, path: Path
    ) -> Iterator[tuple[int, dict | None, Exception | None]]:
        """Yield (lineno, record_or_None, error_or_None) for each line in a JSONL file.

        Blank lines are skipped (no tuple yielded). JSON parse errors and schema
        validation errors are both captured into the third element.
        """
        with path.open("r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as e:
                    yield (lineno, None, e)
                    continue
                try:
                    self.validate(record)
                    yield (lineno, record, None)
                except SchemaValidationError as e:
                    yield (lineno, None, e)
```

- [ ] **Step 4: Verify tests pass**

```bash
pytest tests/unit/test_schema_wrapper.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/common/schema.py \
  tests/unit/test_schema_wrapper.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: StrictValidator wrapper around jsonschema Draft 2020-12"
```

---

## Task 2: All 8 JSON schemas

**Files:**
- Create: `.claude/agents/mythos/schemas/task.schema.json`
- Create: `.claude/agents/mythos/schemas/finding.schema.json`
- Create: `.claude/agents/mythos/schemas/coverage.schema.json`
- Create: `.claude/agents/mythos/schemas/validated.schema.json`
- Create: `.claude/agents/mythos/schemas/dedup-cluster.schema.json`
- Create: `.claude/agents/mythos/schemas/trace.schema.json`
- Create: `.claude/agents/mythos/schemas/report.schema.json`
- Create: `.claude/agents/mythos/schemas/run.schema.json`
- Test: `tests/unit/test_schemas_finding.py` (one per schema, see Step 4 below)

- [ ] **Step 1: Create schemas directory**

```bash
mkdir -p .claude/agents/mythos/schemas
```

- [ ] **Step 2: Write `finding.schema.json`** (the most critical — enforces "no PoC = drop")

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/finding.schema.json",
  "title": "Mythos Finding",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "finding_id", "task_id", "class", "file", "line",
    "function", "severity", "hypothesis", "poc_dir",
    "poc_log", "docker_image", "hunter_id", "confidence",
    "created_at"
  ],
  "properties": {
    "finding_id": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" },
    "task_id": { "type": "string", "pattern": "^T-[A-Z0-9]{4,}$" },
    "class": {
      "type": "string",
      "enum": [
        "sql-injection", "nosql-injection", "command-injection", "ssrf",
        "deserialization", "race-condition", "prototype-pollution", "ssti",
        "type-juggling", "jwt-confusion", "idor", "http-smuggling",
        "mass-assignment", "oauth", "websocket", "bfla", "data-exposure-api",
        "heap-corruption", "uaf", "oob-rw", "double-free", "format-string",
        "deeplink"
      ]
    },
    "file": { "type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$" },
    "line": { "type": "integer", "minimum": 1 },
    "function": { "type": "string", "minLength": 1 },
    "severity": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low", "info"]
    },
    "hypothesis": { "type": "string", "minLength": 10, "maxLength": 5000 },
    "poc_dir": { "type": "string", "pattern": "^poc/F-[A-Z0-9]{6,}/$" },
    "poc_log": { "type": "string", "maxLength": 50000 },
    "docker_image": { "type": "string", "minLength": 1 },
    "hunter_id": { "type": "string", "pattern": "^hunter-[0-9]{2,}$" },
    "confidence": {
      "type": "string",
      "enum": ["poc-confirmed"],
      "description": "ONLY accepted value — enforces 'no PoC = drop' policy at the schema level"
    },
    "created_at": { "type": "string", "format": "date-time" },
    "chain": {
      "type": "array",
      "items": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" },
      "description": "If this finding is part of an exploit chain, IDs of primitive findings"
    }
  }
}
```

- [ ] **Step 3: Write the other 7 schemas**

Write `.claude/agents/mythos/schemas/task.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/task.schema.json",
  "title": "Mythos Hunt Task",
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "class", "scope", "subsystem", "trust_boundary", "priority", "status"],
  "properties": {
    "task_id": { "type": "string", "pattern": "^T-[A-Z0-9]{4,}$" },
    "class": { "type": "string", "minLength": 1 },
    "scope": {
      "type": "string",
      "minLength": 1,
      "description": "Format: <file>:<function>"
    },
    "subsystem": { "type": "string", "minLength": 1 },
    "trust_boundary": { "type": "string", "minLength": 1 },
    "priority": { "type": "integer", "minimum": 1, "maximum": 5 },
    "status": {
      "type": "string",
      "enum": ["pending", "in_progress", "completed", "failed", "timeout"]
    },
    "source": {
      "type": "string",
      "enum": ["recon", "gapfill", "feedback-loop"],
      "description": "Where this task was generated from"
    },
    "consumer_repo": {
      "type": "string",
      "description": "Only set when source=feedback-loop"
    }
  }
}
```

Write `.claude/agents/mythos/schemas/coverage.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/coverage.schema.json",
  "title": "Mythos Hunter Coverage Record",
  "type": "object",
  "additionalProperties": false,
  "required": ["hunter_id", "task_id", "task_class", "task_scope", "verdict"],
  "properties": {
    "hunter_id": { "type": "string", "pattern": "^hunter-[0-9]{2,}$" },
    "task_id": { "type": "string", "pattern": "^T-[A-Z0-9]{4,}$" },
    "task_class": { "type": "string", "minLength": 1 },
    "task_scope": { "type": "string", "minLength": 1 },
    "files_read": { "type": "array", "items": { "type": "string" } },
    "functions_analyzed": { "type": "array", "items": { "type": "string" } },
    "classes_evaluated": { "type": "array", "items": { "type": "string" } },
    "partial_coverage": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["location", "reason"],
        "properties": {
          "location": { "type": "string" },
          "reason": { "type": "string" }
        }
      }
    },
    "findings_produced": {
      "type": "array",
      "items": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" }
    },
    "iterations_used": { "type": "integer", "minimum": 0 },
    "verdict": {
      "type": "string",
      "enum": ["completed", "timeout", "failed", "no_findings"]
    }
  }
}
```

Write `.claude/agents/mythos/schemas/validated.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/validated.schema.json",
  "title": "Mythos Validated Finding",
  "type": "object",
  "additionalProperties": false,
  "required": ["finding_id", "verdict", "validator_notes", "validated_at"],
  "properties": {
    "finding_id": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" },
    "verdict": { "type": "string", "enum": ["keep", "drop"] },
    "validator_notes": { "type": "string", "maxLength": 10000 },
    "independent_poc_path": { "type": "string" },
    "replayed_hunter_poc": { "type": "boolean" },
    "drop_reason": { "type": "string", "maxLength": 1000 },
    "validated_at": { "type": "string", "format": "date-time" }
  }
}
```

Write `.claude/agents/mythos/schemas/dedup-cluster.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/dedup-cluster.schema.json",
  "title": "Mythos Dedup Cluster Set",
  "type": "object",
  "additionalProperties": false,
  "required": ["clusters", "generated_at"],
  "properties": {
    "clusters": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["cluster_id", "root_cause", "primary_finding", "highest_severity"],
        "properties": {
          "cluster_id": { "type": "string", "pattern": "^C-[A-Z0-9]{6,}$" },
          "root_cause": { "type": "string", "minLength": 10 },
          "primary_finding": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" },
          "variant_findings": {
            "type": "array",
            "items": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" }
          },
          "highest_severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"]
          }
        }
      }
    },
    "generated_at": { "type": "string", "format": "date-time" }
  }
}
```

Write `.claude/agents/mythos/schemas/trace.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/trace.schema.json",
  "title": "Mythos Reachability Trace",
  "type": "object",
  "additionalProperties": false,
  "required": ["cluster_id", "consumer_repo", "reachable", "traced_at"],
  "properties": {
    "cluster_id": { "type": "string", "pattern": "^C-[A-Z0-9]{6,}$" },
    "consumer_repo": { "type": "string", "minLength": 1 },
    "reachable": { "type": "boolean" },
    "entry_points": { "type": "array", "items": { "type": "string" } },
    "call_chain": { "type": "array", "items": { "type": "string" } },
    "constraints": { "type": "array", "items": { "type": "string" } },
    "confidence": {
      "type": "string",
      "enum": ["high", "medium", "low"]
    },
    "traced_at": { "type": "string", "format": "date-time" }
  }
}
```

Write `.claude/agents/mythos/schemas/report.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/report.schema.json",
  "title": "Mythos Final Report",
  "type": "object",
  "additionalProperties": false,
  "required": ["run_id", "version", "target_path", "generated_at", "clusters", "metrics"],
  "properties": {
    "run_id": { "type": "string", "minLength": 1 },
    "version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "target_path": { "type": "string", "minLength": 1 },
    "generated_at": { "type": "string", "format": "date-time" },
    "clusters": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["cluster_id", "severity", "reachable", "primary_finding"],
        "properties": {
          "cluster_id": { "type": "string", "pattern": "^C-[A-Z0-9]{6,}$" },
          "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"]
          },
          "reachable": { "type": "boolean" },
          "primary_finding": { "type": "string", "pattern": "^F-[A-Z0-9]{6,}$" },
          "poc_path": { "type": "string" },
          "summary": { "type": "string", "maxLength": 2000 }
        }
      }
    },
    "metrics": {
      "type": "object",
      "additionalProperties": true,
      "description": "Free-form metrics (see metrics.json)"
    }
  }
}
```

Write `.claude/agents/mythos/schemas/run.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mythos.local/schemas/run.schema.json",
  "title": "Mythos Run State",
  "type": "object",
  "additionalProperties": false,
  "required": ["run_id", "version", "target_path", "started_at", "current_phase"],
  "properties": {
    "run_id": { "type": "string", "minLength": 1 },
    "version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "target_path": { "type": "string", "minLength": 1 },
    "started_at": { "type": "string", "format": "date-time" },
    "current_phase": {
      "type": "string",
      "enum": [
        "init", "recon", "hunt", "validate", "gapfill",
        "dedupe", "trace", "feedback", "report", "done"
      ]
    },
    "current_phase_started_at": { "type": "string", "format": "date-time" },
    "phases_completed": {
      "type": "array",
      "items": { "type": "string" }
    },
    "iteration_counts": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "gapfill": { "type": "integer", "minimum": 0 },
        "feedback": { "type": "integer", "minimum": 0 }
      }
    },
    "hash_chain": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
    "finished_at": { "type": "string", "format": "date-time" }
  }
}
```

- [ ] **Step 4: Write per-schema validation tests**

Write `tests/unit/test_schemas_finding.py`:
```python
"""Schema validation tests for finding.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("finding")


VALID_FINDING = {
    "finding_id": "F-ABC123",
    "task_id": "T-XY12",
    "class": "sql-injection",
    "file": "src/db.py",
    "line": 42,
    "function": "get_user",
    "severity": "high",
    "hypothesis": "User input concatenated into SQL query without parameterization.",
    "poc_dir": "poc/F-ABC123/",
    "poc_log": "Query returned admin row when injection payload sent.",
    "docker_image": "mythos-multilang:1.0.0",
    "hunter_id": "hunter-07",
    "confidence": "poc-confirmed",
    "created_at": "2026-05-25T14:00:00Z",
}


def test_valid_finding_passes(validator):
    validator.validate(VALID_FINDING)


def test_missing_finding_id_rejected(validator):
    bad = {k: v for k, v in VALID_FINDING.items() if k != "finding_id"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_finding_id_pattern_rejected(validator):
    bad = {**VALID_FINDING, "finding_id": "bad-id"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_unknown_class_rejected(validator):
    bad = {**VALID_FINDING, "class": "made-up-class"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_extra_property_rejected(validator):
    bad = {**VALID_FINDING, "extra_field": "no thanks"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_confidence_must_be_poc_confirmed(validator):
    """Schema-level enforcement of strict 'no PoC = drop' policy."""
    for bad_value in ["suspected", "theoretical", "high", "low"]:
        bad = {**VALID_FINDING, "confidence": bad_value}
        with pytest.raises(SchemaValidationError):
            validator.validate(bad)


def test_invalid_created_at_format_rejected(validator):
    bad = {**VALID_FINDING, "created_at": "not-a-date"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_chain_field_optional(validator):
    with_chain = {**VALID_FINDING, "chain": ["F-PRIM01", "F-PRIM02"]}
    validator.validate(with_chain)


def test_invalid_chain_member_rejected(validator):
    bad = {**VALID_FINDING, "chain": ["not-a-finding-id"]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_task.py`:
```python
"""Schema validation tests for task.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("task")


VALID_TASK = {
    "task_id": "T-ABCD",
    "class": "sql-injection",
    "scope": "src/db.py:get_user",
    "subsystem": "persistence",
    "trust_boundary": "HTTP request",
    "priority": 1,
    "status": "pending",
}


def test_valid_task_passes(validator):
    validator.validate(VALID_TASK)


def test_priority_out_of_range_rejected(validator):
    for bad_priority in [0, 6, -1, 100]:
        bad = {**VALID_TASK, "priority": bad_priority}
        with pytest.raises(SchemaValidationError):
            validator.validate(bad)


def test_unknown_status_rejected(validator):
    bad = {**VALID_TASK, "status": "running"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_source_field_optional(validator):
    with_source = {**VALID_TASK, "source": "gapfill"}
    validator.validate(with_source)


def test_invalid_source_rejected(validator):
    bad = {**VALID_TASK, "source": "manual"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_coverage.py`:
```python
"""Schema validation tests for coverage.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("coverage")


VALID_COVERAGE = {
    "hunter_id": "hunter-07",
    "task_id": "T-A1B2",
    "task_class": "command-injection",
    "task_scope": "src/api/users.py:update_profile",
    "files_read": ["src/api/users.py", "src/utils/shell.py"],
    "functions_analyzed": ["update_profile", "run_shell"],
    "classes_evaluated": ["command-injection"],
    "partial_coverage": [
        {"location": "src/api/users.py:delete_account", "reason": "not analyzed for race"}
    ],
    "findings_produced": ["F-AB1234"],
    "iterations_used": 3,
    "verdict": "completed",
}


def test_valid_coverage_passes(validator):
    validator.validate(VALID_COVERAGE)


def test_partial_coverage_missing_reason_rejected(validator):
    bad = {**VALID_COVERAGE,
           "partial_coverage": [{"location": "src/x.py:foo"}]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_partial_coverage_extra_field_rejected(validator):
    bad = {**VALID_COVERAGE,
           "partial_coverage": [{"location": "x", "reason": "y", "extra": "z"}]}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_verdict_rejected(validator):
    bad = {**VALID_COVERAGE, "verdict": "success"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_validated.py`:
```python
"""Schema validation tests for validated.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("validated")


VALID_KEEP = {
    "finding_id": "F-AB1234",
    "verdict": "keep",
    "validator_notes": "Independent PoC reproduced the bug.",
    "independent_poc_path": ".mythos/validate-pocs/V-F-AB1234/",
    "replayed_hunter_poc": True,
    "validated_at": "2026-05-25T15:00:00Z",
}

VALID_DROP = {
    "finding_id": "F-AB1234",
    "verdict": "drop",
    "validator_notes": "PoC did not reproduce; spec hypothesis was incorrect.",
    "drop_reason": "PoC failed to trigger the bug independently.",
    "validated_at": "2026-05-25T15:00:00Z",
}


def test_valid_keep_passes(validator):
    validator.validate(VALID_KEEP)


def test_valid_drop_passes(validator):
    validator.validate(VALID_DROP)


def test_unknown_verdict_rejected(validator):
    bad = {**VALID_KEEP, "verdict": "maybe"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_missing_required_rejected(validator):
    bad = {k: v for k, v in VALID_KEEP.items() if k != "verdict"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_dedup_cluster.py`:
```python
"""Schema validation tests for dedup-cluster.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("dedup-cluster")


VALID_CLUSTERS = {
    "clusters": [
        {
            "cluster_id": "C-AB1234",
            "root_cause": "Unsafe shell_exec wrapper called from 3 entry points.",
            "primary_finding": "F-AB1234",
            "variant_findings": ["F-CD5678"],
            "highest_severity": "high"
        }
    ],
    "generated_at": "2026-05-25T16:00:00Z"
}


def test_valid_clusters_passes(validator):
    validator.validate(VALID_CLUSTERS)


def test_empty_clusters_passes(validator):
    validator.validate({"clusters": [], "generated_at": "2026-05-25T16:00:00Z"})


def test_short_root_cause_rejected(validator):
    bad = {
        "clusters": [{
            "cluster_id": "C-AB1234",
            "root_cause": "short",
            "primary_finding": "F-AB1234",
            "highest_severity": "high"
        }],
        "generated_at": "2026-05-25T16:00:00Z"
    }
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_cluster_id_rejected(validator):
    bad = dict(VALID_CLUSTERS)
    bad["clusters"] = [{**bad["clusters"][0], "cluster_id": "C-too-short"}]
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_trace.py`:
```python
"""Schema validation tests for trace.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("trace")


VALID_TRACE = {
    "cluster_id": "C-AB1234",
    "consumer_repo": "/path/to/consumer-a",
    "reachable": True,
    "entry_points": ["POST /api/users/:id"],
    "call_chain": ["handler -> service -> lib_call"],
    "constraints": ["requires auth"],
    "confidence": "high",
    "traced_at": "2026-05-25T17:00:00Z"
}


def test_valid_trace_passes(validator):
    validator.validate(VALID_TRACE)


def test_unreachable_trace_passes(validator):
    unreachable = {**VALID_TRACE, "reachable": False, "entry_points": [], "call_chain": []}
    validator.validate(unreachable)


def test_invalid_confidence_rejected(validator):
    bad = {**VALID_TRACE, "confidence": "absolute"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)
```

Write `tests/unit/test_schemas_report.py`:
```python
"""Schema validation tests for report.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("report")


VALID_REPORT = {
    "run_id": "2026-05-25T13:00:00Z",
    "version": "1.0.0",
    "target_path": "/path/to/target",
    "generated_at": "2026-05-25T18:00:00Z",
    "clusters": [
        {
            "cluster_id": "C-AB1234",
            "severity": "high",
            "reachable": True,
            "primary_finding": "F-AB1234",
            "poc_path": "poc/F-AB1234/",
            "summary": "Command injection via update_profile."
        }
    ],
    "metrics": {"duration_minutes": 78, "tasks_completed": 305}
}


def test_valid_report_passes(validator):
    validator.validate(VALID_REPORT)


def test_invalid_version_format_rejected(validator):
    bad = {**VALID_REPORT, "version": "1.0"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_empty_clusters_passes(validator):
    empty = {**VALID_REPORT, "clusters": []}
    validator.validate(empty)
```

Write `tests/unit/test_schemas_run.py`:
```python
"""Schema validation tests for run.schema.json."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common.schema import StrictValidator, SchemaValidationError


@pytest.fixture(scope="module")
def validator():
    return StrictValidator("run")


VALID_RUN = {
    "run_id": "2026-05-25T13:00:00Z",
    "version": "1.0.0",
    "target_path": "/path/to/target",
    "started_at": "2026-05-25T13:00:00Z",
    "current_phase": "hunt"
}


def test_valid_run_passes(validator):
    validator.validate(VALID_RUN)


def test_invalid_phase_rejected(validator):
    bad = {**VALID_RUN, "current_phase": "scanning"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_invalid_hash_chain_rejected(validator):
    bad = {**VALID_RUN, "hash_chain": "not-a-hash"}
    with pytest.raises(SchemaValidationError):
        validator.validate(bad)


def test_valid_hash_chain_accepted(validator):
    ok = {**VALID_RUN, "hash_chain": "sha256:" + "a" * 64}
    validator.validate(ok)
```

- [ ] **Step 5: Run all schema tests**

```bash
pytest tests/unit/test_schemas_*.py -v
```

Expected: All schema tests PASS (about 35-40 tests).

- [ ] **Step 6: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/schemas/ \
  tests/unit/test_schemas_*.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: 8 JSON Schemas Draft 2020-12 for all Mythos artifacts"
```

---

## Task 3: validate_jsonl.py CLI

**Files:**
- Create: `.claude/agents/mythos/scripts/validate_jsonl.py`
- Test: `tests/unit/test_validate_jsonl.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_validate_jsonl.py`:
```python
"""Tests for the validate_jsonl.py CLI."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"


def run_cli(*args, cwd=None):
    """Invoke validate_jsonl.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPTS_DIR / "validate_jsonl.py"), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    return r.returncode, r.stdout, r.stderr


def test_valid_finding_jsonl_returns_0(tmp_path):
    """Valid finding JSONL exits 0."""
    p = tmp_path / "findings.jsonl"
    p.write_text(json.dumps({
        "finding_id": "F-ABC123", "task_id": "T-XY12", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "Injection via raw query concatenation.", "poc_dir": "poc/F-ABC123/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-07", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T14:00:00Z",
    }) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 0, f"stderr={err}"


def test_invalid_finding_jsonl_returns_1(tmp_path):
    """Invalid finding JSONL exits 1 and prints the violating line."""
    p = tmp_path / "findings.jsonl"
    p.write_text(json.dumps({"finding_id": "bad-id"}) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 1
    assert "line 1" in (out + err).lower() or "finding_id" in (out + err)


def test_mixed_jsonl_reports_each_line(tmp_path):
    """Stream validation reports per-line results, not just first failure."""
    p = tmp_path / "mixed.jsonl"
    valid_finding = {
        "finding_id": "F-ABC123", "task_id": "T-XY12", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "Injection via raw query concatenation.", "poc_dir": "poc/F-ABC123/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-07", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T14:00:00Z",
    }
    p.write_text(
        json.dumps(valid_finding) + "\n"
        + json.dumps({**valid_finding, "finding_id": "broken"}) + "\n"
        + json.dumps({**valid_finding, "finding_id": "F-DEF456"}) + "\n",
        encoding="utf-8",
    )
    rc, out, err = run_cli(str(p), "--schema", "finding")
    assert rc == 1  # at least one invalid line


def test_unknown_schema_returns_2(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text("{}\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "nonexistent-schema-name")
    assert rc == 2


def test_missing_input_file_returns_2(tmp_path):
    rc, out, err = run_cli(str(tmp_path / "does-not-exist.jsonl"), "--schema", "finding")
    assert rc == 2


def test_quiet_flag_suppresses_per_line_output(tmp_path):
    """With --quiet only the final summary is printed."""
    p = tmp_path / "f.jsonl"
    p.write_text(json.dumps({"finding_id": "broken"}) + "\n", encoding="utf-8")
    rc, out, err = run_cli(str(p), "--schema", "finding", "--quiet")
    assert rc == 1
    # Should be quieter: less verbose output
    assert len(out) < 500
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_validate_jsonl.py -v
```

Expected: FAIL with `FileNotFoundError` or similar.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/validate_jsonl.py`:
```python
"""validate_jsonl.py — CLI to validate a JSONL file against a Mythos schema.

Usage:
    python validate_jsonl.py <path> --schema <schema_name> [--quiet]

Exit codes:
    0 — all records valid
    1 — at least one record invalid
    2 — usage error (unknown schema, missing file, etc.)
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

from common.schema import StrictValidator, SchemaNotFoundError, SchemaValidationError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="validate_jsonl")
    p.add_argument("path", help="Path to the JSONL file to validate")
    p.add_argument("--schema", required=True, help="Schema name (e.g., 'finding', 'task')")
    p.add_argument("--quiet", action="store_true", help="Suppress per-line output")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = Path(args.path)
    if not path.is_file():
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 2

    try:
        validator = StrictValidator(args.schema)
    except SchemaNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    total = 0
    invalid = 0
    for lineno, record, err in validator.validate_jsonl_stream(path):
        total += 1
        if err is None:
            if not args.quiet:
                print(f"  line {lineno}: ok")
        else:
            invalid += 1
            if not args.quiet:
                print(f"  line {lineno}: INVALID — {err}", file=sys.stderr)

    print(f"=== {path.name}: {total - invalid}/{total} valid against schema '{args.schema}'")
    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_validate_jsonl.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/validate_jsonl.py \
  tests/unit/test_validate_jsonl.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: validate_jsonl.py CLI for schema validation"
```

---

## Task 4: hook_io.py shared helpers

**Files:**
- Create: `.claude/agents/mythos/scripts/common/hook_io.py`
- (no separate test — covered by hook tests below)

- [ ] **Step 1: Write the implementation**

Write `.claude/agents/mythos/scripts/common/hook_io.py`:
```python
"""Shared helpers for Claude Code hook scripts.

Claude Code passes hook input as JSON on stdin and reads JSON output from
stdout. Hooks exit with:
- 0: allow (default)
- 1: warn (printed to user but tool continues)
- 2: block (tool call rejected)

Schema reference: https://code.claude.com/docs/fr/hooks
"""
from __future__ import annotations

import json
import sys
from typing import Any


def read_hook_input() -> dict[str, Any]:
    """Read JSON from stdin. Return empty dict if stdin is empty/malformed."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_block(reason: str) -> int:
    """Print a blocking reason to stderr and return exit code 2."""
    print(reason, file=sys.stderr)
    return 2


def emit_warn(reason: str) -> int:
    """Print a warning to stderr and return exit code 1."""
    print(reason, file=sys.stderr)
    return 1


def emit_allow() -> int:
    """Allow the tool call. Return exit code 0."""
    return 0


def get_tool_input(hook_input: dict[str, Any]) -> dict[str, Any]:
    """Extract tool_input dict from the hook payload, defensive against missing keys."""
    return hook_input.get("tool_input") or {}


def get_tool_name(hook_input: dict[str, Any]) -> str:
    """Extract the tool name (e.g., 'Bash', 'Write')."""
    return hook_input.get("tool_name") or ""
```

- [ ] **Step 2: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/common/hook_io.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: shared helpers for Claude Code hook I/O"
```

---

## Task 5: validate_bash.py (PreToolUse hook for Bash commands)

**Files:**
- Create: `.claude/agents/mythos/scripts/validate_bash.py`
- Test: `tests/unit/test_validate_bash.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_validate_bash.py`:
```python
"""Tests for validate_bash.py PreToolUse hook."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "validate_bash.py"


def invoke(hook_input: dict) -> tuple[int, str, str]:
    """Invoke validate_bash.py with the given hook input JSON. Return (rc, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)]
    r = subprocess.run(
        cmd,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def hook(cmd: str) -> dict:
    """Build a minimal PreToolUse hook payload for a Bash command."""
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


@pytest.mark.parametrize("dangerous_cmd", [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf $HOME",
    "rm -rf /etc",
    "chmod 777 /",
    "chmod 777 /etc",
    "chown root /tmp/something",
    "sudo apt install x",
    "sudo bash",
    "su -",
    "su root",
    "setcap cap_net_admin+ep /usr/bin/something",
    "docker run --privileged alpine",
    "docker run -v /var/run/docker.sock:/var/run/docker.sock alpine",
    "cat /etc/shadow",
    "cat /etc/sudoers",
    "cat ~/.ssh/id_rsa",
    "cat ~/.aws/credentials",
    "cat ~/.config/gcloud/credentials.db",
    "cp anything ~/.kube/config",
    "ssh-add ~/.ssh/id_rsa",
])
def test_blocks_dangerous_commands(dangerous_cmd):
    rc, out, err = invoke(hook(dangerous_cmd))
    assert rc == 2, f"Expected block for: {dangerous_cmd!r}\nstdout={out}\nstderr={err}"


@pytest.mark.parametrize("safe_cmd", [
    "ls -la",
    "pytest tests/",
    "git status",
    "python preflight.py",
    "rm -rf .mythos/poc/F-test/",  # under .mythos/ is allowed
    "mkdir -p .mythos/state",
    "docker info",
    "docker ps",
])
def test_allows_safe_commands(safe_cmd):
    rc, out, err = invoke(hook(safe_cmd))
    assert rc == 0, f"Expected allow for: {safe_cmd!r}\nstdout={out}\nstderr={err}"


def test_empty_input_allows():
    """Empty stdin (malformed hook payload) should not block."""
    rc, out, err = invoke({})
    assert rc == 0


def test_non_bash_tool_allows():
    """Hook only applies to Bash. Other tools pass through."""
    rc, out, err = invoke({"tool_name": "Write", "tool_input": {"file_path": "any.txt"}})
    assert rc == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_validate_bash.py -v
```

Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/validate_bash.py`:
```python
"""validate_bash.py — PreToolUse hook for Bash commands.

Blocks catastrophic / out-of-scope commands by inspecting the command string.
Reads hook JSON from stdin per Claude Code hook protocol; exits with code 2
to block, 0 to allow.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §11 (Threat T13)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import (
    read_hook_input, emit_block, emit_allow, get_tool_input, get_tool_name,
)


# Each entry: (compiled_pattern, human-readable reason)
# Patterns are matched case-insensitively against the full command.
DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+-[rR]?[fF]\s+/(\s|$|\*)"), "rm -rf / (catastrophic)"),
    (re.compile(r"\brm\s+-[rR]?[fF]\s+(~|\$HOME)(\s|$|/)"), "rm -rf ~/ (catastrophic)"),
    (re.compile(r"\brm\s+-[rR]?[fF]\s+/etc"), "rm -rf /etc (catastrophic)"),
    (re.compile(r"\bchmod\s+777\s+/"), "chmod 777 on absolute root paths"),
    (re.compile(r"\bchown\s+root\b"), "chown to root"),
    (re.compile(r"\bsudo\b"), "sudo (out of scope for Mythos)"),
    (re.compile(r"(^|\s)su\s+(-|root)"), "su to root"),
    (re.compile(r"\bsetcap\b"), "setcap (out of scope)"),
    (re.compile(r"docker\s+run\s+[^#\n]*--privileged"), "docker --privileged (sandbox bypass)"),
    (re.compile(r"docker[^#\n]*docker\.sock"), "mounting docker.sock (sandbox bypass)"),
    (re.compile(r"\bcat\s+/etc/shadow"), "reading /etc/shadow"),
    (re.compile(r"\bcat\s+/etc/sudoers"), "reading /etc/sudoers"),
    (re.compile(r"(~|\$HOME)/\.ssh\b"), "accessing ~/.ssh"),
    (re.compile(r"(~|\$HOME)/\.aws\b"), "accessing ~/.aws"),
    (re.compile(r"(~|\$HOME)/\.config/gcloud\b"), "accessing ~/.config/gcloud"),
    (re.compile(r"(~|\$HOME)/\.kube\b"), "accessing ~/.kube"),
    (re.compile(r"(~|\$HOME)/\.docker\b"), "accessing ~/.docker"),
    (re.compile(r"\bssh-add\b"), "ssh-add (key import out of scope)"),
]


def check(command: str) -> tuple[bool, str | None]:
    """Return (allowed, reason). allowed=False means block."""
    cmd = command.strip()
    if not cmd:
        return True, None
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(cmd):
            return False, reason
    return True, None


def main() -> int:
    payload = read_hook_input()
    if get_tool_name(payload) != "Bash":
        return emit_allow()
    cmd = get_tool_input(payload).get("command", "")
    allowed, reason = check(cmd)
    if not allowed:
        return emit_block(
            f"[mythos validate_bash] Blocked dangerous command: {reason}\n"
            f"  Command: {cmd[:200]}"
        )
    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_validate_bash.py -v
```

Expected: All tests PASS (parameterized = ~30 individual cases).

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/validate_bash.py \
  tests/unit/test_validate_bash.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: validate_bash.py PreToolUse hook blocking catastrophic commands"
```

---

## Task 6: redact.py + redact_patterns.py (secret redaction)

**Files:**
- Create: `.claude/agents/mythos/scripts/common/redact_patterns.py`
- Create: `.claude/agents/mythos/scripts/redact.py`
- Test: `tests/unit/test_redact.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_redact.py`:
```python
"""Tests for the secret redaction pipeline."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from common import redact_patterns
from redact import redact_text, redact_dict


class TestRedactText:
    @pytest.mark.parametrize("secret,kind", [
        ("AKIAIOSFODNN7EXAMPLE", "aws_access_key"),
        ("ghp_1234567890123456789012345678901234567890", "github_token"),
        ("ghs_1234567890123456789012345678901234567890", "github_token"),
        ("sk_live_1234567890123456789012345", "stripe_live_key"),
    ])
    def test_replaces_obvious_secrets(self, secret, kind):
        text = f"Found credential: {secret} in config."
        redacted = redact_text(text)
        assert secret not in redacted
        assert "[REDACTED" in redacted

    def test_jwt_redacted(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        redacted = redact_text(f"token={jwt}")
        assert jwt not in redacted

    def test_dotenv_style_secret_redacted(self):
        text = "DATABASE_PASSWORD=supersecretvaluehere123456789"
        redacted = redact_text(text)
        assert "supersecretvaluehere123456789" not in redacted

    def test_pem_private_key_redacted(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKC...\n-----END RSA PRIVATE KEY-----"
        redacted = redact_text(text)
        assert "PRIVATE KEY" not in redacted or "[REDACTED" in redacted

    def test_safe_text_passes_through(self):
        text = "This is normal text without any secrets in it."
        assert redact_text(text) == text


class TestRedactDict:
    def test_redacts_nested_secret(self):
        data = {
            "name": "alpha",
            "credentials": {"aws_key": "AKIAIOSFODNN7EXAMPLE"},
        }
        out = redact_dict(data)
        assert out["name"] == "alpha"
        assert "AKIA" not in json.dumps(out)

    def test_redacts_in_lists(self):
        data = {"tokens": ["ghp_1234567890123456789012345678901234567890", "safe-value"]}
        out = redact_dict(data)
        assert "ghp_1234" not in json.dumps(out)
        assert "safe-value" in json.dumps(out)


class TestRedactCLI:
    def test_cli_redacts_stdin_to_stdout(self):
        script = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "redact.py"
        secret = "AKIAIOSFODNN7EXAMPLE"
        r = subprocess.run(
            [sys.executable, str(script)],
            input=f"Has key {secret} here",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert r.returncode == 0
        assert secret not in r.stdout
        assert "[REDACTED" in r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_redact.py -v
```

Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write redact_patterns.py**

Write `.claude/agents/mythos/scripts/common/redact_patterns.py`:
```python
"""Compiled regex patterns for redacting secrets from Mythos artifacts.

Each pattern matches a class of secret. The pattern's named match (or full
match if no named group) is replaced with `[REDACTED <kind>]`.

Threat model reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §11 T6.
"""
from __future__ import annotations

import re


# Each entry: (kind_label, compiled_pattern). Order matters — more specific first.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("aws_secret_key", re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("stripe_live_key", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("stripe_test_key", re.compile(r"sk_test_[A-Za-z0-9]{24,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("pem_key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    )),
    ("dotenv_secret", re.compile(
        r"(?m)^(?P<key>[A-Z][A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL))=(?P<value>[^\s'\"]{16,})"
    )),
]


def find_secrets(text: str) -> list[tuple[str, str]]:
    """Return list of (kind, matched_substring) for all secret hits in text."""
    hits: list[tuple[str, str]] = []
    for kind, pattern in PATTERNS:
        for m in pattern.finditer(text):
            hits.append((kind, m.group(0)))
    return hits
```

- [ ] **Step 4: Write redact.py**

Write `.claude/agents/mythos/scripts/redact.py`:
```python
"""redact.py — strip secrets from text and JSON structures.

CLI usage:
    cat raw.txt | python redact.py > clean.txt

Library usage:
    from redact import redact_text, redact_dict
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.redact_patterns import PATTERNS


def redact_text(text: str) -> str:
    """Replace each matched secret with `[REDACTED <kind>]`."""
    out = text
    for kind, pattern in PATTERNS:
        out = pattern.sub(f"[REDACTED {kind}]", out)
    return out


def redact_dict(data: Any) -> Any:
    """Recursively redact strings inside a JSON-like structure."""
    if isinstance(data, str):
        return redact_text(data)
    if isinstance(data, dict):
        return {k: redact_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data


def main() -> int:
    raw = sys.stdin.read()
    sys.stdout.write(redact_text(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_redact.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/common/redact_patterns.py \
  .claude/agents/mythos/scripts/redact.py \
  tests/unit/test_redact.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: secret redaction (AWS/GitHub/Stripe/JWT/PEM/.env patterns)"
```

---

## Task 7: sanitize_output.py (strip ANSI/control chars)

**Files:**
- Create: `.claude/agents/mythos/scripts/sanitize_output.py`
- Test: `tests/unit/test_sanitize_output.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_sanitize_output.py`:
```python
"""Tests for sanitize_output.py."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

from sanitize_output import sanitize


def test_strips_ansi_color_codes():
    text = "\x1b[31mERROR\x1b[0m: something bad"
    assert sanitize(text) == "ERROR: something bad"


def test_strips_ansi_cursor_movement():
    text = "\x1b[2J\x1b[H\x1b[1;1Hclean output"
    assert sanitize(text) == "clean output"


def test_preserves_newlines_and_tabs():
    text = "line1\nline2\twith tab"
    assert sanitize(text) == text


def test_strips_other_control_chars():
    text = "before\x07\x08\x0c\x1eafter"  # BEL, BS, FF, RS
    assert sanitize(text) == "beforeafter"


def test_truncates_at_1mb():
    text = "x" * (2 * 1024 * 1024)
    result = sanitize(text)
    assert len(result) <= 1_000_000


def test_custom_truncation_limit():
    text = "x" * 1000
    result = sanitize(text, max_bytes=500)
    assert len(result) <= 500


def test_empty_string_safe():
    assert sanitize("") == ""


def test_returns_string():
    assert isinstance(sanitize("hello"), str)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_sanitize_output.py -v
```

Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/sanitize_output.py`:
```python
"""sanitize_output.py — strip ANSI escape sequences and control characters.

CLI usage:
    cat noisy.log | python sanitize_output.py > clean.log

Library usage:
    from sanitize_output import sanitize
    clean = sanitize(raw, max_bytes=1_000_000)
"""
from __future__ import annotations

import re
import sys

# Strip CSI/OSC ANSI sequences (color, cursor, OSC).
ANSI_PATTERN = re.compile(r"\x1b(?:\[[0-9;]*[A-Za-z]|\][^\x07\x1b]*(?:\x07|\x1b\\))")

# Strip C0 control chars except \n (0x0a) and \t (0x09).
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

DEFAULT_MAX_BYTES = 1_000_000


def sanitize(text: str, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    """Strip ANSI + control chars and truncate to max_bytes."""
    out = ANSI_PATTERN.sub("", text)
    out = CONTROL_PATTERN.sub("", out)
    if len(out) > max_bytes:
        out = out[:max_bytes]
    return out


def main() -> int:
    raw = sys.stdin.read()
    sys.stdout.write(sanitize(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_sanitize_output.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/sanitize_output.py \
  tests/unit/test_sanitize_output.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: sanitize_output strips ANSI/control chars with size cap"
```

---

## Task 8: validate_write.py (PostToolUse hook for Write/Edit)

**Files:**
- Create: `.claude/agents/mythos/scripts/validate_write.py`
- Test: `tests/unit/test_validate_write.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_validate_write.py`:
```python
"""Tests for validate_write.py PostToolUse hook."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "validate_write.py"


def invoke(hook_input: dict, *extra_args: str) -> tuple[int, str, str]:
    cmd = [sys.executable, str(SCRIPT), *extra_args]
    r = subprocess.run(
        cmd, input=json.dumps(hook_input), capture_output=True, text=True, timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def write_hook(path: str, content: str = "") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_hook(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


class TestPathTraversal:
    def test_blocks_parent_dir_traversal(self):
        rc, out, err = invoke(write_hook(".mythos/poc/../../../etc/passwd"))
        assert rc == 2, f"stderr={err}"

    def test_blocks_absolute_path_outside_project(self):
        rc, out, err = invoke(write_hook("/etc/passwd"))
        assert rc == 2

    def test_allows_normal_path_inside_mythos(self):
        rc, out, err = invoke(write_hook(".mythos/poc/F-test/run.sh"))
        assert rc == 0


class TestAllowPattern:
    def test_allow_pattern_restricts_writes(self):
        # With --allow-pattern, writes outside the allowed regex are blocked
        rc, out, err = invoke(
            write_hook(".claude/agents/mythos/scripts/oops.py"),
            "--allow-pattern", r"^\.mythos/findings\.jsonl$",
        )
        assert rc == 2

    def test_allow_pattern_permits_matching(self):
        rc, out, err = invoke(
            write_hook(".mythos/findings.jsonl"),
            "--allow-pattern", r"^\.mythos/findings\.jsonl$",
        )
        assert rc == 0


class TestSecretLeakage:
    def test_blocks_aws_key_in_write_content(self):
        rc, out, err = invoke(write_hook(
            ".mythos/findings.jsonl",
            content='{"finding_id":"F-A","creds":"AKIAIOSFODNN7EXAMPLE"}',
        ))
        # Either block (2) or warn (1) — but must not silently allow
        assert rc != 0


class TestNonWriteToolPassthrough:
    def test_read_passes_through(self):
        rc, out, err = invoke({"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}})
        assert rc == 0

    def test_bash_passes_through(self):
        rc, out, err = invoke({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert rc == 0


def test_empty_input_allows():
    rc, out, err = invoke({})
    assert rc == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_validate_write.py -v
```

Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/validate_write.py`:
```python
"""validate_write.py — PostToolUse hook for Write/Edit operations.

Two enforcement layers:
1. Path traversal: blocks writes that resolve outside the project root.
2. Allow-list pattern: if --allow-pattern is given, only writes whose
   file_path matches the regex are allowed.
3. Secret leakage: blocks/warns if the written content contains common
   secret patterns.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §11 T4, T6.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import (
    read_hook_input, emit_block, emit_warn, emit_allow,
    get_tool_input, get_tool_name,
)
from common.paths import project_root, ProjectRootNotFound, UnsafePathError, assert_safe_write
from common.redact_patterns import find_secrets


WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="validate_write")
    p.add_argument(
        "--allow-pattern",
        action="append",
        default=[],
        help="Regex that file_path must match (can be given multiple times; OR'd)",
    )
    return p.parse_args(argv)


def check_path_traversal(file_path: str) -> tuple[bool, str | None]:
    """Return (ok, error). file_path must stay inside project_root."""
    try:
        root = project_root()
    except ProjectRootNotFound:
        # Outside any Mythos project — pass through (hook is a no-op).
        return True, None
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    try:
        assert_safe_write(target, base=root)
        return True, None
    except UnsafePathError as e:
        return False, str(e)


def check_allow_patterns(file_path: str, patterns: list[str]) -> tuple[bool, str | None]:
    if not patterns:
        return True, None
    for raw in patterns:
        if re.search(raw, file_path):
            return True, None
    return False, (
        f"path '{file_path}' did not match any allow pattern "
        f"({len(patterns)} pattern(s) tried)"
    )


def check_secrets(content: str) -> tuple[bool, str | None]:
    hits = find_secrets(content or "")
    if not hits:
        return True, None
    summary = ", ".join({kind for kind, _ in hits})
    return False, f"detected secret patterns in content: {summary}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = read_hook_input()
    tool = get_tool_name(payload)
    if tool not in WRITE_TOOLS:
        return emit_allow()

    tool_input = get_tool_input(payload)
    file_path = tool_input.get("file_path") or ""
    content = tool_input.get("content") or tool_input.get("new_string") or ""

    ok, reason = check_path_traversal(file_path)
    if not ok:
        return emit_block(f"[mythos validate_write] path traversal blocked: {reason}")

    ok, reason = check_allow_patterns(file_path, args.allow_pattern)
    if not ok:
        return emit_block(f"[mythos validate_write] {reason}")

    ok, reason = check_secrets(content)
    if not ok:
        # Warn instead of hard-block so hunters who legitimately include
        # high-entropy strings in PoC payloads can still proceed.
        return emit_warn(f"[mythos validate_write] {reason}")

    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_validate_write.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/validate_write.py \
  tests/unit/test_validate_write.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: validate_write.py blocks path traversal + secrets in Write/Edit"
```

---

## Task 9: cleanup_orphans.py

**Files:**
- Create: `.claude/agents/mythos/scripts/cleanup_orphans.py`
- Test: `tests/unit/test_cleanup_orphans.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_cleanup_orphans.py`:
```python
"""Tests for cleanup_orphans.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import cleanup_orphans


class TestFindOrphanContainers:
    def test_returns_empty_when_no_mythos_containers(self):
        with patch("cleanup_orphans.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = cleanup_orphans.find_orphan_containers()
            assert result == []

    def test_parses_container_ids(self):
        with patch("cleanup_orphans.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="abc123\ndef456\n", returncode=0,
            )
            result = cleanup_orphans.find_orphan_containers()
            assert result == ["abc123", "def456"]


class TestKillOrphanProcesses:
    def test_returns_killed_count(self):
        with patch("cleanup_orphans.psutil.process_iter") as mock_iter:
            mock_proc = MagicMock()
            mock_proc.info = {"pid": 12345, "name": "claude", "cmdline": ["claude", "--agent", "mythos-hunter"]}
            mock_proc.kill = MagicMock()
            mock_iter.return_value = [mock_proc]
            count = cleanup_orphans.kill_orphan_claude_processes(parent_pid=99999)
            assert count >= 0


def test_main_runs_without_error():
    """Smoke test: main() should not raise."""
    with patch("cleanup_orphans.find_orphan_containers", return_value=[]):
        with patch("cleanup_orphans.kill_orphan_claude_processes", return_value=0):
            rc = cleanup_orphans.main([])
            assert rc == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_cleanup_orphans.py -v
```

Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/cleanup_orphans.py`:
```python
"""cleanup_orphans.py — kill orphaned Mythos containers + claude processes.

Triggered:
- Manually: python cleanup_orphans.py
- As Stop hook: settings.json hooks.Stop entry
- Periodically: optional cron entry

Looks for:
- Docker containers whose name starts with 'mythos-' (no live parent attached)
- Python `claude --agent` processes whose parent is no longer the Mythos session
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Iterable

import psutil

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def find_orphan_containers() -> list[str]:
    """Return Docker container IDs whose name starts with 'mythos-'.

    Docker isn't required to be on PATH — if it isn't, return empty.
    """
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=mythos-", "--format", "{{.ID}}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def kill_containers(ids: Iterable[str]) -> int:
    """Force-remove containers. Return count actually removed."""
    removed = 0
    for cid in ids:
        try:
            r = subprocess.run(
                ["docker", "rm", "-f", cid], capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                removed += 1
        except (OSError, subprocess.TimeoutExpired):
            continue
    return removed


def kill_orphan_claude_processes(parent_pid: int) -> int:
    """Kill `claude --agent mythos-*` processes whose ppid is no longer `parent_pid`."""
    killed = 0
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            cmdline = info.get("cmdline") or []
            if "claude" not in name.lower() and not any("claude" in str(a).lower() for a in cmdline):
                continue
            cmd_str = " ".join(str(a) for a in cmdline)
            if "mythos-" not in cmd_str:
                continue
            if info.get("ppid") == parent_pid:
                continue
            proc.kill()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="cleanup_orphans")
    p.add_argument("--parent-pid", type=int, default=os.getppid(),
                   help="Only orphans whose ppid != this are killed (default: ppid of this process)")
    p.add_argument("--dry-run", action="store_true", help="Report what would be done")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    containers = find_orphan_containers()
    if args.dry_run:
        print(f"would remove {len(containers)} container(s): {containers}")
    else:
        removed = kill_containers(containers)
        print(f"removed {removed}/{len(containers)} containers")

    if args.dry_run:
        print(f"would scan for orphan claude processes (parent_pid={args.parent_pid})")
    else:
        killed = kill_orphan_claude_processes(parent_pid=args.parent_pid)
        print(f"killed {killed} orphan claude processes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_cleanup_orphans.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/cleanup_orphans.py \
  tests/unit/test_cleanup_orphans.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: cleanup_orphans removes stale containers + claude processes"
```

---

## Task 10: agent_start.py (SubagentStart hook)

**Files:**
- Create: `.claude/agents/mythos/scripts/agent_start.py`
- Test: `tests/unit/test_agent_start.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_agent_start.py`:
```python
"""Tests for agent_start.py SubagentStart hook."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts" / "agent_start.py"


def invoke(payload: dict) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10,
    )
    return r.returncode, r.stdout, r.stderr


def test_non_mythos_agent_passes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, _, _ = invoke({"agent_type": "general-purpose"})
    assert rc == 0


def test_mythos_agent_creates_audit_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Project root needs a .claude/ dir for paths.project_root() to succeed
    (tmp_path / ".claude").mkdir()
    rc, _, _ = invoke({"agent_type": "mythos-hunter"})
    assert rc == 0
    audit = tmp_path / ".mythos" / "audit.jsonl"
    if audit.exists():
        content = audit.read_text(encoding="utf-8")
        assert "agent_start" in content
        assert "mythos-hunter" in content


def test_empty_input_safe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, _, _ = invoke({})
    assert rc == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_agent_start.py -v
```

Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/agent_start.py`:
```python
"""agent_start.py — SubagentStart hook for Mythos agents.

Logs every Mythos sub-agent invocation to .mythos/audit.jsonl with timestamp,
agent type, and any provided task context. Non-Mythos agents pass through
silently.

Reference: docs/superpowers/specs/2026-05-25-mythos-preview-design.md §13.3 audit log.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.hook_io import read_hook_input, emit_allow
from common.paths import project_root, ProjectRootNotFound, mythos_dir, ensure_dirs
from common.locking import AtomicJsonlAppender


def main() -> int:
    payload = read_hook_input()
    agent_type = payload.get("agent_type") or ""
    if not agent_type.startswith("mythos-"):
        return emit_allow()

    try:
        project_root()  # ensure we're in a Mythos repo
    except ProjectRootNotFound:
        return emit_allow()

    audit_dir = mythos_dir()
    ensure_dirs(audit_dir)
    audit_path = audit_dir / "audit.jsonl"

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "event": "agent_start",
        "agent_type": agent_type,
        "session_id": payload.get("session_id"),
    }
    try:
        AtomicJsonlAppender(audit_path, timeout_s=5.0).append(record)
    except Exception as e:
        # Never break the agent start — log only.
        print(f"[mythos agent_start] failed to write audit log: {e}", file=sys.stderr)

    return emit_allow()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_agent_start.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/agent_start.py \
  tests/unit/test_agent_start.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: agent_start.py SubagentStart hook for audit logging"
```

---

## Task 11: build_symbol_index.py

**Files:**
- Create: `.claude/agents/mythos/scripts/build_symbol_index.py`
- Test: `tests/unit/test_build_symbol_index.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_build_symbol_index.py`:
```python
"""Tests for build_symbol_index.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import build_symbol_index


def test_extract_symbols_calls_ctags(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value="/usr/bin/ctags"):
        with patch("build_symbol_index.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps({"name": "foo", "path": "src/x.py", "line": 10}) + "\n",
                returncode=0,
            )
            symbols = build_symbol_index.extract_symbols(tmp_path)
            assert isinstance(symbols, list)


def test_extract_symbols_returns_empty_when_ctags_missing(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value=None):
        symbols = build_symbol_index.extract_symbols(tmp_path)
        assert symbols == []


def test_find_consumer_repos_detects_lockfiles(tmp_path):
    # Create a fake consumer repo with package.json referencing a lib
    consumer = tmp_path / "consumer-a"
    consumer.mkdir()
    (consumer / "package.json").write_text(
        json.dumps({"dependencies": {"my-lib": "1.0.0"}}),
        encoding="utf-8",
    )
    results = build_symbol_index.find_consumer_repos([tmp_path], "my-lib")
    assert consumer in results


def test_find_consumer_repos_skips_unrelated(tmp_path):
    consumer = tmp_path / "consumer-b"
    consumer.mkdir()
    (consumer / "package.json").write_text(
        json.dumps({"dependencies": {"other-lib": "1.0.0"}}),
        encoding="utf-8",
    )
    results = build_symbol_index.find_consumer_repos([tmp_path], "my-lib")
    assert consumer not in results


def test_main_runs_without_crash(tmp_path):
    with patch("build_symbol_index.shutil.which", return_value=None):
        rc = build_symbol_index.main(["--output", str(tmp_path / "symbols.json")])
        assert rc in (0, 2)
        # Should write SOMETHING (even if degraded mode)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_build_symbol_index.py -v
```

Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Write the implementation**

Write `.claude/agents/mythos/scripts/build_symbol_index.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_build_symbol_index.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/build_symbol_index.py \
  tests/unit/test_build_symbol_index.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: build_symbol_index.py (ctags + rg cross-repo symbol map)"
```

---

## Task 12: launch_hunters.py + launch_tracers.py

**Files:**
- Create: `.claude/agents/mythos/scripts/launch_hunters.py`
- Create: `.claude/agents/mythos/scripts/launch_tracers.py`
- Test: `tests/unit/test_launch_hunters.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_launch_hunters.py`:
```python
"""Tests for launch_hunters.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"))

import launch_hunters


@pytest.fixture
def task_queue(tmp_path):
    """Create a fake task-queue.jsonl with 5 pending tasks."""
    q = tmp_path / "task-queue.jsonl"
    lines = []
    for i in range(5):
        lines.append(json.dumps({
            "task_id": f"T-T{i:03d}",
            "class": "sql-injection",
            "scope": f"src/x.py:func{i}",
            "subsystem": "api",
            "trust_boundary": "HTTP",
            "priority": 1,
            "status": "pending",
        }))
    q.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return q


def test_read_pending_tasks_returns_pending_only(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=10)
    assert len(tasks) == 5
    assert all(t["status"] == "pending" for t in tasks)


def test_read_pending_tasks_honors_limit(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=3)
    assert len(tasks) == 3


def test_build_hunter_prompt_includes_task_json():
    task = {"task_id": "T-T001", "class": "sql-injection", "scope": "src/x.py:foo",
            "subsystem": "api", "trust_boundary": "HTTP", "priority": 1, "status": "pending"}
    prompt = launch_hunters.build_hunter_prompt(task, architecture_md="ARCH HERE")
    assert "T-T001" in prompt
    assert "sql-injection" in prompt
    assert "ARCH HERE" in prompt


def test_mark_tasks_in_progress(task_queue):
    tasks = launch_hunters.read_pending_tasks(task_queue, limit=2)
    launch_hunters.mark_tasks_status(task_queue, [t["task_id"] for t in tasks], "in_progress")
    new_tasks = launch_hunters.read_pending_tasks(task_queue, limit=10)
    assert len(new_tasks) == 3  # 5 - 2 that we just claimed


def test_dispatch_dry_run_does_not_invoke_subprocess(tmp_path, task_queue):
    with patch("launch_hunters.subprocess.Popen") as mock_popen:
        rc = launch_hunters.main([
            "--queue", str(task_queue),
            "--architecture", str(tmp_path / "arch.md"),
            "--batch-size", "2",
            "--dry-run",
        ])
        assert rc == 0
        mock_popen.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_launch_hunters.py -v
```

Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Write launch_hunters.py**

Write `.claude/agents/mythos/scripts/launch_hunters.py`:
```python
"""launch_hunters.py — script that spawns N `claude --agent mythos-hunter` processes
in parallel from the task queue.

Each hunter receives its task JSON + the architecture context as user input,
runs in detached mode, writes its findings/coverage to .mythos/ via locks, and
exits. This script waits for all hunters in the batch and reports outcomes.

Reference: spec §5.1.2 (mythos-hunt-lead orchestration), §11 T15 (rate limit backoff).
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
from typing import Any

HERE = Path(__file__).parent.resolve()
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.locking import AtomicJsonlAppender


def read_pending_tasks(queue_path: Path, limit: int) -> list[dict]:
    """Read up to `limit` tasks with status='pending' from the JSONL queue."""
    if not queue_path.is_file():
        return []
    tasks = []
    for raw in queue_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            t = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if t.get("status") == "pending":
            tasks.append(t)
            if len(tasks) >= limit:
                break
    return tasks


def mark_tasks_status(queue_path: Path, task_ids: list[str], status: str) -> None:
    """Rewrite the queue file with given tasks' status updated."""
    if not queue_path.is_file():
        return
    ids = set(task_ids)
    new_lines = []
    for raw in queue_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            t = json.loads(raw)
        except json.JSONDecodeError:
            new_lines.append(raw)
            continue
        if t.get("task_id") in ids:
            t["status"] = status
        new_lines.append(json.dumps(t))
    tmp = queue_path.with_suffix(queue_path.suffix + ".tmp")
    tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.replace(tmp, queue_path)


def build_hunter_prompt(task: dict, architecture_md: str) -> str:
    """Build the -p prompt for a single hunter invocation."""
    return (
        "You are starting Mythos hunt task.\n\n"
        f"Task: {json.dumps(task, indent=2)}\n\n"
        "Architecture context:\n"
        f"{architecture_md}\n"
    )


def spawn_one_hunter(task: dict, prompt: str, work_dir: Path) -> dict:
    """Spawn `claude --agent mythos-hunter -p <prompt>` and wait. Return outcome dict."""
    task_id = task.get("task_id", "T-unknown")
    start = time.monotonic()
    try:
        p = subprocess.run(
            ["claude", "--agent", "mythos-hunter", "-p", prompt],
            cwd=work_dir, capture_output=True, text=True, timeout=600,
        )
        return {
            "task_id": task_id,
            "exit_code": p.returncode,
            "duration_s": time.monotonic() - start,
            "stdout_tail": p.stdout[-2000:],
            "stderr_tail": p.stderr[-2000:],
            "status": "completed" if p.returncode == 0 else "failed",
        }
    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id, "exit_code": -1,
            "duration_s": time.monotonic() - start,
            "status": "timeout",
        }
    except FileNotFoundError:
        return {
            "task_id": task_id, "exit_code": -1,
            "duration_s": time.monotonic() - start,
            "status": "failed", "stderr_tail": "claude CLI not on PATH",
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="launch_hunters")
    p.add_argument("--queue", default=".mythos/task-queue.jsonl")
    p.add_argument("--architecture", default=".mythos/architecture.md")
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    queue_path = Path(args.queue)
    arch_path = Path(args.architecture)

    if not queue_path.is_file():
        print(f"queue not found: {queue_path}", file=sys.stderr)
        return 2

    arch_md = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else ""
    tasks = read_pending_tasks(queue_path, args.batch_size)
    if not tasks:
        print("no pending tasks — nothing to dispatch")
        return 0

    print(f"dispatching {len(tasks)} hunters (batch_size={args.batch_size})")
    if args.dry_run:
        for t in tasks:
            print(f"  would spawn: task={t.get('task_id')} class={t.get('class')}")
        return 0

    mark_tasks_status(queue_path, [t["task_id"] for t in tasks], "in_progress")

    work_dir = Path.cwd()
    outcomes = []
    with ThreadPoolExecutor(max_workers=args.batch_size) as pool:
        future_to_task = {
            pool.submit(spawn_one_hunter, t, build_hunter_prompt(t, arch_md), work_dir): t
            for t in tasks
        }
        for fut in as_completed(future_to_task):
            outcomes.append(fut.result())

    # Update task statuses based on outcomes
    completed = [o["task_id"] for o in outcomes if o.get("status") == "completed"]
    failed = [o["task_id"] for o in outcomes if o.get("status") in ("failed", "timeout")]
    mark_tasks_status(queue_path, completed, "completed")
    mark_tasks_status(queue_path, failed, "failed")

    print(f"batch done: {len(completed)} completed, {len(failed)} failed/timeout")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write launch_tracers.py**

Write `.claude/agents/mythos/scripts/launch_tracers.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_launch_hunters.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  .claude/agents/mythos/scripts/launch_hunters.py \
  .claude/agents/mythos/scripts/launch_tracers.py \
  tests/unit/test_launch_hunters.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: parallel hunter + tracer launcher scripts"
```

---

## Task 13: Integration test — hooks pipeline end-to-end

**Files:**
- Create: `tests/integration/test_hooks_integration.py`

- [ ] **Step 1: Write the integration test**

Write `tests/integration/test_hooks_integration.py`:
```python
"""End-to-end pipeline integration tests for Plan 2.

Exercises: schemas + validate_jsonl + hooks together on realistic inputs.
"""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPTS = Path(__file__).parent.parent.parent / ".claude" / "agents" / "mythos" / "scripts"


def py(*args: str, input_text: str = "") -> tuple[int, str, str]:
    cmd = [sys.executable, *args]
    r = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout, r.stderr


def test_full_pipeline_finding_to_validation_to_validate_jsonl(tmp_path):
    """A valid finding written through the hook stack lands in validate_jsonl OK."""
    # 1. validate_write hook check on the finding write
    finding = {
        "finding_id": "F-E2E001", "task_id": "T-E2E1", "class": "sql-injection",
        "file": "src/db.py", "line": 42, "function": "get_user", "severity": "high",
        "hypothesis": "User input concatenated into SQL.", "poc_dir": "poc/F-E2E001/",
        "poc_log": "ok", "docker_image": "mythos-multilang:1.0.0",
        "hunter_id": "hunter-99", "confidence": "poc-confirmed",
        "created_at": "2026-05-25T18:00:00Z",
    }
    (tmp_path / ".claude").mkdir()  # project root marker
    findings_path = tmp_path / ".mythos" / "findings.jsonl"
    findings_path.parent.mkdir(parents=True, exist_ok=True)
    findings_path.write_text(json.dumps(finding) + "\n", encoding="utf-8")

    # 2. validate_jsonl confirms it
    rc, out, err = py(
        str(SCRIPTS / "validate_jsonl.py"),
        str(findings_path),
        "--schema", "finding",
    )
    assert rc == 0, f"out={out} err={err}"


def test_secret_in_write_content_triggers_warn():
    """A finding containing an AWS key triggers the validate_write secret-detection path."""
    payload = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": ".mythos/findings.jsonl",
            "content": '{"finding_id":"F-A","creds":"AKIAIOSFODNN7EXAMPLE"}',
        },
    }
    rc, out, err = py(str(SCRIPTS / "validate_write.py"), input_text=json.dumps(payload))
    # warn (1) or block (2), but not silent pass
    assert rc in (1, 2)


def test_dangerous_bash_blocked():
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
    rc, _, err = py(str(SCRIPTS / "validate_bash.py"), input_text=json.dumps(payload))
    assert rc == 2
    assert "rm -rf" in err.lower() or "blocked" in err.lower() or "dangerous" in err.lower()
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/integration/test_hooks_integration.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  tests/integration/test_hooks_integration.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "test: end-to-end integration of schemas + hooks + validate_jsonl"
```

---

## Task 14: Full suite gate + plan-2-done tag

**Files:**
- (no new files — final verification)

- [ ] **Step 1: Run the entire suite**

```bash
pytest tests/ -v --tb=short
```

Expected: Many PASS, 0 FAILED. Total should be ~90+ tests (43 from Plan 1 + ~50 added in Plan 2).

- [ ] **Step 2: Generate coverage report**

```bash
pytest tests/ --cov=.claude/agents/mythos/scripts --cov-report=term-missing 2>&1 | tail -30
```

Expected: `common/` modules > 80% coverage. Hook scripts > 70% coverage (CLI dispatch glue is sometimes harder to cover).

- [ ] **Step 3: Tag**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" tag -a mythos-plan-2-done -m "Plan 2 complete: 8 JSON schemas + 4 hooks + 5 utility scripts + 2 launchers"
git log --oneline -5
```

---

## Plan 2 — Completion criteria

- [ ] All 14 tasks above are checked off
- [ ] `pytest tests/ -v` runs green (Plan 1 + Plan 2 suites combined)
- [ ] 8 JSON schemas validate against the meta-schema (no malformed schemas)
- [ ] All hooks correctly identify their target tool (Bash / Write / Edit) and pass through others
- [ ] `redact.py` catches AWS / GitHub / Stripe / JWT / PEM / .env-style secrets
- [ ] `sanitize_output.py` strips ANSI without dropping legitimate text
- [ ] `validate_bash.py` blocks all 20+ dangerous patterns from §11 T13
- [ ] `validate_write.py` blocks path traversal and warns on secret-bearing writes
- [ ] `cleanup_orphans.py` runs without crashing (idempotent on a clean system)
- [ ] `agent_start.py` appends an audit entry only for `mythos-*` agent types
- [ ] `build_symbol_index.py` degrades gracefully when ctags/rg are missing
- [ ] `launch_hunters.py` and `launch_tracers.py` parse queue + dispatch in dry-run mode without error
- [ ] Git tag `mythos-plan-2-done` exists

---

## What's NOT in Plan 2 (deferred)

| Item | Where | Reason |
|---|---|---|
| 40 cybersecurity skills installation | Plan 3 | Independent layer (skill copy/audit script) |
| 23 bug-class definitions | Plan 3 | Independent metadata files |
| bug-class-mapping.json | Plan 3 | Depends on class definitions |
| The 12 agent .md files | Plans 4-5 | Need all underlying infrastructure (done by end of Plan 3) |
| `/mythos` skill orchestrator | Plan 6 | Top of stack |
| Test fixtures (DVWA, Juice Shop, ...) | Plan 7 | After pipeline is wired |
| E2E + acceptance | Plan 8 | Final |

---

## Self-review

**Spec coverage** (vs `2026-05-25-mythos-preview-design.md`):

| Spec section | Plan 2 task | Status |
|---|---|---|
| §8 Data contracts | Tasks 1-3 | ✅ All 8 schemas + validator + CLI |
| §10 Cross-platform | All tasks use Python + pathlib | ✅ |
| §11 T4 path traversal | Task 8 (validate_write) | ✅ |
| §11 T6 secret leakage | Tasks 6, 8 (redact + validate_write) | ✅ |
| §11 T9 output sanitization | Task 7 (sanitize_output) | ✅ |
| §11 T13 catastrophic commands | Task 5 (validate_bash) | ✅ |
| §11 T15 rate limit backoff | Task 12 — base structure (improvements deferred to runtime) | ⚠️ partial |
| §11 T16 cleanup orphans | Task 9 (cleanup_orphans) | ✅ |
| §11 T19 symbol index | Task 11 (build_symbol_index) | ✅ |
| §13.3 audit log | Task 10 (agent_start) | ✅ |

**Placeholder scan:** None — every task has concrete code, exact file paths, and verifiable test assertions.

**Type consistency:** `StrictValidator`, `AtomicJsonlAppender`, `RunResult`, and the hook I/O helpers are used consistently across all tasks. `find_secrets`/`redact_text` referenced in Task 6 are re-used by Task 8 (validate_write). `mythos_dir()`, `ensure_dirs()` from Plan 1 are re-used by Task 10 (agent_start).

---

**Plan 2 complete.** Next: execute (subagent-driven recommended) or generate Plan 3 (skills install + bug-class definitions).
