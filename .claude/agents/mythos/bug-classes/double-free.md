---
class_id: double-free
name: Double Free
applicable_languages: [c, cpp, zig]
applicable_frameworks: []
severity_default: high
fp_rate_expected: 0.25
skill: analyzing-heap-spray-exploitation
---

## Indicators

- `free(p)` called twice on the same pointer
- Cleanup paths in multiple branches both freeing
- Error handlers that don't reset pointer to NULL after free

## PoC strategy

1. Trigger the path that frees the resource
2. Trigger the second cleanup path
3. ASan detects double-free with stack traces
