---
class_id: idor
name: Insecure Direct Object Reference
applicable_languages: [any]
applicable_frameworks: [any]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-idor-vulnerabilities
---

## Indicators

- Endpoints take a resource ID directly from URL/body without ownership check
- `/api/users/:id` without verifying req.user owns id
- Database query by ID without joining authorization tables
- Sequentially-incremented IDs (no UUIDs)

## Hunting hints

- Grep for handlers that use `req.params.id` or `request.path_params["id"]`
- Look for `findById` / `objects.get(pk=...)` without subsequent ACL check
- Check that authorization middleware is registered on the route

## PoC strategy

1. Authenticate as user A, identify a resource ID owned by user B
2. Replay request as A with B's ID
3. Confirm data leak / unauthorized state change
