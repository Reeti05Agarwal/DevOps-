#!/usr/bin/env bash
# Sends a mix of good, slow and failing requests so every Grafana panel has data.
# Usage: ./scripts/generate-traffic.sh [base_url] [seconds]
set -uo pipefail
URL="${1:-http://localhost:5000}"
DURATION="${2:-120}"
END=$((SECONDS + DURATION))
echo "Sending traffic to $URL for ${DURATION}s (Ctrl+C to stop)"
i=0
while (( SECONDS < END )); do
  curl -s -o /dev/null "$URL/health"
  curl -s -o /dev/null "$URL/notes"
  curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -d "{\"text\":\"note $i\"}" "$URL/notes"
  (( i % 5 == 0 ))  && curl -s -o /dev/null "$URL/boom"
  (( i % 10 == 0 )) && curl -s -o /dev/null "$URL/slow"
  i=$((i + 1))
  sleep 0.2
done
echo "Sent $i rounds."
