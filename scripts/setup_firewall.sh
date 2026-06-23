#!/usr/bin/env bash
# Open a TCP port for the Windows draft machine over the direct Ethernet link.
# Usage: bash scripts/setup_firewall.sh [windows_ip] [port]
# Example: bash scripts/setup_firewall.sh 192.168.50.2 8010
set -euo pipefail

WINDOWS_IP="${1:-192.168.50.2}"
PORT="${2:-8010}"

echo "Allowing TCP ${PORT} from ${WINDOWS_IP} ..."
sudo firewall-cmd \
  --add-rich-rule="rule family=\"ipv4\" source address=\"${WINDOWS_IP}\" port port=\"${PORT}\" protocol=\"tcp\" accept" \
  --permanent
sudo firewall-cmd --reload
echo "Firewall rule added."
