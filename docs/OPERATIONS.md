# Mythos Preview — Operations Guide

How to install, configure, run, and monitor Mythos Preview.

## Prerequisites

| Tool | Minimum version | Install (Windows / Mac / Linux) |
|---|---|---|
| Python | 3.10 | `winget install Python.Python.3.12` / `brew install python` / `apt install python3.12 python3-pip` |
| Docker Desktop / Engine | 24+ | Download from docker.com — Windows: enable WSL2 backend |
| ripgrep | 13+ | `winget install BurntSushi.ripgrep.MSVC` / `brew install ripgrep` / `apt install ripgrep` |
| universal-ctags | 5.9+ | `winget install universal-ctags.universal-ctags` / `brew install universal-ctags` / `apt install universal-ctags` |
| Claude Code CLI | latest | https://docs.anthropic.com/claude/docs/claude-code |

## First-time setup

```bash
# 1. Install Python dependencies
pip install -r .claude/agents/mythos/scripts/requirements.txt

# 2. Run pre-flight to check every tool
python .claude/agents/mythos/scripts/preflight.py

# 3. Build the Mythos Docker image (5-10 min first time)
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/ -f .claude/agents/mythos/docker/Dockerfile.multilang

# 4. (Linux only) Load the AppArmor profile
sudo apparmor_parser -r .claude/agents/mythos/docker/apparmor-mythos

# 5. Install the curated cyber skills
python .claude/agents/mythos/scripts/install_skills.py

# 6. Acknowledge the dual-use disclaimer (ONE-TIME, mandatory)
python .claude/agents/mythos/scripts/disclaimer.py --accept
```

## Running Mythos

### Inside Claude Code

```
claude
# In the conversation:
/mythos start ./path/to/target
```

The pipeline will execute 8 phases. Each phase takes 5-30 minutes typically.

### Subcommands

| Subcommand | Purpose |
|---|---|
| `/mythos start [target]` | Start a fresh run (default target = current dir) |
| `/mythos status` | Show current phase + task queue progress |
| `/mythos resume` | Resume an interrupted run from the last completed phase |
| `/mythos abort` | Kill all running sub-agents and orphan containers |
| `/mythos clean [--keep-validated]` | Clean the .mythos/ state directory |

### Expected runtime

| Repo size | Approximate duration |
|---|---|
| Small (< 20K LOC) | 30-90 min |
| Medium (50K-200K LOC) | 1-4 hours |
| Large (500K+ LOC) | 4-12 hours |

### Token budget

A medium-size repo run consumes ~30-100M tokens. On Claude Code Max 20x, this is well within forfait limits. If you see throttling, the orchestrator will print a warning.

## Monitoring

- **`/mythos status`** — phase + progress
- **`.mythos/audit.jsonl`** — append-only log of every security event (sandbox kills, prompt-injection detections, secrets redactions). Never erased.
- **`.mythos/logs/<phase>-<timestamp>.jsonl`** — per-phase structured logs
- **`.mythos/metrics.json`** — produced at end-of-run, has per-phase timings + quality stats

## Failure recovery

| Symptom | Action |
|---|---|
| Hunter batch timeout | Re-run `/mythos start` from the failed phase via `/mythos resume` |
| Docker not running | `docker info` to verify; start Docker Desktop; then `/mythos resume` |
| Out of disk space | `/mythos clean` to purge old PoC artifacts |
| Hash chain mismatch on resume | State was tampered. Investigate via `audit.jsonl`. Decide whether to `/mythos clean` and restart |
| 50 hunters orphaned | `python .claude/agents/mythos/scripts/cleanup_orphans.py` |

## Stopping safely

| Approach | Effect |
|---|---|
| `Ctrl+C` in Claude Code | Sub-agents complete their current turn, then exit. Use `/mythos resume` later |
| `/mythos abort` | Snapshots current state, then kills all sub-agents + containers |

## Reporting findings

After a successful run, `.mythos/report.md` has the operator-friendly version and `.mythos/report.json` is machine-readable. PoC artifacts live in `.mythos/poc/F-<id>/`.

For bug bounty submissions: include the PoC files (`run.sh` + source) and the relevant `hypothesis` from the finding.
