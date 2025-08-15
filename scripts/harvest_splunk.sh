#!/usr/bin/env bash
set -euo pipefail

# Dev-only bulk A/B fetch from Splunk by hour windows
# Requires: BOLCD_SPLUNK_URL, BOLCD_SPLUNK_TOKEN

OUT_DIR=${1:-data/raw}
INDEX=${2:-_internal}
HOURS=${3:-24}
B_EXCLUDE=${4:-"sourcetype=splunkd*"}
DAY=$(date +%F)

mkdir -p "$OUT_DIR"

echo "[A] collecting ${HOURS}h from index=${INDEX}"
for ((i=HOURS;i>=1;i--)); do
  FROM="${i}h"; TO="$((i-1))h"
  OUT_A="$OUT_DIR/splunk_A_${DAY}_${FROM}_${TO}.jsonl"
  echo "  A ${FROM}..${TO} -> ${OUT_A}"
  python scripts/fetch_data.py splunk "index=${INDEX} earliest=-${FROM} latest=-${TO} | fields *" --out "$OUT_A" || true
done

echo "[B] collecting with exclude: ${B_EXCLUDE}"
for ((i=HOURS;i>=1;i--)); do
  FROM="${i}h"; TO="$((i-1))h"
  OUT_B="$OUT_DIR/splunk_B_${DAY}_${FROM}_${TO}.jsonl"
  echo "  B ${FROM}..${TO} -> ${OUT_B}"
  python scripts/fetch_data.py splunk "index=${INDEX} earliest=-${FROM} latest=-${TO} NOT ${B_EXCLUDE} | fields *" --out "$OUT_B" || true
done

cat "$OUT_DIR"/splunk_A_${DAY}_*.jsonl > "$OUT_DIR/splunk_A_${DAY}.jsonl"
cat "$OUT_DIR"/splunk_B_${DAY}_*.jsonl > "$OUT_DIR/splunk_B_${DAY}.jsonl"

echo "[report] writing reports/ab_${DAY}.*"
python scripts/ab_report.py --a "$OUT_DIR/splunk_A_${DAY}.jsonl" --b "$OUT_DIR/splunk_B_${DAY}.jsonl" --out-prefix "reports/ab_${DAY}"

echo "done"


