---
class_id: mass-assignment
name: Mass Assignment / Over-Posting
applicable_languages: [python, javascript, typescript, ruby, java]
applicable_frameworks: [django, drf, fastapi, rails, spring]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-mass-assignment-in-rest-apis
---

## Indicators

- `User(**request.json)` (Python) or `User.objects.create(**data)`
- Rails `params[:user]` passed without `.permit(...)` allowlist
- DRF serializer with `fields = "__all__"`

## Hunting hints

- Grep for `**request.json`, `**request.data`, `**req.body`
- Rails: scan for `params.require` without `permit`
- DRF: scan for serializers with `fields = "__all__"`

## PoC strategy

1. Identify a model with sensitive flags (e.g., `is_admin`, `email_verified`)
2. Submit those fields in a request body the API does not expect
3. Confirm the privilege is escalated
