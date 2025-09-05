## BOL-CD A/B検証 実施ガイド（ローカル/本番）

このガイドは、A/B検証を1ユーザー体験レベルで日次実行し、10日間の結果でエラー低減を確認できるようにするための手順です。

### 1) 収集・集計の正しい分岐適用（A 全件 / B 抑制後）
- Helm の日次 CronJob を有効化し、実データのインデックスと除外条件を設定してください。
- 例（本番 `values-prod.yaml` の上書き）:
```yaml
cron:
  abDaily:
    enabled: true
    schedule: "5 1 * * *"   # 日次 01:05
    hours: 24
    splunk:
      index: "security"     # ← 実データのインデックス
      exclude: "signature=Foo OR rule_name=Bar OR sourcetype=baz"  # ← 抑制条件
```
- CronJob 定義は `deploy/helm/templates/cron-ab-daily.yaml`。A 側は全件、B 側は `NOT (${exclude})` で収集します。
- 収集結果から日次レポート `/reports/ab_YYYY-MM-DD.json`（完全版）と `/reports/ab_YYYY-MM-DD_effects.json`（effects のみ）を生成します。

### 2) レポートの共有ストレージ（PVC）
- アプリと CronJob から同一の `/reports` を参照できるよう PVC を有効化します。
```yaml
reportsPVC:
  enabled: true
  size: 5Gi
```
- `Deployment` と CronJob 双方に同じ PVC がマウントされます（テンプレート済）。

### 3) メトリクス更新と Grafana 可視化
- API の `/metrics` は `/reports` の最新ファイルを読み取り、以下の Gauge を更新します:
  - `bolcd_ab_reduction_by_count`
  - `bolcd_ab_reduction_by_unique`
  - `bolcd_ab_suppressed_count`
  - `bolcd_ab_new_in_b_unique`, `bolcd_ab_new_in_b_count`
  - `bolcd_ab_last_file_mtime`
- Prometheus Operator を使用する場合:
  - `monitor.serviceMonitorEnabled: true` を有効化
  - ServiceMonitor は `jobLabel: app` を使用します（job ラベルは `bolcd`）
- Grafana ダッシュボード（Helm の ConfigMap）は `job=bolcd` を前提にした式へ調整済みです。

### 4) ローカル日次実行（Splunk）
- ローカル収集スクリプト: `scripts/harvest_splunk.sh`
```bash
export BOLCD_SPLUNK_URL="https://<your-splunk>"
export BOLCD_SPLUNK_TOKEN="********"

# 前日24時間を収集（A=全件, B=除外適用）、レポートを ./reports に出力
bash scripts/harvest_splunk.sh data/raw security 24 'signature="DummyAlert" OR rule_name="Test"'

# アプリ側の参照先（デフォルト /reports）をローカルに合わせる場合
export BOLCD_REPORTS_DIR=reports
uvicorn bolcd.api.app:app --reload --port 8080
```
- B 側除外は自動で括弧包みされ、複合条件でも安全にクエリされます。

### 5) 10日間のレポート化
- 10日分の `ab_YYYY-MM-DD.json` が `/reports` に蓄積されることを確認してください。
- 週次/期間集計ツール: `scripts/ab_weekly.py`（`--start`/`--end` で任意期間指定可）
```bash
python scripts/ab_weekly.py \
  --prefix-a /reports/raw/splunk_A_ \
  --prefix-b /reports/raw/splunk_B_ \
  --start 2025-08-01 --end 2025-08-10 \
  --keys host index sourcetype source component group \
  --out-prefix reports/ab_weekly_2025-08-01_2025-08-10
```

### 6) 典型トラブルと対策
- B 側が効いていない: インデックス/除外条件が開発用（`_internal`, `sourcetype=splunkd*`）のまま。Helm 値を本番向けに上書き。
- Grafana が 0 のまま: `/reports` が共有されていない（PVC 無効/マウント不整合）。`reportsPVC.enabled=true` を確認。
- 値が古い: `Report age (minutes)` が増え続ける → CronJob 失敗/権限/ネットワーク確認。
- 回帰が多い: 集計キーを安定したフィールドに限定（`values-prod.yaml` の `cron.abDaily.keys` を利用）。

### 7) クイック検証（毎時実行）
- セットアップ中は `hours: 1` と `schedule: "5 * * * *"` にすると 60 分毎に指標が更新され、Grafana で素早く挙動確認できます。安定後に 24h に戻してください。


