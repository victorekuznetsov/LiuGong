#!/bin/bash
# Runs the full crawl pipeline for each remaining Polyus fleet VIN, one at a time.
set -uo pipefail
cd "$(dirname "$0")/.."

VINS=(
  CLG942EHKSE917908
  CLG890HZTSL831819
  CLG8128HERL801592
  CLG862HZLRL813829
  LGJ6614EHNR058121
  LGC922FWHSC139999
  CLG975FZASE912911
)

for vin in "${VINS[@]}"; do
  echo "=========================================="
  echo "=== $vin  $(date)"
  echo "=========================================="
  for step in tree parts drawings details photos; do
    echo "--- $vin / $step ---"
    PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only "$step" --threads 6
    if [ $? -ne 0 ]; then
      echo "!!! $vin / $step FAILED, retrying once"
      sleep 5
      PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only "$step" --threads 6
    fi
  done
done
echo "=== FLEET CRAWL DONE $(date) ==="
