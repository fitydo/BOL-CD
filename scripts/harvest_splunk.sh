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
  QUERY_A="index=${INDEX} earliest=-${FROM}@h latest=-${TO}@h+59s | fields *"
  echo "  A ${FROM}..${TO} -> ${OUT_A}"
  echo "[DEBUG] A: ${QUERY_A}"
  python scripts/fetch_data.py splunk "${QUERY_A}" --out "$OUT_A" || true
done

echo "[B] collecting with exclude: ${B_EXCLUDE}"
# Always wrap B_EXCLUDE with parentheses if not already wrapped
_B_EXPR="${B_EXCLUDE}"
if [[ "${_B_EXPR}" != \(*\) ]]; then
  _B_EXPR="(${_B_EXPR})"
fi
for ((i=HOURS;i>=1;i--)); do
  FROM="${i}h"; TO="$((i-1))h"
  OUT_B="$OUT_DIR/splunk_B_${DAY}_${FROM}_${TO}.jsonl"
  QUERY_B="index=${INDEX} earliest=-${FROM}@h latest=-${TO}@h+59s NOT ${_B_EXPR} | fields *"
  echo "  B ${FROM}..${TO} -> ${OUT_B}"
  echo "[DEBUG] B: ${QUERY_B}"
  python scripts/fetch_data.py splunk "${QUERY_B}" --out "$OUT_B" || true
done

cat "$OUT_DIR"/splunk_A_${DAY}_*.jsonl > "$OUT_DIR/splunk_A_${DAY}.jsonl"
cat "$OUT_DIR"/splunk_B_${DAY}_*.jsonl > "$OUT_DIR/splunk_B_${DAY}.jsonl"

echo "[report] writing reports/ab_${DAY}.*"
python scripts/ab_report.py --a "$OUT_DIR/splunk_A_${DAY}.jsonl" --b "$OUT_DIR/splunk_B_${DAY}.jsonl" --out-prefix "reports/ab_${DAY}"

echo "done"


