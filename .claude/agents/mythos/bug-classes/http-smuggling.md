---
class_id: http-smuggling
name: HTTP Request Smuggling
applicable_languages: [any]
applicable_frameworks: [nginx, apache, haproxy, traefik, varnish, edge-cdn]
severity_default: critical
fp_rate_expected: 0.30
skill: exploiting-http-request-smuggling
---

## Indicators

- Proxy + backend with disagreement on Content-Length vs Transfer-Encoding
- Custom HTTP parsers (CVE-prone)
- Backend that allows both CL and TE headers
- Reverse proxy not normalizing headers before forward

## Hunting hints

- Identify proxy + backend versions; check known smuggling CVEs
- Look for `req.headers.raw` access patterns
- Check for keep-alive misconfigurations

## PoC strategy

1. Send CL.TE or TE.CL crafted request
2. Confirm second pipelined request is misrouted/cached/poisoned
3. Use this to bypass auth or poison cache
