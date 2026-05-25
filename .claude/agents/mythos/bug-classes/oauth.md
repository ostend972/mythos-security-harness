---
class_id: oauth
name: OAuth Misconfiguration
applicable_languages: [python, javascript, typescript, java, ruby, go]
applicable_frameworks: [authlib, passport, spring-security, omniauth, oauth2-proxy]
severity_default: high
fp_rate_expected: 0.25
skill: exploiting-oauth-misconfiguration
---

## Indicators

- Permissive `redirect_uri` validation (substring match, wildcards)
- Missing or weak `state` parameter validation (CSRF in OAuth)
- Implicit flow when authorization code + PKCE is appropriate
- `client_secret` shipped to public clients

## Hunting hints

- Grep for `redirect_uri` validators using `startswith` / regex substrings
- Check OAuth library configs for state nonce requirements
- Look for token endpoints accepting both `code` and `id_token` responses

## PoC strategy

1. Try `redirect_uri=https://attacker.com.victim.com` if regex is loose
2. Try parameter pollution: `redirect_uri=victim.com&redirect_uri=attacker.com`
3. Confirm token / auth code leaks to attacker domain
