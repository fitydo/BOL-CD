## 目的
A/B検証の崩れを防ぐための標準化（すぐやる版）

## 変更点
- [ ] 決定的ランダム割付（entity_id, rule_id）
- [ ] 同一観測窓（開始/終了日時を明記）
- [ ] 重複キー定義の明文化と version
- [ ] 日次 JSON/Markdown 出力
- [ ] Prometheus メトリクス
- [ ] Helm CronJob（APIとPVC共有）
- [ ] プリフライト検証
- [ ] ドキュメント 4点セット

## 検証手順
- [ ] `pytest -q tests/ab/test_ab_pipeline.py` が緑
- [ ] `scripts/ab/ab_preflight.py --reports-dir /reports` が OK
- [ ] A/B 事前件数差 ±5% 以内
- [ ] 最新 `ab_YYYY-MM-DD.json` が /reports に生成
- [ ] /metrics に `bolcd_ab_*` が反映

## ダッシュボード裏SQL/KQL
- [ ] 添付済み（Splunk/Sentinel/OpenSearch）

## ロールバック
- [ ] CronJob 停止で日次生成停止
- [ ] PVC のバックアップ/保持方針明記

