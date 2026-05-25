# c-vuln-samples — In-repo C bug fixture

Hand-crafted minimal C programs, each demonstrating exactly ONE memory bug class. Built with `-fsanitize=address,undefined` so each crash is unambiguous when executed inside the Mythos sandbox.

| Source | Bug class | ASan/UBSan output |
|---|---|---|
| `src/uaf.c` | `uaf` | heap-use-after-free |
| `src/oob_read.c` | `oob-rw` (read) | heap-buffer-overflow READ |
| `src/oob_write.c` | `oob-rw` (write) | heap-buffer-overflow WRITE |
| `src/double_free.c` | `double-free` | attempting double-free |
| `src/format_string.c` | `format-string` | runtime warning (no ASan crash) |
| `src/stack_overflow.c` | `oob-rw` (stack) | stack-buffer-overflow |

## Build (inside the sandbox container)

```bash
make
```

## Why hand-craft these instead of using public fixtures?

External vulnerable C apps (e.g., the Linux kernel test corpus) are huge and noisy. These 6 files are pedagogical: each isolates ONE bug, so Mythos's hunters can find them with a clean signal and Plan 8's E2E tests can score recall precisely.

**Do NOT compile or run these outside the Mythos Docker sandbox.** They are designed to crash.
