#!/bin/bash
# Escape attempt #5: try to access Docker socket (if mistakenly mounted).
# Expected outcome: /var/run/docker.sock is not mounted, so it doesn't exist.
if [[ -S /var/run/docker.sock ]]; then
  echo "SANDBOX_BREACH: docker.sock is accessible"
  ls -la /var/run/docker.sock
  exit 0
fi
echo "docker_sock_absent: as expected"
exit 1
