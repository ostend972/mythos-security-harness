---
class_id: prototype-pollution
name: Prototype Pollution
applicable_languages: [javascript, typescript]
applicable_frameworks: [express, lodash, jquery, hoek, merge-deep]
severity_default: high
fp_rate_expected: 0.25
skill: exploiting-prototype-pollution-in-javascript
---

## Indicators

- Recursive merge / deep-clone functions that don't filter `__proto__`, `constructor`, `prototype`
- Direct assignment patterns: `obj[user_key] = user_value`
- Lodash `_.merge`, `_.set`, `_.defaultsDeep` with user input
- Custom JSON.parse + assign loops

## Hunting hints

- Grep for `__proto__`, `prototype\[`, `merge\(`, `defaultsDeep\(`
- Look for absent key-allowlist checks before deep merges
- Check for `Object.assign(target, JSON.parse(req.body))`

## PoC strategy

1. Send `{"__proto__":{"polluted":1}}` via JSON body
2. Verify `({}).polluted === 1` after the request
3. Escalate to RCE if a gadget exists (e.g., process.mainModule.require)
