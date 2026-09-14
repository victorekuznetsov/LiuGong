#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."

# EPC tolerates NO concurrent requests on one JSESSIONID: any overlap answers
# 401, which is what killed every previous run. Measured 2026-09-14: 80
# strictly sequential requests all returned 200 on the very session a 2-thread
# run had just declared dead. 2 threads still overlap because
# /supersession/detail is issued outside photo_lock, so the only safe value
# is 1. Costs little anyway -- photo_lock already serialised most of the work.
THREADS="${THREADS:-1}"

VINS=(
  CLG8128HERL801592
  CLG862HZLRL813829
  LGJ6614EHNR058121
)

for vin in "${VINS[@]}"; do
  echo "=========================================="
  echo "=== $vin  $(date)"
  echo "=========================================="
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only details --threads "$THREADS"
  if [ $? -ne 0 ]; then
    echo "!!! $vin / details FAILED -- stopping batch"
    exit 1
  fi
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only photos --threads "$THREADS"
  if [ $? -ne 0 ]; then
    echo "!!! $vin / photos FAILED -- stopping batch"
    exit 1
  fi
done
echo "=== REMAINING 3 DONE $(date) ==="
