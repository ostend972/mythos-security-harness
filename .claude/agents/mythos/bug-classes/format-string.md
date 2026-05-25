---
class_id: format-string
name: Format String Vulnerability
applicable_languages: [c, cpp]
applicable_frameworks: []
severity_default: high
fp_rate_expected: 0.20
skill: analyzing-heap-spray-exploitation
---

## Indicators

- `printf(user_string)` instead of `printf("%s", user_string)`
- Custom logging that passes user data as format string
- `syslog(LOG_INFO, user_data)` patterns

## PoC strategy

1. Inject `%x %x %x` to leak stack
2. Use `%n` to write arbitrary values (if writable)
3. Confirm info leak or arbitrary write
