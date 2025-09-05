## 目的
KPI（Noise / Ops / Cost / Risk）を Prometheus + Grafana で標準可視化

## 変更点
- [ ] 日次KPI計算 `scripts/kpi/compute_kpi.py`
- [ ] /metrics に KPI 反映（`app/metrics/kpi_metrics.py`）
- [ ] Helm: `cron-kpi-daily` + PVC 共有
- [ ] Grafana ダッシュボード ConfigMap
- [ ] ドキュメント `docs/kpi/KPI-Dashboard.md`
- [ ] 最小 pytest / Makefile / CI

## 検証手順
- [ ] `pytest -q tests/kpi/test_kpi_pipeline.py` 成功
- [ ] ローカルで `/reports/ab_YYYY-MM-DD.json` と `cases.jsonl` を用意 → `make kpi-daily`
- [ ] `/metrics` に `bolcd_*` KPI が出現
- [ ] Grafana に「BOL-CD KPI」ダッシュボードが表示され、値が更新

## ダッシュボード裏SQL/KQL
- [ ] 添付済み（Splunk/Sentinel/OpenSearch）

## 留意点
- cases スキーマ（detected/triaged/resolved/status）の整備
- Cost 利用時は `values.yaml` で ingest と $/GB を指定

