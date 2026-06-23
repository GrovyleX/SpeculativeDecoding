#!/usr/bin/env bash
# Open port 8000 for the Windows draft machine over the direct Ethernet link.
set -euo pipefail

WINDOWS_IP="${1:-192.168.50.2}"
PORT="${2:-8000}"

echo "Allowing TCP ${PORT} from ${WINDOWS_IP} ..."
sudo firewall-cmd \
  --add-rich-rule="rule family=\"ipv4\" source address=\"${WINDOWS_IP}\" port port=\"${PORT}\" protocol=\"tcp\" accept" \
  --permanent
sudo firewall-cmd --reload
echo "Firewall rule added."
