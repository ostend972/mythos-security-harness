#!/bin/bash
# Entrypoint for the mythos-multilang container.
# Expects:
#   /work     : read-only PoC directory (input)
#   /work-rw  : writable tmpfs (output, scratch — for compiler temp files)
#
# Reads /work/run.sh if present, else /work/run.* (first match).
# Streams stdout/stderr directly so the caller (docker-py) can read them.

set -u  # NO -e: we want to capture failures, not abort

if [[ ! -d /work ]]; then
  echo "error: no /work mount" >&2
  exit 2
fi

if [[ -f /work/run.sh ]]; then
  CMD=(bash /work/run.sh)
elif [[ -f /work/run.py ]]; then
  CMD=(python3 /work/run.py)
elif [[ -f /work/run.js ]]; then
  CMD=(node /work/run.js)
else
  echo "error: no run.{sh,py,js} found in /work" >&2
  exit 3
fi

# Internal 25s timeout (container is externally killed at 30s by caller).
# stdout and stderr stream directly to docker (no file redirect).
timeout --kill-after=2 25 "${CMD[@]}"
exit $?
