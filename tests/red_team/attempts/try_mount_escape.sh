#!/bin/bash
# Escape attempt #6: try to mount a directory.
# Expected outcome: seccomp blocks mount() syscall.
mkdir -p /tmp/escape-target 2>/dev/null
mount -t proc proc /tmp/escape-target 2>&1
RC=$?
if [[ $RC -eq 0 ]]; then
  echo "SANDBOX_BREACH: mount succeeded"
  exit 0
fi
echo "mount_denied: rc=$RC"
exit 1
