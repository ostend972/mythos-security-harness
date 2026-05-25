# Plan 1 Finalization (Docker-dependent steps)

The Plan 1 code is complete and committed (`mythos-plan-1-code-complete` tag).
To officially close Plan 1 and tag `mythos-plan-1-done`, run these Docker-dependent steps once Docker Desktop is running and `docker` is on PATH.

## Prerequisites

1. Docker Desktop running (Windows: open Docker Desktop and wait for the whale icon to be steady)
2. `docker --version` and `docker info` both succeed in your terminal
3. `winget install BurntSushi.ripgrep.MSVC universal-ctags.universal-ctags` (rg + ctags for later plans)

## Step 1: Run preflight

```bash
python .claude/agents/mythos/scripts/preflight.py
```

All 5 checks should be OK.

## Step 2: Build the sandbox image

```bash
docker build -t mythos-multilang:1.0.0 .claude/agents/mythos/docker/ -f .claude/agents/mythos/docker/Dockerfile.multilang
```

5-10 min on first build.

## Step 3: Run the smoke tests

```bash
pytest tests/integration/test_sandbox_smoke.py -v -m docker
```

Expected: 3 PASS.

## Step 4: Run the red-team tests (THE security gate)

```bash
pytest tests/red_team/ -v -m "redteam and docker"
```

Expected: 6 PASS. If ANY of them FAIL, do NOT tag plan-1-done — the sandbox has a hole and must be fixed first.

## Step 5: Tag the milestone

```bash
git tag -a mythos-plan-1-done -m "Plan 1 complete: infrastructure + hardened sandbox passes red-team"
```

Plan 1 is now officially complete. Proceed to Plan 2 (data contracts + hooks + utility scripts).
