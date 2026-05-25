---
class_id: oob-rw
name: Out-of-Bounds Read/Write
applicable_languages: [c, cpp, rust-unsafe, zig]
applicable_frameworks: []
severity_default: critical
fp_rate_expected: 0.30
skill: analyzing-heap-spray-exploitation
---

## Indicators

- Array indexing without bounds check
- Integer overflow in size calculation
- memcpy/memmove with untrusted lengths
- Off-by-one in loop conditions

## PoC strategy

1. Craft input with size = INT_MAX or carefully-chosen value
2. Observe ASan stack/heap-buffer-overflow report
3. Refine into a read primitive (leak) or write primitive (control)
