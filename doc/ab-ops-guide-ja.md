# BOL-CD A/B検証 運用ガイド（失敗原因分析と改善）

本ガイドは、BOL-CD の A/B 検証が失敗・停滞する典型原因の切り分け手順と、確実に日次レポートを生成・可視化・通知するための運用手順をまとめたものです。Helm チャート／アプリ実装の現行仕様に準拠しています。

## 1. Deployment が Ready にならないときのチェックリスト

### 1-1. Secret 未設定／キー不足
- 必須シークレット（例）
  - `bolcd-apikeys`: `BOLCD_API_KEYS`（API キー列）
  - `bolcd-secrets`: Splunk/Sentinel/OpenSearch 等の接続情報
    - `splunk_url`, `splunk_token`
    - `sentinel_workspace_id`, `azure_token`, `azure_subscription_id`, `azure_resource_group`, `azure_workspace_name`
    - `opensearch_endpoint`, `opensearch_basic`
- Helm 値（一例）
  - `apiKeysSecret.enabled: true` かつ `apiKeysSecret.name/key` を参照
  - `secretEnv` 配列で上記キーを `valueFrom.secretKeyRef` として注入
- 事前確認と作成例
```bash
kubectl -n <ns> get secret bolcd-apikeys bolcd-secrets

# 例: bolcd-apikeys（API キー列）
kubectl -n <ns> create secret generic bolcd-apikeys \
  --from-literal=BOLCD_API_KEYS="view:viewer,testop:operator,admin:admin"

# 例: bolcd-secrets（Splunk）
kubectl -n <ns> create secret generic bolcd-secrets \
  --from-literal=splunk_url="https://splunk.example.com" \
  --from-literal=splunk_token="<token>"
```
- ExternalSecret を利用する場合
  - `externalSecrets.enabled: true` と SecretStore を設定
  - 作成完了まで待機（CI では Helm 適用前に生成を先行、または Helm の timeout 延長）
```bash
kubectl -n <ns> get externalsecret
kubectl -n <ns> describe externalsecret <name>
```

### 1-2. コンテナイメージの Pull 失敗
- 値例: `image.repository: ghcr.io/...` とコミット由来の `image.tag: sha-xxxxxx`
- GHCR がプライベートの場合は Pull 用 Secret を作成し、`imagePullSecrets` で参照
```bash
# GHCR 用 pull secret（<gh-user>, <ghcr-pat> を適宜設定）
kubectl -n <ns> create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<gh-user> \
  --docker-password=<ghcr-pat>

# values.yaml 例
# imagePullSecrets:
#   - name: ghcr-pull
```
- CI/CD ではビルド→`ghcr push`→`values.image.tag` 反映の整合を担保

### 1-3. PVC（永続ボリューム）のバインド不良
- レポート共有: `reportsPVC.enabled: true`（推奨）
  - `reportsPVC.storageClass` をクラスタに合わせて設定、または `existingClaim` を指定
- 監査ログ: `persistence.logs.enabled: true`（または `logs.emptyDir: true` 開発用）
- 事前確認
```bash
kubectl -n <ns> get sc
kubectl -n <ns> get pvc
kubectl -n <ns> describe pvc <name>
```
- 一時回避（検証用）として `reportsPVC.enabled: false` で `emptyDir` も可能（本番は PVC 推奨）

### 1-4. 追加のデバッグの勘所
```bash
# Helm の自動ロールバックを一時停止し、イベントを確認
helm upgrade --install bolcd deploy/helm -n <ns> --timeout 10m --debug  # --atomic を外す

# Pod / イベント確認
kubectl -n <ns> get pods
kubectl -n <ns> describe pod <pod>
kubectl -n <ns> logs <pod> -c api --tail=200
```

## 2. 日次で A/B を自動実行しレポートを生成

### 2-1. CronJob の有効化とスケジュール
```yaml
cron:
  abDaily:
    enabled: true
    schedule: "5 1 * * *"   # 毎日 01:05
    hours: 24
    keys: ["index","sourcetype","rule_name","severity"]
    splunk:
      index: "security"
      exclude: "severity=low OR rule_name=\"NoiseRule\""
    extraEnv:
      - name: BOLCD_SPLUNK_AUTH_SCHEME
        value: bearer

reportsPVC:
  enabled: true
  size: 5Gi
  storageClass: <your-sc>     # 必要に応じ指定
```
- CronJob は `secretEnv` により `BOLCD_SPLUNK_URL`/`BOLCD_SPLUNK_TOKEN` を参照。漏れがあると起動時に失敗します。
- `/reports` は CronJob／Deployment の両方で同一 PVC をマウント（レポート共有）。

### 2-2. 実行確認ポイント
```bash
kubectl -n <ns> get cronjob,job | grep bolcd-ab-daily
kubectl -n <ns> logs job/<job-name> --tail=200 | cat

# アプリ側から最新メトリクス確認（Port-Forward 等で）
curl -fsS http://<svc>:8080/metrics | grep '^bolcd_ab_'
```

### 2-3. 週次集計・通知・クリーンアップ（任意）
- 週次: `cron.abWeekly.enabled: true`
- 通知（Slack 等 Webhook）: `cron.abNotify.enabled: true` と `webhookSecret` を設定
- 期限超過ファイル削除: `cron.cleanup.enabled: true` と `keepDays: 14` など

## 3. ワークフロー全体と再現性の担保

### 3-1. データ収集 → レポート生成 → メトリクス更新
- 収集: 前日分を 1 時間刻みで A（全件）/B（除外適用）を取得
- 生成: `scripts/ab_report.py` が JSON/Markdown を `/reports/ab_YYYY-MM-DD.*` に出力
- 公開: アプリ `/metrics` が最新 JSON を読み取り `bolcd_ab_*` をエクスポート

### 3-2. 監視と可視化
- Prometheus（Operator）: `monitor.serviceMonitorEnabled: true`
- 代表アラート（PrometheusRule）
  - `BolcdABReportStale`: `bolcd_ab_last_file_mtime` でレポート停滞検知
  - `BolcdABReductionDrop`: 削減率の悪化
  - `BolcdABRegressions(Count)Spike`: B 側のみの新規増加
- Grafana ダッシュボードは Helm で同梱（A/B パネルあり）

### 3-3. ステージング検証／CI への組込み
- ステージング: `deploy/helm/values-ab-local.yaml` を併用し毎時実行（`schedule: "5 * * * *"`, `hours: 1`）
- CI 簡易比較: 必要に応じ `scripts/ab_report.py` をパイプラインで実行し Markdown をアーティファクト化

### 3-4. ローカル／WSL での手動検証
```bash
# 必要変数を指定（例: WSL では Bearer 利用を推奨）
export BOLCD_SPLUNK_URL=https://splunk.example.com
export BOLCD_SPLUNK_TOKEN=<token>
export BOLCD_SPLUNK_AUTH_SCHEME=bearer

# 直近 24h をローカル収集→レポート作成
bash scripts/harvest_splunk.sh data/raw security 24 "severity=low OR rule_name=NoiseRule"
ls -l reports/ab_$(date +%F).*  # 出力確認
```

## 4. 障害時の切り分け順序（推奨フロー）
1) Secrets: `kubectl get secret` と `env` 注入の確認（Deployment/Cron 両方）
2) イメージ: `image.tag` の存在、`imagePullSecrets` の有無
3) ストレージ: `reportsPVC`/`logs` の PVC が Bound か
4) Cron: `kubectl get cronjob,job` と Job Pod のログ
5) アプリ: `/metrics` の `bolcd_ab_*` 値、`bolcd_ab_last_file_mtime` の更新
6) 値の見直し: `cron.abDaily.splunk.index/exclude/keys` の妥当性

## 5. 参考 Helm 値（抜粋例）
```yaml
image:
  repository: ghcr.io/your-org/bol-cd
  tag: sha-<commit>

apiKeysSecret:
  enabled: true
  name: bolcd-apikeys
  key: BOLCD_API_KEYS

secretEnv:
  - name: BOLCD_SPLUNK_URL
    secretName: bolcd-secrets
    secretKey: splunk_url
  - name: BOLCD_SPLUNK_TOKEN
    secretName: bolcd-secrets
    secretKey: splunk_token

reportsPVC:
  enabled: true
  size: 5Gi
  storageClass: <your-sc>

cron:
  abDaily:
    enabled: true
    schedule: "5 1 * * *"
    hours: 24
    keys: ["index","sourcetype","rule_name","severity"]
    splunk:
      index: "security"
      exclude: "severity=low OR rule_name=\"NoiseRule\""
    extraEnv:
      - name: BOLCD_SPLUNK_AUTH_SCHEME
        value: bearer

monitor:
  serviceMonitorEnabled: true
  grafana:
    enabled: true
  alertsEnabled: true
```

---
このガイドは `deploy/helm/templates/*.yaml`（Deployment/Cron/PrometheusRule 等）と `src/bolcd/api/app.py`（メトリクス更新）に基づいています。環境差分は Helm values で管理し、Runbook と値の整合を定期的にレビューしてください。


