<div align="center">

# 🜲 Mythos Preview

### Multi-agent vulnerability discovery harness for Claude Code

*Built for operators who want **findings with PoCs, not paragraphs of "potentially"**.*

**🇬🇧 English** &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md)

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
   │ spawns scouts × N│                                                task-queue.jsonl
   └──────────────────┘
                                               ▼
   ┌──── 2. HUNT ─────┐    50 hunters × Opus + effort=max, in parallel
   │ mythos-hunt-lead │ ────────────────────────────────────────────► findings.jsonl
   │ spawns hunters   │     each writes PoC, runs in Docker sandbox    coverage.jsonl
   │       × 50       │     no PoC = no finding (schema-enforced)      poc/F-XXX/
   └──────────────────┘
                                               ▼  ┌──── 4. GAPFILL ────┐
   ┌──── 3. VALIDATE ─┐   devil's advocate.       │  spots coverage    │
   │ mythos-validate  │   writes INDEPENDENT      │  gaps, requeues    │
   │ no Agent tool    │ ─ PoC. drops on disagreement.└────────┬──────┘
   │ (anti-correlation)│                          ▲           │ loop ×3
   └──────────────────┘                           └───────────┘
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

---

## 🔬 How Mythos works — deep technical walkthrough

This section explains the internal mechanics for engineers who want to understand or extend the harness.

### Why 8 phases instead of one big agent?

A single agent pointed at a repository drifts. It picks a thread, follows it, runs out of context, and forgets the other 95% of the surface. Mythos instead **decomposes the problem along two axes** at once:

1. **Phase axis** (vertical) — Recon establishes shared context; Hunt finds claims; Validate destroys claims; Gapfill widens; Dedupe collapses; Trace contextualizes; Feedback closes the loop; Report ships.
2. **Worker axis** (horizontal) — each phase that does real work fans out to many narrow workers, each scoped to *one bug class × one function*. The lead agent does not analyze code; it only coordinates.

This decoupling means the agent that finds a bug is **different** from the agent that confirms it, which is **different** from the agent that traces its reachability. Each is the right tool for its question.

### Agent topology

```
                       /mythos skill (orchestrator)
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
    8 LEADS                  12 AGENTS                4 WORKERS
    (one per phase)            total                  (do the work)
        │                                                  │
        ├─ mythos-recon  ───spawns N────► mythos-scout
        ├─ mythos-hunt-lead ──launches via subprocess──►  mythos-hunter × 50
        │                                                  │
        │                                                  └─spawns──► mythos-explorer
        ├─ mythos-validate  (no Agent tool — anti-correlation)
        ├─ mythos-gapfill   (reads coverage gaps, requeues)
        ├─ mythos-dedupe    (clusters findings by root cause)
        ├─ mythos-trace ────spawns M────► mythos-tracer (one per consumer repo)
        ├─ mythos-feedback  (turns reachable traces into new tasks)
        └─ mythos-report    (schema-validated final output)
```

Every agent runs **Claude Opus 4.7 with `effort: max`**. The model file lists 11 of the 12 agents as standard Claude Code sub-agents; the 50 parallel hunters are spawned as **separate `claude --agent mythos-hunter -p "..."` subprocesses** via a Python launcher script — this is how we get true 50-wide parallelism while staying within sub-agent semantics.

### The anti-correlation principle

The single highest-impact design choice in Mythos is: **the agent that confirms a finding is not allowed to use the tools that created it**.

`mythos-validate`'s frontmatter declares `tools: Read, Bash, Write` — there is **no `Agent` tool**. It cannot spawn helpers. It cannot ask another model to second-opinion. It must read the source code independently, write its own PoC from scratch, execute it in the sandbox, and only then look at the hunter's claim. A finding survives only if **both PoCs reproduce the same root cause**.

The structural test `test_validate_lead_does_not_have_agent_tool` enforces this at the file level — it would fail the build if someone accidentally widened Validate's toolset.

### The "no PoC = no finding" gate

`finding.schema.json` declares:

```json
"confidence": {
  "type": "string",
  "enum": ["poc-confirmed"]
}
```

The enum has **exactly one value**. There is no `suspected`, no `theoretical`, no `medium-confidence`. A finding without a working PoC cannot serialize to a schema-valid record, so it cannot enter `findings.jsonl`. This is the structural mechanism behind the "no paragraphs of potentially" promise.

When a hunter exhausts its 5 hypothesis-revision iterations without a successful PoC execution, it writes **only** a `coverage.jsonl` record (which uses a different schema) and exits with `NO_FINDING`. The bug never reaches Validate.

### The sandbox — 9 stacked layers

When a hunter executes a PoC, the container is constrained by:

| Layer | Mechanism | Threat it stops |
|---|---|---|
| 1 | `cap_drop=ALL` | All Linux capabilities revoked — `CAP_SETUID`, `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, etc. |
| 2 | `no-new-privileges=true` | SUID binaries inside the container cannot escalate |
| 3 | Custom seccomp profile | ~190 syscalls whitelisted; `mount`, `ptrace`, `bpf`, `setns`, `unshare`, `kexec_*`, kernel module ops — all denied |
| 4 | AppArmor profile (Linux only) | Deny rules for `/proc/sysrq-trigger`, `/sys/kernel/security`, `/etc/shadow`, `/root/**` |
| 5 | `read_only=True` root FS | Container cannot persist writes outside two tmpfs mounts |
| 6 | `user=1000:1000` | Runs as a dedicated non-root user (UID 1000) |
| 7 | `network_mode=none` | Zero outbound network by default; OAST callbacks use an isolated internal network |
| 8 | Resource limits | `pids_limit=100`, `mem_limit=512m`, `cpu_quota=100000` (= 1 CPU), `ulimit nofile=256 nproc=200` |
| 9 | `cgroupns=private` | Container has its own cgroup namespace |

The red-team test suite verifies each layer independently. 6 escape attempts (`/etc/passwd` isolation, `setuid(0)`, fork bomb, network egress, `docker.sock` access, `mount` syscall) — **all 6 blocked**.

### What happens inside one hunter

```
INPUT (from launch_hunters.py via --prompt):
  task = {
    task_id: "T-A1B2",
    class: "sql-injection",
    scope: "src/api/users.py:update_profile",
    subsystem: "api",
    trust_boundary: "HTTP request",
    priority: 1,
    status: "in_progress"
  }
  architecture_md_excerpt = "<the relevant slice of architecture.md>"

WORKFLOW (max 50 turns, hard timeout 600s):
  1. Parse task.class → lookup bug-class-mapping.json → "exploiting-sql-injection-vulnerabilities"
  2. Invoke Skill(exploiting-sql-injection-vulnerabilities) → loads expert workflow
  3. Read bug-class metadata at .claude/agents/mythos/bug-classes/sql-injection.md
     (indicators, hunting hints, PoC strategy)
  4. Read the target file/function + ≤ 5 related files
  5. Form an exploitability hypothesis
  6. (Optional) Spawn mythos-explorer for one deep dive
  7. Write PoC to .mythos/poc/F-<id>/{run.sh, source.<ext>, expected.log}
  8. Execute: python mythos_sandbox.py run F-<id>
  9. Read result. Iterate 4-8 up to 5 times.
 10. Confirmed → append to findings.jsonl (file-locked, append-only)
     Failed → append only to coverage.jsonl, exit NO_FINDING

OUTPUT contract:
  - findings.jsonl line MUST validate against finding.schema.json
  - coverage.jsonl line MUST validate against coverage.schema.json
  - PostToolUse hook validate_write.py rejects writes outside allowed paths
  - PreToolUse hook validate_bash.py rejects 22 catastrophic command patterns
```

The hunter is intentionally narrow. It does **not** explore the architecture — `mythos-recon` did that. It does **not** decide what to chase — `mythos-hunt-lead` assigned it one task. It does **not** judge severity in isolation — `mythos-validate` will reproduce it. This narrowness is what makes 50 hunters in parallel productive instead of redundant.

### Cross-process safety

Mythos runs as a single Claude Code conversation but spawns **51+ concurrent processes** during Hunt (`mythos-hunt-lead` + 50 hunters via `claude --agent`) plus 50 ephemeral Docker containers. The state directory `.mythos/` is shared between all of them. Three mechanisms keep it consistent:

| File | Concurrency strategy |
|---|---|
| `findings.jsonl`, `coverage.jsonl`, `task-queue.jsonl` | Append-only, every append goes through `AtomicJsonlAppender` (uses `filelock`, OS-level locks via `LockFileEx` on Windows / `fcntl` elsewhere) |
| `run.json`, `dedup-clusters.json`, `symbols.json` | Atomic overwrite via `write to tmp → os.replace()` |
| `.mythos/poc/F-<id>/` | One directory per finding, never shared. No locking needed. |

The 20-thread concurrent-append test in `test_locking.py` verifies that 20 simultaneous workers can each append 5 records without losing or corrupting any line.

### State integrity & resume

Before each phase, `snapshot_run.py`:
1. Computes a **SHA-256 hash chain** over every file in `.mythos/` (excluding `snapshots/` itself)
2. Writes a `.tar.gz` snapshot of the current state under `.mythos/snapshots/pre-<phase>-<timestamp>.tar.gz`
3. Updates `run.json` with the new phase + the new hash

If the operator runs `/mythos resume` later, the orchestrator:
1. Reads `run.json`, recomputes the hash chain, **refuses to proceed if the chain doesn't match** (state was modified out-of-band)
2. Restores the snapshot taken just before the last incomplete phase
3. Continues the pipeline from that phase

This means a session crash mid-Hunt is non-fatal: the operator loses the in-flight hunters' work but everything previous (Recon, prior validated batches) is intact.

### Why JSON Schema Draft 2020-12 + `additionalProperties: false`

Strict schemas make the data layer **executable specification**. The schema is the contract. If a future contributor changes `mythos-hunter.md`'s output without updating the schema, the next write call fails loudly. The 8 schemas are validated against the JSON Schema meta-schema at construction time (`Draft202012Validator.check_schema`) — so a malformed schema fails on import, not at first use.

`additionalProperties: false` everywhere means a hunter cannot "improvise" extra fields. If a model invents `{ "confidence": "high-but-not-poc" }` to dodge the strict enum, the line is rejected before being written.

### Cross-platform Python everything

All scripts are Python 3.10+. Cross-platform paths via `pathlib`. Cross-platform locking via `filelock` (uses `LockFileEx` on Windows, `fcntl` elsewhere). Cross-platform Docker via `docker-py`. Cross-platform process management via `psutil`. The seccomp profile is loaded **inline as JSON content** in `security_opt` rather than as a file path because Docker Desktop on Windows with WSL2 backend cannot reliably read `/mnt/c/...` paths for seccomp profiles — a quirk discovered during the red-team validation phase.

### What about secret leakage?

`redact.py` ships with patterns for AWS access keys, GitHub tokens (`gh{p,o,u,s,r}_…`), Stripe live/test keys, JWTs, PEM private keys, and `.env`-style `KEY=value` lines with high-entropy values ≥ 16 chars. The `validate_write.py` PostToolUse hook scans every Write/Edit content; if a pattern matches, the write is downgraded to a warning (not blocked, because a hunter may legitimately include a high-entropy payload in a PoC) but emits an audit log entry.

The audit log `.mythos/audit.jsonl` is append-only and survives `/mythos clean` (unless `--all` is passed). Every security-relevant event is recorded with a timestamp.

---

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
