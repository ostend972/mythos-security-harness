---
class_id: ssrf
name: Server-Side Request Forgery
applicable_languages: [python, javascript, typescript, java, ruby, go, php]
applicable_frameworks: [requests, axios, httpx, fetch, urllib, okhttp, httparty]
severity_default: critical
fp_rate_expected: 0.20
skill: exploiting-server-side-request-forgery
---

## Indicators

- HTTP client called with URL from user input, no allowlist
- `requests.get(user_url)` patterns
- URL fetched server-side for webhooks, image previews, OAuth callbacks
- No validation against `localhost`, `127.0.0.1`, `169.254.169.254` (cloud metadata)

## Hunting hints

- Grep for HTTP client calls using user-controlled variables
- Check for allowlist enforcement in URL fetchers
- Look for redirect-following enabled by default

## PoC strategy

1. Submit `http://localhost:80/admin` or `http://169.254.169.254/latest/meta-data/`
2. Capture server's response to confirm internal access
3. Use OOB callback (Burp Collaborator equivalent) if blind
