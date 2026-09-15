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

# Order matters: emptiest machine first. 862H and 6614E had ZERO part cards
# after five runs purely because 8128H used to sit at the top of this list and
# the batch aborted on its first failure -- they were never even started.
# 8128H's cards are complete now, so it goes last (only its photo pass is left).
VINS=(
  CLG862HZLRL813829   # 862H  loader    -- 0 cards
  LGJ6614EHNR058121   # 6614E roller    -- 0 cards
  CLG8128HERL801592   # 8128H loader    -- cards done, photos partial
)

failed=()
for vin in "${VINS[@]}"; do
  for step in details photos; do
    echo "=========================================="
    echo "=== $vin / $step  $(date)"
    echo "=========================================="
    PYTHONIOENCODING=utf-8 python3 tools/crawl_machine.py "$vin" --only "$step" --threads "$THREADS"
    if [ $? -ne 0 ]; then
      # Never abort the batch: one machine's dead session must not starve the
      # ones behind it (that is exactly how 862H/6614E stayed at zero). Each
      # step is resumable, so re-running after a re-login picks up the rest.
      echo "!!! $vin / $step FAILED -- skipping to next, batch continues"
      failed+=("$vin/$step")
      break
    fi
  done
done

if [ ${#failed[@]} -gt 0 ]; then
  echo "=== DONE WITH FAILURES $(date): ${failed[*]}"
  echo "=== re-run after refreshing the session (_recon/refresh_epc2.py)"
  exit 1
fi
echo "=== REMAINING 3 DONE $(date) ==="
