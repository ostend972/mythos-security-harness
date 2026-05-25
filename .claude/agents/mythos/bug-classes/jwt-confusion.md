---
class_id: jwt-confusion
name: JWT Algorithm Confusion
applicable_languages: [python, javascript, typescript, java, go, ruby]
applicable_frameworks: [pyjwt, jsonwebtoken, jose, jjwt, golang-jwt]
severity_default: high
fp_rate_expected: 0.20
skill: exploiting-jwt-algorithm-confusion-attack
---

## Indicators

- `jwt.decode(token, key, ...)` without explicit `algorithms=` allowlist
- Token verification accepts `alg: none`
- `HS256` verification using a PUBLIC key (treating it as secret)
- Custom JWT verification using the header's `alg` field directly

## Hunting hints

- Grep for `jwt.decode(.+verify=False`, `algorithms=` (its absence)
- Check for trust in `decoded_header["alg"]`
- Look for shared verification keys between RS/HS contexts

## PoC strategy

1. Modify the JWT header `alg` to `none` and remove the signature
2. Or sign with public RS key using HS256 algorithm
3. Confirm token accepted by the server
