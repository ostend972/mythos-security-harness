---
class_id: bfla
name: Broken Function-Level Authorization
applicable_languages: [any]
applicable_frameworks: [any]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-broken-function-level-authorization
---

## Indicators

- Admin endpoints rely on UI-side visibility instead of server-side role check
- Missing role check on `/admin/*` routes
- Verbs other than GET trusted without re-authorization

## Hunting hints

- Grep for routes containing `/admin/`, `/internal/`
- Check middleware registration: does every admin route apply the role gate?
- Look for `@requires_role` decorators missing on some endpoints

## PoC strategy

1. As a regular user, send a request to a known admin endpoint
2. Confirm execution succeeds (or returns admin-only data)
