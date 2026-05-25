#!/bin/bash
# Escape attempt #3: fork bomb to exhaust PIDs.
# Expected outcome: pids_limit=100 kicks in, the bomb is contained.
# The container should be killed by Docker (OOM-ish) before the host suffers.
( :(){ :|:& };: ) &
sleep 5
echo "fork_bomb_survived"
