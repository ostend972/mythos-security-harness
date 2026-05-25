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
    """Validates data against a Draft 2020-12 JSON Schema with strict semantics."""

    def __init__(self, schema_name: str, *, schema_dir: Path | None = None) -> None:
        self.schema_name = schema_name
        self._schema_dir = schema_dir or DEFAULT_SCHEMA_DIR
        schema_path = self._schema_dir / f"{schema_name}.schema.json"
        if not schema_path.is_file():
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' not found at {schema_path}"
            )
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(
            self.schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    def validate(self, data: dict) -> None:
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
