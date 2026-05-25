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
