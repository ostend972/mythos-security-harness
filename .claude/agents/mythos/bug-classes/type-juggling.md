---
class_id: type-juggling
name: PHP/JS Type Juggling
applicable_languages: [php, javascript, typescript]
applicable_frameworks: []
severity_default: medium
fp_rate_expected: 0.30
skill: exploiting-type-juggling-vulnerabilities
---

## Indicators

- Loose equality (`==`) for security-sensitive comparisons
- PHP `strcmp`/`md5`/`==` patterns with user input
- JS `==` instead of `===` near auth checks
- Use of `0e...` strings compared loosely

## Hunting hints

- Grep PHP files for `== "?\$_REQUEST` and `md5\(.+==\s*`
- JS: `==` near auth, token, password literals
- Look for `0e...` constants as magic comparison targets

## PoC strategy

1. Identify the vulnerable comparison
2. Craft a payload matching via type coercion (e.g., `0e123` matches `0`)
3. Confirm auth bypass or unintended branch
