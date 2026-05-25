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

## (Linux only) Loading the AppArmor profile

```bash
sudo apparmor_parser -r .claude/agents/mythos/docker/apparmor-mythos
```

This is best-effort: if AppArmor isn't installed, Mythos skips this layer and continues with seccomp + cap-drop + namespaces.

## Building the sandbox image

Once Docker Desktop is running and `docker` is on PATH:

```bash
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/ -f .claude/agents/mythos/docker/Dockerfile.multilang
```

First build takes 5-10 minutes (downloads runtimes). Subsequent builds use layer cache and are much faster.
