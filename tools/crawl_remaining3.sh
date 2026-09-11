#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."

VINS=(
  CLG8128HERL801592
  CLG862HZLRL813829
  LGJ6614EHNR058121
)

for vin in "${VINS[@]}"; do
  echo "=========================================="
  echo "=== $vin  $(date)"
  echo "=========================================="
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only details --threads 6
  if [ $? -ne 0 ]; then
    echo "!!! $vin / details FAILED -- stopping batch"
    exit 1
  fi
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only photos --threads 6
  if [ $? -ne 0 ]; then
    echo "!!! $vin / photos FAILED -- stopping batch"
    exit 1
  fi
done
echo "=== REMAINING 3 DONE $(date) ==="
