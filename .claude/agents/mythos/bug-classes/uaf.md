---
class_id: uaf
name: Use-After-Free
applicable_languages: [c, cpp, rust-unsafe, zig]
applicable_frameworks: []
severity_default: critical
fp_rate_expected: 0.35
skill: analyzing-heap-spray-exploitation
---

## Indicators

- Dangling pointer access after `free`
- Object access after destruction in C++
- Reference counting mismatches
- Asynchronous callbacks holding stale pointers

## Hunting hints

- Look for `free(p)` followed later by `p->...` or `*p`
- Check destructors that don't null out aliased pointers
- Refcount decrement without check before next use

## PoC strategy

1. Reach the path that frees the resource
2. Trigger a second event that uses the freed pointer
3. Run under ASan to confirm UAF
4. Optionally exploit via heap-spray to control freed memory
