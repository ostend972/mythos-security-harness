# Mythos Preview

**A multi-agent vulnerability discovery harness for Claude Code, inspired by Cloudflare's pipeline.**

Mythos Preview runs an 8-phase research pipeline (Recon → Hunt → Validate → Gapfill → Dedupe → Trace → Feedback → Report) using 12 specialized Claude Opus 4.7 agents. It hunts vulnerabilities in your code, writes a proof-of-concept exploit for each finding, and reports only confirmed bugs.

## Quick start

```bash
# Install
pip install -r .claude/agents/mythos/scripts/requirements.txt
python .claude/agents/mythos/scripts/preflight.py
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/ -f .claude/agents/mythos/docker/Dockerfile.multilang
python .claude/agents/mythos/scripts/install_skills.py
python .claude/agents/mythos/scripts/disclaimer.py --accept

# Run
claude
# inside Claude Code:
/mythos start ./your-target-repo
```

The pipeline will produce `.mythos/report.md` with all confirmed findings, each backed by a runnable PoC in `.mythos/poc/F-<id>/`.

## Features

- **12 specialized agents** — 8 phase orchestrators + 4 workers, all on Opus 4.7 + effort=max
- **Hardened sandbox** — 9 stacked Docker security layers, validated by 6 red-team tests
- **No false positives** — schema-enforced "no PoC = drop" policy; Validate generates independent PoCs
- **23 bug classes** — SQL injection, SSRF, deserialization, JWT confusion, race conditions, UAF, OOB R/W, format-string, IDOR, BFLA, mass-assignment, OAuth misconfig, prototype pollution, SSTI, …
- **39 curated cybersecurity skills** — installed from Anthropic-Cybersecurity-Skills, audited before install
- **Cross-platform** — Windows 11 / macOS / Linux, Python helpers everywhere
- **Resumable** — snapshot before each phase + hash-chain integrity check
- **Audit log** — append-only, captures every security event

## Documentation

- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — Install, run, monitor, recover
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — How to extend (new bug classes, new agents, new hooks)
- [`docs/SECURITY.md`](docs/SECURITY.md) — Threat model + defense-in-depth
- [`docs/V1-ACCEPTANCE.md`](docs/V1-ACCEPTANCE.md) — V1 acceptance checklist
- [`docs/superpowers/specs/2026-05-25-mythos-preview-design.md`](docs/superpowers/specs/2026-05-25-mythos-preview-design.md) — Full design spec

## ⚠️ Dual-use disclaimer

Mythos Preview produces functional, weaponized exploit code. Use only on:

1. Code you own
2. Code in scope of an authorized bug bounty
3. Code under signed pen-test engagement
4. Code in authorized security research

Unauthorized use is illegal in most jurisdictions.

## License

Apache 2.0 (cyber skills) + project-specific (this orchestration code) — see `LICENSE`.

## Status

V1 — see [`docs/V1-ACCEPTANCE.md`](docs/V1-ACCEPTANCE.md).
