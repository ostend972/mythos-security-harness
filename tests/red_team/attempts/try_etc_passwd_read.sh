#!/bin/bash
# Escape attempt #1: try to read /etc/passwd of the host
# Expected outcome: the file inside the container is readable (it's the container's /etc/passwd),
# but it must contain ONLY the container's users, NOT the host's. Verification is by checking
# that "nobody-mythos" is present and the host's primary user is NOT.
cat /etc/passwd
