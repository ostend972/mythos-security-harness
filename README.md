# Mythos Preview

Vulnerability discovery harness for Claude Code, inspired by Cloudflare's pipeline.

**Status:** In development (Plan 1: Infrastructure & Sandbox)

See `docs/superpowers/specs/2026-05-25-mythos-preview-design.md` for the full design.

## Prerequisites

- Python 3.10+
- Docker Desktop (Windows/Mac) or Docker Engine 24+ (Linux)
- On Windows: WSL2 backend enabled in Docker Desktop
- `winget install Python.Python.3.12` (Windows) / `brew install python` (Mac) / `apt install python3.12 python3-pip` (Linux)

## Quick start (after this plan completes)

```bash
pip install -r .claude/agents/mythos/scripts/requirements.txt
python .claude/agents/mythos/scripts/preflight.py
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/
pytest tests/ -v
```
