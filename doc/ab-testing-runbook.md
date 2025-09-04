### A/Bテスト不具合の原因確認と改善手順（Runbook）

このRunbookは、BOL‑CDのA/Bテスト機能が想定通りに動作しない場合の切り分けと改善策、ならびに10日間の検証レポート作成までの実務手順をまとめたものです。対象ファイルは `deploy/helm/`、`src/bolcd/api/app.py`、`scripts/`、`grafana/` 配下です。

---

### 1. CronJob とデータ収集の確認

- 参照ファイル: `deploy/helm/templates/cron-ab-daily.yaml`, `deploy/helm/values-*.yaml`
- デフォルトでは `INDEX="_internal"`、`B_EXCLUDE="sourcetype=splunkd*"`。これでは内部ログの除外に留まり、意図した抑制検証になりにくい。

対策（Helm values 例）:

```yaml
# values-prod.yaml 例
cron:
  abDaily:
    enabled: true
    schedule: "5 1 * * *"    # 毎日 01:05
    hours: 24
    keys: ["host", "index", "sourcetype", "source", "component", "group"]
    splunk:
      index: "security"      # 本番の監視対象インデックス
      exclude: "signature=LowPriorityAlert OR rule_name=Noise*"  # 抑制候補条件

reportsPVC:
  enabled: true               # Cron と API で共有
```

チェックポイント:
- `CronJob` の `env` で `INDEX` と `B_EXCLUDE` が上記に反映されること。
- `volumes` が `reports` PVC を参照し、`/reports` にマウントされていること（Cron/Deployment 両方）。

---

### 2. アプリ側メトリクス更新とレポート共有

- 参照ファイル: `src/bolcd/api/app.py`
- エンドポイント: `/metrics`
- 実装: `_update_ab_metrics_from_reports()` は `BOLCD_REPORTS_DIR`（デフォルト `/reports`）直下の `ab_YYYY-MM-DD*.json` から最新を読み取り、`bolcd_ab_*` Gauge を更新。

確認事項:
- `Deployment` が `reports` PVC を `readOnly: true` で `/reports` にマウントしていること。
- `BOLCD_REPORTS_DIR` を変更する場合は環境変数で上書き（例: ローカルでは `BOLCD_REPORTS_DIR=reports`）。

---

### 3. Prometheus/Grafana 設定

- 参照ファイル: `deploy/helm/templates/service.yaml`, `deploy/helm/templates/servicemonitor.yaml`, `deploy/helm/templates/grafana-dashboard.yaml`, `grafana/bolcd-ab.json`
- Prometheus Operator 利用時は `monitor.serviceMonitorEnabled: true` を有効化。`ServiceMonitor` は `jobLabel: app` を使用し、`app: bolcd` がジョブ名となる。

確認/対策:
- Grafana クエリで `job="bolcd"` など、実際のジョブ名と一致しているか（Operator 以外のスクレイプ方法を使う場合は、実ジョブ名に合わせてクエリ修正）。
- A/B 用メトリクスはダッシュボードで `bolcd_ab_*` を参照。`grafana/bolcd-ab.json` では `%` 表示（unit: percent）を設定済み。
- 「Report age (minutes)」= `(time() - bolcd_ab_last_file_mtime)/60` が増え続ける場合、Cron 停止やファイル未共有（PVC不備）を疑う。

---

### 4. ローカル検証（手動実行）

- 参照ファイル: `scripts/harvest_splunk.sh`
- 事前に環境変数を設定:

```bash
export BOLCD_SPLUNK_URL="https://<your-splunk>"
export BOLCD_SPLUNK_TOKEN="********"
```

- 収集とレポート生成（前日24時間、対象INDEX/除外条件を指定）:

```bash
bash scripts/harvest_splunk.sh data/raw security 24 'signature="DummyAlert" OR rule_name=Test'
```

- 出力: `data/raw/` に A/B の JSONL、`reports/ab_YYYY-MM-DD.{json,md}` が生成。
- アプリ起動時は `BOLCD_REPORTS_DIR=reports` を設定して、`/reports` ではなくカレントの `reports/` を参照させることが可能。

---

### 5. 10日間の検証レポート

手順A（ファイルベース周集計の応用）:
1) 10日間、毎日 `cron.abDaily` で `raw/splunk_A_YYYY-MM-DD.jsonl` と `raw/splunk_B_YYYY-MM-DD.jsonl` を蓄積。
2) 期間集計（週次スクリプトの期間指定活用）:

```bash
python scripts/ab_weekly.py \
  --prefix-a /reports/raw/splunk_A_ \
  --prefix-b /reports/raw/splunk_B_ \
  --start 2025-08-01 --end 2025-08-10 \
  --keys host index sourcetype source component group \
  --out-prefix /reports/ab_weekly_2025-08-01_2025-08-10
```

- 生成物: `/reports/ab_weekly_...{.csv,.md}`（各日の `a_total/b_total/reduction_*` を表とMarkdownに出力）。

手順B（Prometheus 時系列の活用）:
- `bolcd_ab_reduction_by_count` などを日次でサンプリングし、Grafana の Time-series で 10日間推移を可視化（`offset` や `subquery` で 1d 単位集計）。

レポート要素の推奨:
- 日次削減率推移グラフ（count/unique）。
- 10日合計の A/B 件数比較と総合削減率。
- 抑制上位カテゴリおよび B の新規（回帰）カテゴリ上位（`scripts/ab_report.py` の `top` 出力を利用）。
- PoC のKPI対比（Docsの基準に対する実績）。

---

### 6. 典型トラブルと対処

- メトリクスが0のまま: `/reports/ab_*.json` が無い、または API から見える場所に未配置。`reportsPVC.enabled` を有効化し、Cron/Deployment の両方で同一PVCをマウント。
- 期待と異なる削減率: `INDEX/B_EXCLUDE` が想定と不一致。values を修正し再デプロイ。
- Grafana にダミー/古い値: Cron 停止やファイル未更新が原因。`bolcd_ab_last_file_mtime` と「Report age」で確認。必要に応じてメトリクス名変更でシリーズを切替。

---

### 7. 変更時の具体的操作例

Helm の上書き（例: prod 環境で EXCLUDE を更新）:

```bash
helm upgrade --install bolcd ./deploy/helm \
  -f deploy/helm/values-prod.yaml \
  --set cron.abDaily.splunk.index=security \
  --set-string cron.abDaily.splunk.exclude='signature="LowPriorityAlert" OR rule_name=Noise*' \
  --set reportsPVC.enabled=true
```

---

### 8. 将来拡張メモ（ユーザー安定割当の実装指針）

- 今回はログイベント単位のA/B分割。ユーザー単位での安定割当が必要な場合は、`user_id` や `session_id` のハッシュ偶奇でA/Bを決定し、同一ユーザーは常に同一群に割当。収集クエリや前処理で群ラベルを付与したうえで、同一キーでの集計が安定するよう `--keys` を調整する。


