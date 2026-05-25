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
        v.validate({"id": "T-001", "name": "alpha"})

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
