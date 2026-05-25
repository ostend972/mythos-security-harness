---
class_id: websocket
name: WebSocket Vulnerabilities
applicable_languages: [javascript, typescript, python, java, go]
applicable_frameworks: [socket.io, ws, websockets, gorilla, spring-websocket]
severity_default: high
fp_rate_expected: 0.25
skill: exploiting-websocket-vulnerabilities
---

## Indicators

- No origin validation on WS handshake
- Authentication done via cookie/header but not re-checked per message
- Lack of CSWSH (Cross-Site WebSocket Hijacking) protection
- Trust in `Origin` header without server-side allowlist

## Hunting hints

- Grep for `socket.io/server` or `WebSocketServer` instantiations
- Check for `verifyClient` / `onConnection` origin check
- Look for cookie-based auth without CSRF token

## PoC strategy

1. From attacker-controlled origin, attempt WS connection with victim's cookie
2. Confirm authenticated WS session is hijacked
3. Send authenticated messages on victim's behalf
