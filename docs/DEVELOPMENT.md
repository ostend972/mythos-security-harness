# Mythos Preview — Development Guide

How to extend Mythos: add new bug classes, new lead agents, new hooks, new test fixtures.

## Repo layout

```
.claude/
├── agents/mythos/
│   ├── leads/                          # 8 phase orchestrators (.md)
│   ├── workers/                        # 4 working agents (.md)
│   ├── bug-classes/                    # 23 bug-class metadata (.md)
│   ├── schemas/                        # 8 JSON schemas (Draft 2020-12)
│   ├── docker/                         # Dockerfile + seccomp + apparmor
│   └── scripts/                        # all Python helpers + hooks
│       ├── common/                     # shared modules (paths, locking, schema, etc.)
│       └── *.py                        # CLI entry points + hooks
├── skills/                             # 39 cybersecurity skills (installed)
│   └── mythos/SKILL.md                 # the /mythos orchestrator
└── settings.json                       # env, hooks, deny list

docs/superpowers/
├── specs/                              # design doc (immutable spec)
└── plans/                              # 8 implementation plans

tests/
├── unit/                               # ~400 unit tests
├── integration/                        # smoke/E2E tests (slower, Docker-gated)
└── red_team/                           # sandbox escape attempts

test-fixtures/                          # vulnerable apps for E2E
.mythos/                                # runtime state (gitignored)
```

## Adding a new bug class

1. Add the bug class id to `bug-class-mapping.json`. The value must be a real cyber-skill name.
2. Create `.claude/agents/mythos/bug-classes/<class-id>.md` with the required frontmatter (`class_id`, `name`, `applicable_languages`, `severity_default`, `fp_rate_expected`, `skill`).
3. Add the class to the `enum` in `.claude/agents/mythos/schemas/finding.schema.json`.
4. If the cyber-skill isn't already installed, add it to `.claude/agents/mythos/allowed-skills.txt` and re-run `install_skills.py`.
5. Add at least 3 test cases to `tests/unit/test_bug_classes.py`.

## Adding a new worker or lead agent

1. Decide: is it a worker (does the work, narrow scope) or a lead (orchestrates a phase)?
2. Create `.claude/agents/mythos/workers/<name>.md` (or `leads/<name>.md`) with:
   - Required frontmatter: `name`, `description`, `version`, `model: opus`, `effort: max`, `tools`, `permissionMode`, hooks
   - A `# TRUST BOUNDARY` section in the body (anti-injection guardrail)
3. Update `tests/unit/test_worker_definitions.py` (or `test_lead_definitions.py`) to include the new agent.
4. If the new agent should be spawnable by another, add `Agent(<name>)` to the spawning agent's `tools` field.

## Adding a new hook

1. Write the hook script in `.claude/agents/mythos/scripts/`. It must:
   - Read JSON from stdin (`common.hook_io.read_hook_input`)
   - Exit 0 (allow), 1 (warn), or 2 (block)
2. Add the wire entry in `.claude/settings.json` under `hooks.PreToolUse`, `PostToolUse`, `SubagentStart`, etc.
3. Write tests in `tests/unit/test_<hook>.py` that pipe JSON via subprocess and assert exit codes.

## Adding a new test fixture

1. Pick a small, well-known vulnerable app.
2. Add it to `FIXTURE_REGISTRY` in `test-fixtures/fetch_fixtures.py` (kind = `external-clone` or `internal`).
3. Create `test-fixtures/expected/<fixture>-expected-bugs.json` listing ≥ 5 documented bugs with their class.
4. Add a parametrized entry to `tests/unit/test_expected_bugs_schemas.py`.

## Running the test suite

```bash
pytest tests/                # everything except slow
pytest tests/ -m docker      # only Docker-gated tests (smoke, red-team)
pytest tests/ -m slow        # only real claude --agent invocations
pytest tests/ -m "not slow and not docker"  # safest CI subset
```

## CI considerations

- Skip `slow` tests (real Claude API) by default — they're long and require credentials
- Docker tests skip cleanly when daemon is absent
- Coverage: data-safety modules (locking, paths, schema) are 100%; CLI dispatchers are ~50-70%

## Style

- Python: PEP 8, type hints everywhere, `from __future__ import annotations` in modules using union types
- Markdown: ATX-style headings, fenced code blocks
- JSON: 2-space indent for human-readable files, single-line for JSONL streams
- Commit messages: conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`)
- Git identity: ALWAYS inline (`-c user.email=... -c user.name=...`), never modify global config

## Versioning

The whole project versions together via git tags `mythos-plan-<N>-done`. The V1 ship is tagged `mythos-v1-ship`. After V1, regular `vX.Y.Z` tags resume.
