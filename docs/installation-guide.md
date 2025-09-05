# BOL-CD インストールガイド

## 📋 前提条件

### システム要件
- **OS**: Linux (Ubuntu 20.04+, RHEL 8+) / macOS / Windows (WSL2)
- **Python**: 3.9以上
- **メモリ**: 最小4GB、推奨8GB以上
- **ディスク**: 10GB以上の空き容量
- **CPU**: 2コア以上、推奨4コア以上

### 必要なソフトウェア
- Docker 20.10+ (コンテナデプロイの場合)
- Kubernetes 1.21+ (K8sデプロイの場合)
- Helm 3.7+ (Helmデプロイの場合)

## 🚀 クイックスタート

### 1. Dockerを使用した起動（推奨）

```bash
# イメージの取得
docker pull ghcr.io/fitydo/bol-cd:latest

# 基本的な起動
docker run -d \
  --name bolcd \
  -p 8080:8080 \
  -e BOLCD_API_KEYS="viewer:readonly,admin:secretkey123" \
  ghcr.io/fitydo/bol-cd:latest

# ヘルスチェック
curl http://localhost:8080/api/health
```

### 2. Docker Composeを使用した起動

`docker-compose.yml`を作成:

```yaml
version: '3.8'

services:
  bolcd:
    image: ghcr.io/fitydo/bol-cd:latest
    ports:
      - "8080:8080"
    environment:
      - BOLCD_API_KEYS=viewer:readonly,operator:operkey,admin:adminkey
      - BOLCD_CORS_ORIGINS=http://localhost:3000,https://app.example.com
      - BOLCD_RATE_LIMIT_ENABLED=1
      - BOLCD_RATE_LIMIT_RPS=10
    volumes:
      - ./data:/data
      - ./reports:/reports
      - ./logs:/logs
    restart: unless-stopped

  # 高可用性構成の場合（オプション）
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

起動:

```bash
docker-compose up -d
```

## 📦 Pythonパッケージとしてのインストール

### 開発環境

```bash
# リポジトリのクローン
git clone https://github.com/yourorg/bol-cd.git
cd bol-cd

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# 開発モードでインストール
pip install -e .

# APIサーバーの起動
uvicorn bolcd.api.app:app --host 0.0.0.0 --port 8080 --reload
```

### 本番環境

```bash
# 本番用依存関係のインストール
pip install -r requirements.txt

# Gunicornを使用した起動（推奨）
pip install gunicorn
gunicorn bolcd.api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 \
  --access-logfile - \
  --error-logfile -
```

## ☸️ Kubernetes/Helmデプロイ

### Helmを使用したインストール

```bash
# Helmリポジトリの追加（将来的に公開予定）
# helm repo add bolcd https://charts.bolcd.io
# helm repo update

# 現在はローカルチャートを使用
git clone https://github.com/yourorg/bol-cd.git
cd bol-cd

# 基本インストール
helm install bolcd ./deploy/helm \
  --namespace bolcd \
  --create-namespace \
  --set image.tag=latest

# カスタム設定でのインストール
cat <<EOF > custom-values.yaml
replicaCount: 3

env:
  BOLCD_API_KEYS: "viewer:viewkey,operator:opkey,admin:adminkey"
  BOLCD_CORS_ORIGINS: "https://app.example.com"
  BOLCD_REDIS_ENABLED: "1"
  BOLCD_REDIS_HOST: "redis-master.redis.svc.cluster.local"

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: bolcd.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: bolcd-tls
      hosts:
        - bolcd.example.com

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"

# 高可用性設定
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

# Prometheusメトリクス
serviceMonitor:
  enabled: true
EOF

helm install bolcd ./deploy/helm \
  --namespace bolcd \
  --create-namespace \
  -f custom-values.yaml
```

### 確認

```bash
# Podの状態確認
kubectl get pods -n bolcd

# サービスの確認
kubectl get svc -n bolcd

# ログの確認
kubectl logs -n bolcd -l app=bolcd --tail=100

# ポートフォワード（テスト用）
kubectl port-forward -n bolcd svc/bolcd 8080:8080
```

## 🔧 環境変数設定

### 必須設定

| 変数名 | 説明 | デフォルト | 例 |
|--------|------|----------|-----|
| `BOLCD_API_KEYS` | API認証キー（role:key形式） | なし | `viewer:key1,admin:key2` |

### SIEM連携設定

#### Splunk
```bash
export BOLCD_SPLUNK_URL="https://splunk.example.com:8089"
export BOLCD_SPLUNK_TOKEN="your-hec-token"
export BOLCD_SPLUNK_VERIFY_SSL="0"  # 自己署名証明書の場合
```

#### Azure Sentinel
```bash
export BOLCD_AZURE_TOKEN="your-azure-token"
export BOLCD_AZURE_SUBSCRIPTION_ID="sub-id"
export BOLCD_AZURE_RESOURCE_GROUP="rg-name"
export BOLCD_AZURE_WORKSPACE_NAME="workspace"
export BOLCD_SENTINEL_WORKSPACE_ID="workspace-id"
```

#### OpenSearch
```bash
export BOLCD_OPENSEARCH_ENDPOINT="https://opensearch.example.com:9200"
export BOLCD_OPENSEARCH_BASIC="username:password"
export BOLCD_OPENSEARCH_VERIFY_SSL="1"
```

### セキュリティ設定

```bash
# OIDC/OAuth2認証
export BOLCD_OIDC_ISS="https://auth.example.com/"
export BOLCD_OIDC_AUD="bolcd-api"
export BOLCD_OIDC_JWKS="https://auth.example.com/.well-known/jwks.json"

# CORS設定
export BOLCD_CORS_ORIGINS="https://app.example.com,https://admin.example.com"

# レート制限
export BOLCD_RATE_LIMIT_ENABLED="1"
export BOLCD_RATE_LIMIT_RPS="10"
export BOLCD_RATE_LIMIT_BURST="20"

# HTTPS強制
export BOLCD_REQUIRE_HTTPS="1"
export BOLCD_HSTS_ENABLED="1"
```

### 高可用性設定（Redis）

```bash
# スタンドアロンRedis
export BOLCD_REDIS_ENABLED="1"
export BOLCD_REDIS_HOST="redis.example.com"
export BOLCD_REDIS_PORT="6379"
export BOLCD_REDIS_PASSWORD="redis-password"
export BOLCD_REDIS_DB="0"

# Redis Sentinel（高可用性）
export BOLCD_REDIS_SENTINELS="sentinel1:26379,sentinel2:26379,sentinel3:26379"
export BOLCD_REDIS_SERVICE="mymaster"
```

## 🔍 動作確認

### APIヘルスチェック

```bash
# ヘルスチェック
curl http://localhost:8080/api/health

# 生存性チェック
curl http://localhost:8080/livez

# 準備状態チェック
curl http://localhost:8080/readyz

# メトリクス確認
curl http://localhost:8080/metrics
```

### 基本的なAPI操作

```bash
# API認証付きリクエスト
curl -H "X-API-Key: admin:adminkey" \
  http://localhost:8080/api/rules

# グラフ取得
curl -H "X-API-Key: viewer:viewkey" \
  http://localhost:8080/api/graph?format=json

# イベント処理
curl -X POST \
  -H "X-API-Key: operator:operkey" \
  -H "Content-Type: application/json" \
  -d '{"events_path": "/data/events.jsonl"}' \
  http://localhost:8080/api/edges/recompute
```

## 🔄 アップグレード

### Dockerの場合

```bash
# 新しいイメージの取得
docker pull ghcr.io/fitydo/bol-cd:latest

# 既存コンテナの停止と削除
docker stop bolcd
docker rm bolcd

# 新しいコンテナで起動
docker run -d --name bolcd ... ghcr.io/fitydo/bol-cd:latest
```

### Helmの場合

```bash
# チャートの更新
helm upgrade bolcd ./deploy/helm \
  --namespace bolcd \
  --reuse-values \
  --set image.tag=v1.1.0
```

## 🆘 トラブルシューティング

### よくある問題と解決方法

#### 1. APIが起動しない

```bash
# ログを確認
docker logs bolcd
# または
kubectl logs -n bolcd -l app=bolcd

# 一般的な原因:
# - ポート8080が既に使用中 → 別のポートを指定
# - 環境変数の設定ミス → 設定を確認
```

#### 2. SIEM接続エラー

```bash
# 接続テスト
python scripts/test_connection.py splunk

# 一般的な原因:
# - 認証情報の誤り → トークンを再確認
# - ネットワーク接続 → ファイアウォール設定を確認
# - SSL証明書エラー → VERIFY_SSL=0で一時的に無効化
```

#### 3. メモリ不足

```yaml
# Kubernetes の場合、リソース制限を調整
resources:
  requests:
    memory: "1Gi"
  limits:
    memory: "4Gi"
```

#### 4. レート制限エラー

```bash
# レート制限を緩和または無効化
export BOLCD_RATE_LIMIT_ENABLED="0"
# または
export BOLCD_RATE_LIMIT_RPS="100"
export BOLCD_RATE_LIMIT_BURST="200"
```

## 📚 次のステップ

1. [APIリファレンス](./api-reference.md) - 詳細なAPI仕様
2. [運用ガイド](./operations-guide.md) - 本番環境での運用方法
3. [A/Bテストガイド](./ab-ops-guide-ja.md) - アラート削減の設定と監視
4. [開発者ガイド](./developer-guide.md) - カスタマイズと拡張

## 📞 サポート

- GitHub Issues: https://github.com/yourorg/bol-cd/issues
- ドキュメント: https://docs.bolcd.io
- コミュニティ: https://community.bolcd.io
