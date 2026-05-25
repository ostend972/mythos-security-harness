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
