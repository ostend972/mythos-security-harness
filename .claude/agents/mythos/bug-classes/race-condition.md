---
class_id: race-condition
name: Race Condition / TOCTOU
applicable_languages: [any]
applicable_frameworks: [any]
severity_default: high
fp_rate_expected: 0.35
skill: exploiting-race-condition-vulnerabilities
---

## Indicators

- "Check then act" sequences without locking (balance check + withdraw)
- Coupon / discount redemption without uniqueness constraint
- File create-then-chmod patterns
- Quantity validation followed by stock decrement (no transaction)

## Hunting hints

- Grep for separated check + action lines
- Look for SQL UPDATE without WHERE conditions that include the prior state
- Check for missing `SELECT ... FOR UPDATE` or atomic CAS operations

## PoC strategy

1. Identify the vulnerable check-then-act sequence
2. Send the action request N times in parallel (asyncio.gather, threading)
3. Confirm the action fired more than once (double-spend, duplicate coupon)
