# 運用 Runbook / Operations SOP

## 1. デプロイ
- Docker Compose / Kubernetes（Helm）に対応。
- Secrets / 環境変数:
  - `BOLCD_API_KEYS`（例: `view:viewer,testop:operator`）
  - Splunk: `BOLCD_SPLUNK_URL`, `BOLCD_SPLUNK_TOKEN`
  - Sentinel: `BOLCD_SENTINEL_WORKSPACE_ID`, `BOLCD_AZURE_TOKEN`, `BOLCD_AZURE_SUBSCRIPTION_ID`, `BOLCD_AZURE_RESOURCE_GROUP`, `BOLCD_AZURE_WORKSPACE_NAME`
  - OpenSearch: `BOLCD_OPENSEARCH_ENDPOINT`, `BOLCD_OPENSEARCH_BASIC`

## 2. 初期設定
- `configs/thresholds.yaml` と `configs/segments.yaml` を用意。
- `fdr_q=0.01`, `epsilon=0.005`, `delta` は指標の 2–5% 幅で開始。

## 3. 監視（Observability）
- メトリクス: `eps`, `latency_p95_ms`, `edges_total`, `edges_pruned_tr_ratio`。
- アラート: p95>100ms（5分間）、edges_pruned_tr_ratio<0.2（連鎖化不全）。
- Prometheus Operator 環境では `ServiceMonitor` を有効化（`monitor.serviceMonitorEnabled: true`）。

## 4. しきい再学習
1) `POST /edges/recompute` を nightly 実行。
2) diff レポートを確認（エッジ増減、3/n 上限）。
3) 大きな変化は `staging` で A/B 確認後に本番へ。

## 5. 障害時
- SIEM への書き戻しを停止（read‑only モード）→ 再学習をロールバック。
- バックアップ：監査ログ（`/app/logs`、PVC）の日次スナップショット。
  - PVC モード: Helm の `backup.enabled: true`, `backup.pvc.enabled: true` で CronJob を有効化
  - S3 モード: `backup.s3.enabled: true` と AWS 資格情報 Secret（`bolcd-backup-aws`）を作成
  - 復元手順（PVC モード例）:
    1) 最新アーカイブを確認 `kubectl -n <ns> exec -ti <backup-pod> -- ls /backup`（PVC モードの場合）
    2) Pod 上で展開 `tar xzf /backup/audit-<ts>.tgz -C /tmp && kubectl cp <pod>:/tmp/logs ./logs` など
    3) `logs/audit.jsonl` をターゲット環境へ配置（必要に応じて再学習前にバックアップ）

## 6. 監査
- すべての辺追加/削除/しきい変更に署名ハッシュを付与し監査ログへ。
- 監査ストア: JSONL（`logs/audit.jsonl`）を既定に使用。将来的に SQLite/WORM 化を検討。
