---
class_id: heap-corruption
name: Heap Corruption (generic)
applicable_languages: [c, cpp, rust-unsafe, zig]
applicable_frameworks: []
severity_default: critical
fp_rate_expected: 0.40
skill: analyzing-heap-spray-exploitation
---

## Indicators

- malloc/free imbalance
- Untrusted size in allocation
- Mixing malloc/new and free/delete
- Custom allocators

## PoC strategy

1. Trigger via crafted input
2. Run with ASan to detect heap-overflow / heap-underflow
3. Capture crash with stack trace
