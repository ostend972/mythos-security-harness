#!/bin/bash
# Entrypoint for the mythos-multilang container.
# Expects:
#   /work     : read-only PoC directory (input)
#   /work-rw  : writable tmpfs (output, scratch)
#
# Reads /work/run.sh if present, else /work/run.* (first match).
# Writes /work-rw/result.json with {exit_code, duration_s}.

set -u  # NO -e: we want to capture failures, not abort

START_TS=$(date +%s%N)

if [[ ! -d /work ]]; then
  echo '{"error":"no /work mount"}' > /work-rw/result.json
  exit 2
fi

if [[ -f /work/run.sh ]]; then
  CMD="bash /work/run.sh"
elif [[ -f /work/run.py ]]; then
  CMD="python3 /work/run.py"
elif [[ -f /work/run.js ]]; then
  CMD="node /work/run.js"
else
  echo '{"error":"no run.{sh,py,js} found in /work"}' > /work-rw/result.json
  exit 3
fi

# Capture output, timeout after 25s (container also gets killed externally at 30s)
timeout --kill-after=2 25 $CMD > /work-rw/stdout.log 2> /work-rw/stderr.log
EXIT_CODE=$?

END_TS=$(date +%s%N)
DURATION_MS=$(( (END_TS - START_TS) / 1000000 ))

cat > /work-rw/result.json <<EOF
{
  "exit_code": ${EXIT_CODE},
  "duration_ms": ${DURATION_MS},
  "command": "${CMD}"
}
EOF

exit ${EXIT_CODE}
