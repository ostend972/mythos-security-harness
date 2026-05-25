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
