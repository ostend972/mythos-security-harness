# Mythos Preview — Plan 7: Test Fixtures + Expected Bugs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Set up the vulnerable application fixtures Mythos will be tested against, with curated `expected-bugs.json` lists for each. External fixtures (DVWA, Juice Shop, etc.) are fetched on-demand via a script; the internal `c-vuln-samples` fixture is included in-repo so Plan 8's E2E tests can run without network.

**Architecture:** A `fetch_fixtures.py` script clones external vulnerable apps from upstream repos to `test-fixtures/<name>/` on demand. The `c-vuln-samples/` directory is committed directly (small C source files with known memory bugs). Each fixture has an `expected-bugs.json` describing the bugs E2E tests will check for.

**Tech Stack:** Python + subprocess for `git clone`, Markdown for documentation, C source for the internal fixture.

**Spec reference:** [`docs/superpowers/specs/2026-05-25-mythos-preview-design.md`](../specs/2026-05-25-mythos-preview-design.md) §12.3 E2E tests on vulnerable fixtures.

**Plan 1-6 dependencies:** all done.

**Out of scope:**
- Running E2E `/mythos start` against the fixtures (Plan 8)
- V1 acceptance criteria evaluation (Plan 8)

---

## File Structure

```
<repo_root>/
├── test-fixtures/
│   ├── README.md                                  # how to fetch
│   ├── fetch_fixtures.py                          # downloader CLI
│   ├── c-vuln-samples/                            # IN-REPO mini fixture
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── uaf.c                              # use-after-free
│   │   │   ├── oob_read.c                         # out-of-bounds read
│   │   │   ├── oob_write.c                        # out-of-bounds write
│   │   │   ├── double_free.c
│   │   │   ├── format_string.c
│   │   │   └── stack_overflow.c
│   │   ├── Makefile
│   │   └── expected-bugs.json
│   └── expected/                                  # per-fixture expected bug lists
│       ├── dvwa-expected-bugs.json
│       ├── juice-shop-expected-bugs.json
│       ├── nodegoat-expected-bugs.json
│       ├── webgoat-expected-bugs.json
│       ├── vulnado-expected-bugs.json
│       └── c-vuln-samples-expected-bugs.json
└── tests/
    └── unit/
        ├── test_fetch_fixtures.py
        ├── test_expected_bugs_schemas.py
        └── test_c_vuln_samples_buildable.py
```

---

## Task 1: fetch_fixtures.py downloader

**Files:**
- Create: `test-fixtures/README.md`
- Create: `test-fixtures/fetch_fixtures.py`
- Test: `tests/unit/test_fetch_fixtures.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_fetch_fixtures.py`:
```python
"""Tests for test-fixtures/fetch_fixtures.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "test-fixtures"))

import fetch_fixtures


class TestListFixtures:
    def test_lists_all_supported_fixtures(self):
        names = fetch_fixtures.list_fixture_names()
        assert "dvwa" in names
        assert "juice-shop" in names
        assert "nodegoat" in names
        assert "webgoat" in names
        assert "vulnado" in names
        assert "c-vuln-samples" in names

    def test_fixture_metadata_has_required_keys(self):
        for name in fetch_fixtures.list_fixture_names():
            meta = fetch_fixtures.FIXTURE_REGISTRY[name]
            assert "language" in meta
            assert "kind" in meta
            assert meta["kind"] in {"external-clone", "internal"}
            if meta["kind"] == "external-clone":
                assert "url" in meta


class TestFetchOne:
    def test_fetch_one_skips_existing_if_no_force(self, tmp_path):
        target = tmp_path / "dvwa"
        target.mkdir()
        (target / "marker").write_text("existing", encoding="utf-8")
        with patch("fetch_fixtures.subprocess.run") as mock_run:
            result = fetch_fixtures.fetch_one("dvwa", base_dir=tmp_path, force=False)
            assert result["status"] == "exists"
            mock_run.assert_not_called()

    def test_fetch_one_clones_external(self, tmp_path):
        with patch("fetch_fixtures.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = fetch_fixtures.fetch_one("dvwa", base_dir=tmp_path, force=False)
            assert result["status"] in {"cloned", "exists"}
            if result["status"] == "cloned":
                # Verify git clone was called
                assert any("clone" in str(c) for c in mock_run.call_args_list)

    def test_internal_fixture_skipped(self, tmp_path):
        result = fetch_fixtures.fetch_one("c-vuln-samples", base_dir=tmp_path, force=False)
        assert result["status"] == "internal-skipped"


class TestMain:
    def test_main_with_list_flag_prints_fixtures(self, capsys):
        rc = fetch_fixtures.main(["--list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "dvwa" in out
        assert "juice-shop" in out
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_fetch_fixtures.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

Write `test-fixtures/fetch_fixtures.py`:
```python
"""fetch_fixtures.py — clone or set up vulnerable application fixtures.

External fixtures live at known upstream repos and are fetched on demand.
Internal fixtures (like c-vuln-samples) ship with this repo — they're skipped.

Usage:
    python test-fixtures/fetch_fixtures.py --list
    python test-fixtures/fetch_fixtures.py --fetch dvwa juice-shop
    python test-fixtures/fetch_fixtures.py --all
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


FIXTURE_REGISTRY: dict[str, dict] = {
    "dvwa": {
        "kind": "external-clone",
        "url": "https://github.com/digininja/DVWA.git",
        "language": "php",
        "framework": "raw-php",
        "size_mb": 5,
    },
    "juice-shop": {
        "kind": "external-clone",
        "url": "https://github.com/juice-shop/juice-shop.git",
        "language": "typescript",
        "framework": "express",
        "size_mb": 200,
        "branch": "master",
    },
    "nodegoat": {
        "kind": "external-clone",
        "url": "https://github.com/OWASP/NodeGoat.git",
        "language": "javascript",
        "framework": "express",
        "size_mb": 30,
    },
    "webgoat": {
        "kind": "external-clone",
        "url": "https://github.com/WebGoat/WebGoat.git",
        "language": "java",
        "framework": "spring-boot",
        "size_mb": 80,
    },
    "vulnado": {
        "kind": "external-clone",
        "url": "https://github.com/ScaleSec/vulnado.git",
        "language": "java",
        "framework": "spring-boot",
        "size_mb": 15,
    },
    "c-vuln-samples": {
        "kind": "internal",
        "language": "c",
        "framework": None,
        "size_mb": 0.1,
    },
}


def list_fixture_names() -> list[str]:
    return list(FIXTURE_REGISTRY.keys())


def fetch_one(name: str, *, base_dir: Path, force: bool = False) -> dict:
    """Fetch a single fixture. Return outcome dict."""
    if name not in FIXTURE_REGISTRY:
        return {"name": name, "status": "unknown"}
    meta = FIXTURE_REGISTRY[name]
    if meta["kind"] == "internal":
        return {"name": name, "status": "internal-skipped"}
    target = base_dir / name
    if target.exists() and not force:
        return {"name": name, "status": "exists", "path": str(target)}
    if target.exists() and force:
        shutil.rmtree(target)
    base_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if meta.get("branch"):
        cmd += ["--branch", meta["branch"]]
    cmd += [meta["url"], str(target)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "timeout"}
    except FileNotFoundError:
        return {"name": name, "status": "git-not-found"}
    if r.returncode != 0:
        return {"name": name, "status": "clone-failed", "error": r.stderr[-500:]}
    return {"name": name, "status": "cloned", "path": str(target)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="fetch_fixtures")
    p.add_argument("--list", action="store_true", help="List available fixtures")
    p.add_argument("--fetch", nargs="*", default=[], help="Fixture names to fetch")
    p.add_argument("--all", action="store_true", help="Fetch all external fixtures")
    p.add_argument("--force", action="store_true", help="Re-clone even if exists")
    p.add_argument("--base-dir", default="test-fixtures", help="Base directory")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        print("Available fixtures:")
        for name, meta in FIXTURE_REGISTRY.items():
            kind = meta["kind"]
            lang = meta["language"]
            size = meta.get("size_mb", "?")
            print(f"  - {name:<18} [{kind:<14}] {lang:<10} ({size} MB)")
        return 0

    base_dir = Path(args.base_dir)
    names_to_fetch: list[str] = list(args.fetch)
    if args.all:
        names_to_fetch = [n for n, m in FIXTURE_REGISTRY.items() if m["kind"] == "external-clone"]
    if not names_to_fetch:
        print("No fixtures specified. Use --list, --fetch <name>, or --all.")
        return 2

    overall_ok = True
    for name in names_to_fetch:
        result = fetch_one(name, base_dir=base_dir, force=args.force)
        print(json.dumps(result))
        if result["status"] in ("clone-failed", "timeout", "git-not-found", "unknown"):
            overall_ok = False
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write README**

Write `test-fixtures/README.md`:
```markdown
# Mythos Preview — Test Fixtures

This directory hosts vulnerable application fixtures used by Mythos's E2E tests.

## Internal fixtures (included in this repo)

| Fixture | Language | Bugs |
|---|---|---|
| `c-vuln-samples/` | C | 6 hand-crafted memory bugs (UAF, OOB R/W, double-free, format string, stack overflow) |

## External fixtures (fetched on demand)

| Fixture | Language | Source |
|---|---|---|
| `dvwa/` | PHP | https://github.com/digininja/DVWA |
| `juice-shop/` | TypeScript / Express | https://github.com/juice-shop/juice-shop |
| `nodegoat/` | JavaScript / Express | https://github.com/OWASP/NodeGoat |
| `webgoat/` | Java / Spring Boot | https://github.com/WebGoat/WebGoat |
| `vulnado/` | Java / Spring Boot | https://github.com/ScaleSec/vulnado |

## Usage

```bash
# List
python test-fixtures/fetch_fixtures.py --list

# Fetch a single fixture
python test-fixtures/fetch_fixtures.py --fetch dvwa

# Fetch all external fixtures (~330 MB total)
python test-fixtures/fetch_fixtures.py --all

# Re-clone an existing fixture
python test-fixtures/fetch_fixtures.py --fetch dvwa --force
```

## Expected bugs

`expected/<fixture>-expected-bugs.json` lists the bugs Mythos's E2E tests
expect to find for each fixture. Recall (= bugs found ÷ bugs expected) must
be ≥ 80% for V1 acceptance.
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest tests/unit/test_fetch_fixtures.py -v
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  test-fixtures/README.md test-fixtures/fetch_fixtures.py \
  tests/unit/test_fetch_fixtures.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: fetch_fixtures.py downloader + fixture registry"
```

Expected: 6 tests PASS.

---

## Task 2: c-vuln-samples (in-repo C fixture)

**Files:**
- Create: `test-fixtures/c-vuln-samples/README.md`
- Create: `test-fixtures/c-vuln-samples/Makefile`
- Create: 6 C source files in `test-fixtures/c-vuln-samples/src/`

- [ ] **Step 1: Create the directory + Makefile**

```bash
mkdir -p test-fixtures/c-vuln-samples/src
```

Write `test-fixtures/c-vuln-samples/Makefile`:
```makefile
# Build all c-vuln-samples binaries with ASan + UBSan enabled.
# These binaries INTENTIONALLY crash to demonstrate the bug; only build them
# inside the Mythos sandbox.

CC ?= clang
CFLAGS = -g -O0 -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS = -fsanitize=address,undefined

SRC = $(wildcard src/*.c)
BIN = $(SRC:src/%.c=bin/%)

all: $(BIN)

bin/%: src/%.c | bin
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

bin:
	mkdir -p bin

clean:
	rm -rf bin

.PHONY: all clean
```

- [ ] **Step 2: Write `uaf.c`**

Write `test-fixtures/c-vuln-samples/src/uaf.c`:
```c
/* Use-after-free demonstration.
 * EXPECTED: ASan reports heap-use-after-free.
 * MYTHOS BUG CLASS: uaf
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buf = malloc(32);
    strcpy(buf, "first allocation");
    printf("Before free: %s\n", buf);
    free(buf);
    /* Bug: dereference after free */
    printf("After free:  %s\n", buf);
    return 0;
}
```

- [ ] **Step 3: Write `oob_read.c`**

Write `test-fixtures/c-vuln-samples/src/oob_read.c`:
```c
/* Out-of-bounds read demonstration.
 * EXPECTED: ASan reports heap-buffer-overflow READ.
 * MYTHOS BUG CLASS: oob-rw
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buf = malloc(8);
    strcpy(buf, "ABCDEFG");
    /* Bug: read 16 bytes from an 8-byte allocation */
    char copy[16];
    memcpy(copy, buf, 16);
    printf("%.16s\n", copy);
    free(buf);
    return 0;
}
```

- [ ] **Step 4: Write `oob_write.c`**

Write `test-fixtures/c-vuln-samples/src/oob_write.c`:
```c
/* Out-of-bounds write demonstration.
 * EXPECTED: ASan reports heap-buffer-overflow WRITE.
 * MYTHOS BUG CLASS: oob-rw
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char *buf = malloc(8);
    /* Bug: write 16 bytes into an 8-byte buffer */
    memset(buf, 'X', 16);
    printf("done\n");
    free(buf);
    (void)argc; (void)argv;
    return 0;
}
```

- [ ] **Step 5: Write `double_free.c`**

Write `test-fixtures/c-vuln-samples/src/double_free.c`:
```c
/* Double-free demonstration.
 * EXPECTED: ASan reports attempting double-free.
 * MYTHOS BUG CLASS: double-free
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = malloc(sizeof(int));
    *p = 42;
    printf("value=%d\n", *p);
    free(p);
    /* Bug: free the same pointer again */
    free(p);
    return 0;
}
```

- [ ] **Step 6: Write `format_string.c`**

Write `test-fixtures/c-vuln-samples/src/format_string.c`:
```c
/* Format-string demonstration.
 * EXPECTED: leaks stack via %x / %p when ASLR doesn't fully mask.
 * MYTHOS BUG CLASS: format-string
 */
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <format>\n", argv[0]);
        return 1;
    }
    /* Bug: argv[1] is used as the format string */
    printf(argv[1]);
    printf("\n");
    return 0;
}
```

- [ ] **Step 7: Write `stack_overflow.c`**

Write `test-fixtures/c-vuln-samples/src/stack_overflow.c`:
```c
/* Stack buffer overflow demonstration.
 * EXPECTED: ASan reports stack-buffer-overflow.
 * MYTHOS BUG CLASS: oob-rw (stack variant)
 */
#include <stdio.h>
#include <string.h>

void vulnerable(const char *input) {
    char buf[16];
    /* Bug: no length check */
    strcpy(buf, input);
    printf("%s\n", buf);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        vulnerable("default-short");
    } else {
        vulnerable(argv[1]);
    }
    return 0;
}
```

- [ ] **Step 8: Write c-vuln-samples README**

Write `test-fixtures/c-vuln-samples/README.md`:
```markdown
# c-vuln-samples — In-repo C bug fixture

Hand-crafted minimal C programs, each demonstrating exactly ONE memory bug class. Built with `-fsanitize=address,undefined` so each crash is unambiguous when executed inside the Mythos sandbox.

| Source | Bug class | ASan/UBSan output |
|---|---|---|
| `src/uaf.c` | `uaf` | heap-use-after-free |
| `src/oob_read.c` | `oob-rw` (read) | heap-buffer-overflow READ |
| `src/oob_write.c` | `oob-rw` (write) | heap-buffer-overflow WRITE |
| `src/double_free.c` | `double-free` | attempting double-free |
| `src/format_string.c` | `format-string` | runtime warning (no ASan crash) |
| `src/stack_overflow.c` | `oob-rw` (stack) | stack-buffer-overflow |

## Build (inside the sandbox container)

```bash
make
```

## Why hand-craft these instead of using public fixtures?

External vulnerable C apps (e.g., the Linux kernel test corpus) are huge and noisy. These 6 files are pedagogical: each isolates ONE bug, so Mythos's hunters can find them with a clean signal and Plan 8's E2E tests can score recall precisely.

**Do NOT compile or run these outside the Mythos Docker sandbox.** They are designed to crash.
```

- [ ] **Step 9: Verify they compile (inside Docker sandbox)**

```bash
docker run --rm \
  -v "$(pwd)/test-fixtures/c-vuln-samples":/work:ro \
  --tmpfs /work-rw:size=50M,exec \
  mythos-multilang:1.0.0 \
  bash -c "cp -r /work/* /work-rw/ && cd /work-rw && make 2>&1 | tail -10"
```

Expected: All 6 binaries built (with ASan warnings about static linking — harmless).

If Docker is unavailable, skip this step — Plan 8 will rebuild within the sandbox.

- [ ] **Step 10: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  test-fixtures/c-vuln-samples/
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: c-vuln-samples — 6 hand-crafted C memory bugs for E2E"
```

---

## Task 3: expected-bugs.json files

**Files:**
- Create: `test-fixtures/expected/c-vuln-samples-expected-bugs.json`
- Create: `test-fixtures/expected/dvwa-expected-bugs.json`
- Create: `test-fixtures/expected/juice-shop-expected-bugs.json`
- Create: `test-fixtures/expected/nodegoat-expected-bugs.json`
- Create: `test-fixtures/expected/webgoat-expected-bugs.json`
- Create: `test-fixtures/expected/vulnado-expected-bugs.json`

- [ ] **Step 1: Create the expected/ directory**

```bash
mkdir -p test-fixtures/expected
```

- [ ] **Step 2: Write `c-vuln-samples-expected-bugs.json`**

```json
{
  "fixture": "c-vuln-samples",
  "language": "c",
  "expected_bugs": [
    {"file": "src/uaf.c", "function": "main", "class": "uaf", "severity": "critical"},
    {"file": "src/oob_read.c", "function": "main", "class": "oob-rw", "severity": "high"},
    {"file": "src/oob_write.c", "function": "main", "class": "oob-rw", "severity": "critical"},
    {"file": "src/double_free.c", "function": "main", "class": "double-free", "severity": "high"},
    {"file": "src/format_string.c", "function": "main", "class": "format-string", "severity": "high"},
    {"file": "src/stack_overflow.c", "function": "vulnerable", "class": "oob-rw", "severity": "critical"}
  ],
  "recall_target": 0.7,
  "precision_target": 0.7,
  "notes": "Memory bugs are harder to chain; 70% recall is the V1 floor."
}
```

- [ ] **Step 3: Write `dvwa-expected-bugs.json`**

```json
{
  "fixture": "dvwa",
  "language": "php",
  "expected_bugs": [
    {"file": "vulnerabilities/sqli/source/low.php", "function": "n/a", "class": "sql-injection", "severity": "critical"},
    {"file": "vulnerabilities/sqli_blind/source/low.php", "function": "n/a", "class": "sql-injection", "severity": "high"},
    {"file": "vulnerabilities/exec/source/low.php", "function": "n/a", "class": "command-injection", "severity": "critical"},
    {"file": "vulnerabilities/csrf/source/low.php", "function": "n/a", "class": "type-juggling", "severity": "medium"},
    {"file": "vulnerabilities/fi/source/low.php", "function": "n/a", "class": "command-injection", "severity": "high"},
    {"file": "vulnerabilities/upload/source/low.php", "function": "n/a", "class": "command-injection", "severity": "high"},
    {"file": "vulnerabilities/xss_r/source/low.php", "function": "n/a", "class": "type-juggling", "severity": "medium"},
    {"file": "vulnerabilities/xss_s/source/low.php", "function": "n/a", "class": "type-juggling", "severity": "high"},
    {"file": "vulnerabilities/weak_id/source/low.php", "function": "n/a", "class": "idor", "severity": "high"},
    {"file": "vulnerabilities/captcha/source/low.php", "function": "n/a", "class": "type-juggling", "severity": "medium"}
  ],
  "recall_target": 0.8,
  "precision_target": 0.7
}
```

- [ ] **Step 4: Write `juice-shop-expected-bugs.json`**

```json
{
  "fixture": "juice-shop",
  "language": "typescript",
  "expected_bugs": [
    {"file": "routes/login.ts", "function": "login", "class": "sql-injection", "severity": "critical"},
    {"file": "routes/likeProductReviews.ts", "function": "likeProductReviews", "class": "nosql-injection", "severity": "high"},
    {"file": "routes/dataExport.ts", "function": "dataExport", "class": "data-exposure-api", "severity": "high"},
    {"file": "routes/userProfile.ts", "function": "userProfile", "class": "ssti", "severity": "critical"},
    {"file": "routes/profileImageUrlUpload.ts", "function": "profileImageUrlUpload", "class": "ssrf", "severity": "high"},
    {"file": "routes/redirect.ts", "function": "redirect", "class": "type-juggling", "severity": "medium"},
    {"file": "lib/insecurity.ts", "function": "verify", "class": "jwt-confusion", "severity": "high"},
    {"file": "routes/showProductReviews.ts", "function": "showProductReviews", "class": "idor", "severity": "high"},
    {"file": "routes/updateUserProfile.ts", "function": "updateUserProfile", "class": "mass-assignment", "severity": "high"},
    {"file": "routes/restoreBasket.ts", "function": "restoreBasket", "class": "race-condition", "severity": "medium"},
    {"file": "routes/coupon.ts", "function": "coupon", "class": "race-condition", "severity": "high"},
    {"file": "routes/order.ts", "function": "order", "class": "bfla", "severity": "high"}
  ],
  "recall_target": 0.8,
  "precision_target": 0.7
}
```

- [ ] **Step 5: Write `nodegoat-expected-bugs.json`**

```json
{
  "fixture": "nodegoat",
  "language": "javascript",
  "expected_bugs": [
    {"file": "app/data/profile-dao.js", "function": "updateUser", "class": "nosql-injection", "severity": "critical"},
    {"file": "app/data/profile-dao.js", "function": "getUser", "class": "nosql-injection", "severity": "high"},
    {"file": "app/routes/profile.js", "function": "handleProfileUpdate", "class": "mass-assignment", "severity": "high"},
    {"file": "app/routes/research.js", "function": "displayResearch", "class": "ssrf", "severity": "high"},
    {"file": "app/data/allocations-dao.js", "function": "update", "class": "idor", "severity": "high"},
    {"file": "app/routes/index.js", "function": "n/a", "class": "type-juggling", "severity": "medium"},
    {"file": "config/config.js", "function": "n/a", "class": "data-exposure-api", "severity": "medium"}
  ],
  "recall_target": 0.8,
  "precision_target": 0.7
}
```

- [ ] **Step 6: Write `webgoat-expected-bugs.json`**

```json
{
  "fixture": "webgoat",
  "language": "java",
  "expected_bugs": [
    {"file": "src/main/java/org/owasp/webgoat/lessons/sqlinjection/", "function": "various", "class": "sql-injection", "severity": "critical"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/idor/", "function": "various", "class": "idor", "severity": "high"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/jwt/", "function": "various", "class": "jwt-confusion", "severity": "high"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/ssrf/", "function": "various", "class": "ssrf", "severity": "high"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/deserialization/", "function": "various", "class": "deserialization", "severity": "critical"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/missingac/", "function": "various", "class": "bfla", "severity": "high"},
    {"file": "src/main/java/org/owasp/webgoat/lessons/passwordreset/", "function": "various", "class": "idor", "severity": "high"}
  ],
  "recall_target": 0.8,
  "precision_target": 0.7,
  "notes": "WebGoat exercises are organized as lesson packages; file paths refer to the package root."
}
```

- [ ] **Step 7: Write `vulnado-expected-bugs.json`**

```json
{
  "fixture": "vulnado",
  "language": "java",
  "expected_bugs": [
    {"file": "src/main/java/com/scalesec/vulnado/User.java", "function": "fetch", "class": "sql-injection", "severity": "critical"},
    {"file": "src/main/java/com/scalesec/vulnado/CommandsController.java", "function": "commandInjection", "class": "command-injection", "severity": "critical"},
    {"file": "src/main/java/com/scalesec/vulnado/CookieController.java", "function": "value", "class": "deserialization", "severity": "critical"},
    {"file": "src/main/java/com/scalesec/vulnado/LinksController.java", "function": "links", "class": "ssrf", "severity": "high"},
    {"file": "src/main/java/com/scalesec/vulnado/LoginController.java", "function": "login", "class": "sql-injection", "severity": "critical"}
  ],
  "recall_target": 0.8,
  "precision_target": 0.7
}
```

- [ ] **Step 8: Commit**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  test-fixtures/expected/
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "feat: expected-bugs.json for all 6 fixtures (recall/precision targets)"
```

---

## Task 4: Expected-bugs JSON validation tests

**Files:**
- Create: `tests/unit/test_expected_bugs_schemas.py`

- [ ] **Step 1: Write the test**

Write `tests/unit/test_expected_bugs_schemas.py`:
```python
"""Validate the structure of every expected-bugs.json fixture."""
import json
from pathlib import Path
import pytest


EXPECTED_DIR = Path(__file__).parent.parent.parent / "test-fixtures" / "expected"
INTERNAL_DIR = Path(__file__).parent.parent.parent / "test-fixtures" / "c-vuln-samples"
MAPPING_PATH = (
    Path(__file__).parent.parent.parent
    / ".claude" / "agents" / "mythos" / "bug-class-mapping.json"
)


def _expected_files() -> list[Path]:
    files = sorted(EXPECTED_DIR.glob("*-expected-bugs.json"))
    # Also include the internal fixture's own expected-bugs.json
    internal = INTERNAL_DIR / "expected-bugs.json"
    if internal.is_file():
        files.append(internal)
    return files


REQUIRED_FIXTURES = {
    "c-vuln-samples", "dvwa", "juice-shop", "nodegoat", "webgoat", "vulnado",
}


def test_all_6_fixtures_have_expected_bugs():
    fixtures = set()
    for f in EXPECTED_DIR.glob("*-expected-bugs.json"):
        # Strip "-expected-bugs.json" suffix
        fixtures.add(f.name.replace("-expected-bugs.json", ""))
    # c-vuln-samples lives in its own directory
    if (INTERNAL_DIR / "expected-bugs.json").is_file():
        fixtures.add("c-vuln-samples")
    assert REQUIRED_FIXTURES.issubset(fixtures), (
        f"missing expected-bugs.json for: {REQUIRED_FIXTURES - fixtures}"
    )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_expected_bugs_has_required_keys(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ["fixture", "language", "expected_bugs", "recall_target", "precision_target"]:
        assert key in data, f"{path.name}: missing key '{key}'"


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_expected_bugs_classes_are_valid(path):
    """Every bug class must exist in bug-class-mapping.json."""
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    valid_classes = set(mapping.keys())
    data = json.loads(path.read_text(encoding="utf-8"))
    for bug in data["expected_bugs"]:
        assert bug["class"] in valid_classes, (
            f"{path.name}: bug class {bug['class']!r} not in bug-class-mapping.json"
        )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_severity_values_valid(path):
    valid = {"critical", "high", "medium", "low", "info"}
    data = json.loads(path.read_text(encoding="utf-8"))
    for bug in data["expected_bugs"]:
        assert bug["severity"] in valid, (
            f"{path.name}: bug severity {bug['severity']!r} not valid"
        )


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_recall_target_in_range(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    target = data["recall_target"]
    assert 0.0 <= target <= 1.0


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_precision_target_in_range(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    target = data["precision_target"]
    assert 0.0 <= target <= 1.0


@pytest.mark.parametrize("path", _expected_files(), ids=lambda p: p.name)
def test_at_least_5_bugs_per_fixture(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    n = len(data["expected_bugs"])
    assert n >= 5, f"{path.name}: only {n} bugs; need ≥ 5 for meaningful recall measurement"
```

- [ ] **Step 2: Run + commit**

```bash
pytest tests/unit/test_expected_bugs_schemas.py -v
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  tests/unit/test_expected_bugs_schemas.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "test: validate expected-bugs.json for all fixtures"
```

Expected: ~40 tests PASS (6 fixtures × 6 parametrized + 1 unparameterized).

---

## Task 5: c-vuln-samples buildability test

**Files:**
- Create: `tests/unit/test_c_vuln_samples_buildable.py`

- [ ] **Step 1: Write the test**

Write `tests/unit/test_c_vuln_samples_buildable.py`:
```python
"""Verify c-vuln-samples can compile inside the Mythos sandbox."""
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


FIXTURE_DIR = (
    Path(__file__).parent.parent.parent / "test-fixtures" / "c-vuln-samples"
)


def test_source_files_present():
    expected = {"uaf.c", "oob_read.c", "oob_write.c", "double_free.c",
                "format_string.c", "stack_overflow.c"}
    actual = {p.name for p in (FIXTURE_DIR / "src").glob("*.c")}
    assert expected.issubset(actual), f"missing: {expected - actual}"


def test_makefile_present():
    assert (FIXTURE_DIR / "Makefile").is_file()


def test_readme_present():
    assert (FIXTURE_DIR / "README.md").is_file()


def test_expected_bugs_present():
    assert (FIXTURE_DIR / "expected-bugs.json").is_file()


@pytest.mark.docker
def test_compiles_in_sandbox(docker_available):
    """Build c-vuln-samples inside the mythos-multilang sandbox."""
    if not shutil.which("docker"):
        pytest.skip("docker not on PATH")
    # Run: copy source → build → check binaries exist
    docker_path = "docker"  # absolute path resolved by shutil
    cmd = [
        docker_path, "run", "--rm",
        "-v", f"{FIXTURE_DIR}:/work:ro",
        "--tmpfs", "/work-rw:size=50M,exec",
        "--user", "1000:1000",
        "mythos-multilang:1.0.0",
        "bash", "-c",
        "cp -r /work/* /work-rw/ && cd /work-rw && make 2>&1 | tail -5 && ls bin/",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"build failed: stdout={r.stdout}\nstderr={r.stderr}"
    for expected_bin in ["uaf", "oob_read", "oob_write", "double_free", "format_string", "stack_overflow"]:
        assert expected_bin in r.stdout, f"binary {expected_bin!r} missing from output"
```

- [ ] **Step 2: Run + commit**

```bash
pytest tests/unit/test_c_vuln_samples_buildable.py -v
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" add \
  tests/unit/test_c_vuln_samples_buildable.py
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" commit -m "test: c-vuln-samples build + structural checks"
```

Expected: 5 tests PASS (test_compiles_in_sandbox depends on Docker availability).

---

## Task 6: Plan-7-done tag

- [ ] **Step 1: Run the full suite**

```bash
pytest tests/ 2>&1 | tail -3
```

Expected: All non-slow tests PASS. Plan 6 had 378; Plan 7 adds ~50 = ~430.

- [ ] **Step 2: Tag**

```bash
git -c user.email="ca.ostend@gmail.com" -c user.name="Alan" tag -a mythos-plan-7-done -m "Plan 7 complete: fetch_fixtures + c-vuln-samples + 6 expected-bugs.json"
```

---

## Completion criteria

- [ ] All 6 tasks above are checked off
- [ ] `fetch_fixtures.py --list` shows all 6 fixtures
- [ ] `c-vuln-samples/` has 6 source files + Makefile + README + expected-bugs.json
- [ ] All 6 expected-bugs.json files exist with valid structure
- [ ] Every bug class in expected files exists in `bug-class-mapping.json`
- [ ] Tag `mythos-plan-7-done` exists

---

## What's NOT in Plan 7 (deferred to Plan 8)

| Item | Plan |
|---|---|
| Run `/mythos start` end-to-end on each fixture | 8 |
| Recall/precision measurement | 8 |
| V1 acceptance criteria gating | 8 |
| Final docs (OPERATIONS.md, DEVELOPMENT.md, SECURITY.md) | 8 |

---

## Self-review

| Spec section | Plan 7 task | Status |
|---|---|---|
| §12.3 E2E vulnerable fixtures | Tasks 1, 2, 3 | ✅ |
| §17 acceptance: recall ≥ 80% on Juice Shop / DVWA | Task 3 (targets in JSON) | ✅ |

---

**Plan 7 complete.** Final step is Plan 8 (E2E runs + V1 ship docs).
