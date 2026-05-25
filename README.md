<div align="center">

# 🜲 Mythos Preview

### Multi-agent vulnerability discovery harness for Claude Code

*Inspired by Cloudflare's research pipeline. Built for operators who want **findings with PoCs, not paragraphs of "potentially"**.*

[![Status](https://img.shields.io/badge/status-V1%20ship-success?style=flat-square)](docs/V1-ACCEPTANCE.md)
[![Tests](https://img.shields.io/badge/tests-436%20passing-brightgreen?style=flat-square)](tests/)
[![Sandbox](https://img.shields.io/badge/red--team-6%2F6%20blocked-success?style=flat-square)](docs/SECURITY.md)
[![Model](https://img.shields.io/badge/model-Opus%204.7%20%C2%B7%20effort%3Dmax-blueviolet?style=flat-square)](https://code.claude.com/docs/fr/sub-agents)
[![Platform](https://img.shields.io/badge/Win11%20%C2%B7%20macOS%20%C2%B7%20Linux-supported-informational?style=flat-square)](docs/OPERATIONS.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-lightgrey?style=flat-square)](LICENSE)

</div>

---

## What it does

You point Mythos at a repository. Eight specialized agents pick it apart in parallel, each chasing one vulnerability class through one function at a time. Hunters write proof-of-concept exploits, compile them in a hardened Docker sandbox, and execute them. An adversarial validator generates **its own independent PoC** for every claim and drops anything that doesn't reproduce twice.

What you get is a `report.md` of bugs you can act on — each one backed by a runnable PoC, ordered by severity × reachability. No "may", no "potentially", no "in theory".

## The pipeline

```
                  ┌─────────────────────────────────────────────────────────────────┐
                  │                  CLAUDE CODE  ·  /mythos start                  │
                  └────────────────────────────┬────────────────────────────────────┘
                                               ▼
   ┌──── 1. RECON ────┐    arch + build + 100-500 narrow tasks
   │   mythos-recon   │ ────────────────────────────────────────────► architecture.md
   │  spawns scouts × N│                                                task-queue.jsonl
   └──────────────────┘
                                               ▼
   ┌──── 2. HUNT ─────┐    50 hunters × Opus + effort=max, in parallel
   │ mythos-hunt-lead │ ────────────────────────────────────────────► findings.jsonl
   │  spawns hunters   │     each writes PoC, runs in Docker sandbox    coverage.jsonl
   │       × 50        │     no PoC = no finding (schema-enforced)        poc/F-XXX/
   └──────────────────┘
                                               ▼  ┌──── 4. GAPFILL ────┐
   ┌──── 3. VALIDATE ─┐   devil's advocate.    │  │  spots coverage    │
   │ mythos-validate  │   writes INDEPENDENT   │  │  gaps, requeues    │
   │ no Agent tool    │ ─ PoC. drops on disagreement.  └────────┬──────┘
   │ (anti-correlation)│                       ▲                │ loop ×3
   └──────────────────┘                        └────────────────┘
                                               ▼
   ┌──── 5. DEDUPE ───┐ ─► dedup-clusters.json
   ├──── 6. TRACE ────┤    1 tracer per consumer repo  ────────► traces/*.json
   │ mythos-trace     │    "is this REACHABLE from outside?"
   ├──── 7. FEEDBACK ─┤    reachable → new Hunt tasks  ──── loop ×1
   ├──── 8. REPORT ───┤ ─► report.md  +  report.json  (schema-validated)
   └──────────────────┘
```

## The big numbers

| | |
|---:|:---|
| **12** | specialized Claude Opus 4.7 agents (8 leads + 4 workers) |
| **23** | supported bug classes (SQLi, SSRF, deserialization, JWT confusion, UAF, OOB R/W, IDOR, BFLA, mass-assignment, prototype pollution, SSTI, race condition, double-free, format string, …) |
| **39** | curated cybersecurity skills, audited before install |
| **9** | stacked Docker security layers (seccomp + AppArmor + cap-drop + read-only + non-root + no-network + cgroup-ns + ulimits + pids_limit) |
| **8** | JSON schemas, Draft 2020-12, strict (`additionalProperties: false`) |
| **6** | red-team escape attempts — **all blocked** |
| **436** | tests passing (unit + integration + red-team) |
| **20** | documented threats with explicit mitigations |
| **100%** | code coverage on the critical data-safety modules (paths, locking, redact) |
| **0** | findings without a working PoC |

## Quick start

```bash
# 1. Prereqs (Win/Mac/Linux)
pip install -r .claude/agents/mythos/scripts/requirements.txt
docker build -t mythos-multilang:1.0.0 \
  .claude/agents/mythos/docker/ \
  -f .claude/agents/mythos/docker/Dockerfile.multilang
python .claude/agents/mythos/scripts/install_skills.py

# 2. Verify
python .claude/agents/mythos/scripts/preflight.py
python .claude/agents/mythos/scripts/disclaimer.py --accept

# 3. Run
claude
```

In Claude Code:

```
/mythos start ./your-target-repo
```

Then sit back. Mythos snapshots the state before each phase, computes a SHA-256 hash chain over the workspace, and writes an append-only audit log. If you Ctrl-C halfway through, `/mythos resume` picks up where you left off.

## Why it's different from "point an AI at a repo and ask for vulns"

| Naive approach | Mythos |
|---|---|
| One agent tries to find everything | 50 hunters in parallel, each scoped to ONE bug class × ONE function |
| "Potentially exploitable" → human triage | Schema-enforced `confidence: poc-confirmed` only |
| Same model reviews its own work | `mythos-validate` is **denied the `Agent` tool** — it writes an independent PoC from scratch |
| PoC runs on your machine | Hardened ephemeral Docker container, 9 isolation layers |
| Secrets leak into reports | `redact.py` pipeline scrubs AWS/GitHub/Stripe/JWT/PEM/.env before any write |
| Catastrophic commands ride along | `PreToolUse` hook blocks 22 patterns (`rm -rf /`, `~/.ssh/*`, `docker.sock`, sudo, …) |

## Documentation

| | |
|---|---|
| 🚀 [**OPERATIONS.md**](docs/OPERATIONS.md) | Install, configure, run, monitor, recover |
| 🛠️ [**DEVELOPMENT.md**](docs/DEVELOPMENT.md) | Add bug classes, agents, hooks, fixtures |
| 🛡️ [**SECURITY.md**](docs/SECURITY.md) | 20-threat model with mitigations + audit log |
| ✅ [**V1-ACCEPTANCE.md**](docs/V1-ACCEPTANCE.md) | 16-criterion ship checklist |
| 📐 [**Design spec**](docs/superpowers/specs/2026-05-25-mythos-preview-design.md) | Full 1,400-line architecture document |
| 📋 [**Plans 1-8**](docs/superpowers/plans/) | Implementation plans, ~15K lines total |

## Architecture in one paragraph

12 Claude Code agents (`.claude/agents/mythos/`) — 8 leads orchestrate the phases, 4 workers do the work. The `/mythos` skill drives the pipeline in sequence. Each phase writes JSON/JSONL artifacts validated against strict Draft 2020-12 schemas. Inter-process safety via `filelock` (cross-platform). Sandbox via `docker-py` with a custom seccomp profile + AppArmor (Linux only) + 9 layers. State persistence via tar.gz snapshots + SHA-256 hash chain over the workspace. Hooks block dangerous Bash patterns, paths outside `.mythos/`, and secret-bearing writes. Every Mythos sub-agent invocation appends to `.mythos/audit.jsonl` (append-only, survives `clean`).

## ⚠️ Dual-use disclaimer

Mythos generates **functional, weaponized exploit code**. Use only on:

1. Code you own
2. Code in scope of an authorized bug bounty
3. Code under signed pen-test engagement
4. Code in authorized security research

Unauthorized use is illegal in most jurisdictions. First-run requires explicit `disclaimer.py --accept`.

## Status

**V1 ship-ready** — see [V1-ACCEPTANCE.md](docs/V1-ACCEPTANCE.md). Tag: `mythos-v1-ship`.

## License

Apache 2.0 — see [LICENSE](LICENSE). Vendored cybersecurity skills retain their original licenses.

---

<div align="center">

*Findings, not paragraphs.*

</div>
