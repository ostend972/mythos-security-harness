#!/bin/bash
# Escape attempt #4: try to exfiltrate data to an external host.
# Expected outcome: network_mode=none blocks all outbound. curl must fail.
if command -v curl >/dev/null 2>&1; then
  curl -sS --max-time 3 https://example.com -o /tmp/exfil.html 2>&1
  RC=$?
  if [[ $RC -eq 0 ]]; then
    echo "SANDBOX_BREACH: curl to example.com succeeded"
    exit 0
  fi
  echo "network_denied: curl exit=$RC"
fi
# Try direct socket
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(('1.1.1.1', 53))
    print('SANDBOX_BREACH: socket to 1.1.1.1:53 succeeded')
except Exception as e:
    print(f'network_denied: {type(e).__name__}: {e}')
" 2>&1
exit 1
