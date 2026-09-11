#!/bin/bash
# Runs details+photos for each already tree/parts/drawings-crawled fleet VIN.
# Stops the whole batch on first unrecoverable failure (e.g. session expiry)
# instead of grinding through the rest with a dead session -- re-run after
# fixing the session, already-done files are skipped automatically.
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
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only details --threads 6
  if [ $? -ne 0 ]; then
    echo "!!! $vin / details FAILED -- stopping batch (fix session, then re-run this script)"
    exit 1
  fi
  PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only photos --threads 6
  if [ $? -ne 0 ]; then
    echo "!!! $vin / photos FAILED -- stopping batch (fix session, then re-run this script)"
    exit 1
  fi
done
echo "=== FLEET DETAILS+PHOTOS DONE $(date) ==="
