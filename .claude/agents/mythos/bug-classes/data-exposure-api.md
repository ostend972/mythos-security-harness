---
class_id: data-exposure-api
name: Excessive Data Exposure in API
applicable_languages: [any]
applicable_frameworks: [any]
severity_default: medium
fp_rate_expected: 0.30
skill: exploiting-excessive-data-exposure-in-api
---

## Indicators

- Endpoint returns full DB row instead of curated DTO
- Serializer returns all fields (`fields = "__all__"`)
- API responses include internal flags (e.g., `is_admin`, `password_hash`)
- Client filters sensitive fields instead of server

## Hunting hints

- Grep for serializers with `fields = "__all__"`
- Check response shapes against API documentation
- Look for raw model→JSON serialization paths

## PoC strategy

1. Make a normal authenticated request to a list/detail endpoint
2. Inspect the JSON response for fields not exposed in the UI
3. Document the leak (e.g., password hash, internal IDs, PII)
