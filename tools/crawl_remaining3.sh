#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."

# 6 threads made EPC hand out spurious 401s (measured 2026-09-14: the exact
# part URLs that failed mid-run answered 200 when fetched one at a time, and
# 28/30 sequential fetches succeeded). Detail fetches are serialised by
# photo_lock anyway, so a low thread count costs little throughput.
THREADS="${THREADS:-2}"

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
