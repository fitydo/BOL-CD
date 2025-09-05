#!/bin/bash
# A/B日次レポート生成スクリプト
cd /home/yoshi/workspace/BOL-CD
DATE=$(date +%Y-%m-%d)

# 1. データ取得（実際はSIEM連携）
# python scripts/fetch_data.py --source splunk --date $DATE

# 2. A/B分割
if [ -f data/raw/events_$DATE.jsonl ]; then
    python scripts/ab/ab_split.py --in data/raw/events_$DATE.jsonl --out-dir data/ab --key-fields entity_id,rule_id
    
    # 3. レポート生成
    python scripts/ab/ab_report.py --in-a data/ab/A.jsonl --in-b data/ab/B.jsonl --out-dir reports --date-label $DATE
    
    echo "A/B report generated for $DATE"
fi
