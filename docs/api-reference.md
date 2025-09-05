# BOL-CD API リファレンス

## 概要

BOL-CD APIは、アラート削減と因果分析機能を提供するRESTful APIです。

- **ベースURL**: `http://localhost:8080` (デフォルト)
- **認証**: API Key (ヘッダー: `X-API-Key`)
- **形式**: JSON (一部エンドポイントはXML/GraphMLも対応)
- **OpenAPI仕様**: `/api/openapi.yaml`

## 認証

### API Key認証

すべてのAPIリクエストには、`X-API-Key`ヘッダーが必要です：

```bash
curl -H "X-API-Key: viewer:your-key" http://localhost:8080/api/health
```

### ロール

| ロール | 権限 | 用途 |
|--------|------|------|
| `viewer` | 読み取り専用 | ダッシュボード表示、レポート閲覧 |
| `operator` | 読み書き | イベント処理、ルール管理 |
| `admin` | フルアクセス | SIEM書き戻し、設定変更 |

## エンドポイント一覧

### ヘルスチェック

#### `GET /api/health`
システムの健全性を確認

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-05T12:00:00Z",
  "version": "1.0.0"
}
```

#### `GET /livez`
生存性チェック（Kubernetes用）

#### `GET /readyz`
準備状態チェック（Kubernetes用）

### メトリクス

#### `GET /metrics`
Prometheus形式のメトリクス取得

**レスポンス例:**
```
# HELP bolcd_requests_total Total API requests
# TYPE bolcd_requests_total counter
bolcd_requests_total{path="/api/health"} 42.0
# HELP bolcd_ab_reduction_by_count Reduction by count for latest daily AB
# TYPE bolcd_ab_reduction_by_count gauge
bolcd_ab_reduction_by_count 0.585
```

### イベント処理

#### `POST /api/encode`
イベントデータをエンコード

**リクエスト:**
```json
{
  "events": [
    {
      "entity_id": "host-001",
      "rule_id": "rule-123",
      "severity": "high",
      "timestamp": "2025-09-05T12:00:00Z"
    }
  ]
}
```

**レスポンス:**
```json
{
  "encoded_count": 1,
  "dimensions": 10,
  "segments": ["default"]
}
```

#### `POST /api/edges/recompute`
因果グラフの再計算

**必要ロール:** `operator` または `admin`

**リクエスト:**
```json
{
  "events_path": "/data/events.jsonl",
  "persist_dir": "/reports/2025-09-05",
  "epsilon": 0.02,
  "margin_delta": 0.0,
  "fdr_q": 0.01,
  "segments": ["time_window", "severity"]
}
```

**レスポンス:**
```json
{
  "status": "success",
  "edges_count": 42,
  "pruned_count": 15,
  "processing_time_ms": 1234
}
```

**エラーレスポンス (403):**
```json
{
  "detail": "Insufficient permissions for operator role"
}
```

### グラフ取得

#### `GET /api/graph`
計算済みグラフの取得

**パラメータ:**
- `format`: 出力形式 (`json`, `graphml`, `dot`)
- `segment`: セグメント名（省略時は全体）

**例:**
```bash
# JSON形式
curl -H "X-API-Key: viewer:key" \
  "http://localhost:8080/api/graph?format=json"

# GraphML形式（XML）
curl -H "X-API-Key: viewer:key" \
  "http://localhost:8080/api/graph?format=graphml"
```

**JSONレスポンス例:**
```json
{
  "nodes": [
    {"id": "rule_001", "label": "SSH Brute Force", "severity": "high"},
    {"id": "rule_002", "label": "Privilege Escalation", "severity": "critical"}
  ],
  "edges": [
    {
      "source": "rule_001",
      "target": "rule_002",
      "weight": 0.85,
      "confidence": 0.95,
      "support": 42
    }
  ],
  "metadata": {
    "total_events": 10000,
    "computation_time": "2025-09-05T12:00:00Z",
    "reduction_rate": 0.585
  }
}
```

### ルール管理

#### `GET /api/rules`
全ルールの一覧取得

**レスポンス:**
```json
{
  "rules": [
    {
      "name": "ssh_brute_force",
      "enabled": true,
      "severity": "high",
      "query": "EventID=4625 AND TargetUserName!=*$",
      "description": "SSH brute force detection"
    }
  ],
  "total": 42
}
```

#### `GET /api/rules/{name}`
特定ルールの詳細取得

#### `POST /api/rules`
新規ルールの作成

**必要ロール:** `operator` または `admin`

**リクエスト:**
```json
{
  "name": "new_rule",
  "query": "EventID=4688 AND CommandLine=*powershell*",
  "severity": "medium",
  "enabled": true,
  "description": "PowerShell execution detection"
}
```

#### `PUT /api/rules/{name}`
ルールの更新

#### `DELETE /api/rules/{name}`
ルールの削除

**必要ロール:** `admin`

#### `POST /api/rules/apply`
ルールセットの適用

**リクエスト:**
```json
{
  "rules": ["rule1", "rule2"],
  "target_events": "/data/events.jsonl",
  "dry_run": true
}
```

**レスポンス:**
```json
{
  "applied": 2,
  "matched_events": 150,
  "suppressed_events": 89,
  "reduction_rate": 0.593
}
```

### レポート

#### `GET /api/reports/daily/latest`
最新の日次レポート取得

**レスポンス:**
```json
{
  "date": "2025-09-05",
  "reduction_by_count": 0.585,
  "reduction_by_unique": 0.423,
  "suppressed_count": 5850,
  "new_in_b_count": 0,
  "top_suppressed": [
    {"signature": "Info Log", "count": 2000},
    {"signature": "Debug Message", "count": 1500}
  ]
}
```

#### `GET /api/reports/daily/{date}`
指定日のレポート取得

**例:**
```bash
curl -H "X-API-Key: viewer:key" \
  http://localhost:8080/api/reports/daily/2025-09-05
```

### SIEM連携

#### `POST /api/siem/writeback`
SIEMへのルール書き戻し

**必要ロール:** `admin`

**リクエスト:**
```json
{
  "target": "splunk",
  "rules": [
    {
      "name": "BOLCD_Suppression_001",
      "spl": "index=security | where severity!=\"info\"",
      "app": "search",
      "owner": "admin"
    }
  ],
  "dry_run": false
}
```

**対応SIEM:**
- `splunk`: Splunk Enterprise/Cloud
- `sentinel`: Azure Sentinel
- `opensearch`: OpenSearch/Elasticsearch

**レスポンス:**
```json
{
  "status": "success",
  "written": 1,
  "details": [
    {
      "rule": "BOLCD_Suppression_001",
      "status": "created",
      "siem_id": "saved_search_12345"
    }
  ]
}
```

**エラーレスポンス (429):**
```json
{
  "detail": "Rate limit exceeded. Please retry after 60 seconds."
}
```

### 監査

#### `GET /api/audit`
監査ログの取得

**必要ロール:** `admin`

**パラメータ:**
- `start_time`: 開始時刻 (ISO 8601)
- `end_time`: 終了時刻
- `user`: ユーザーフィルター
- `action`: アクションフィルター

**レスポンス:**
```json
{
  "entries": [
    {
      "timestamp": "2025-09-05T12:00:00Z",
      "user": "admin",
      "action": "rules.create",
      "resource": "ssh_detection",
      "result": "success",
      "ip": "192.168.1.100"
    }
  ],
  "total": 150
}
```

#### `GET /api/audit/verify`
監査ログの整合性検証

## エラーハンドリング

### HTTPステータスコード

| コード | 意味 | 説明 |
|--------|------|------|
| 200 | OK | リクエスト成功 |
| 400 | Bad Request | 不正なリクエスト形式 |
| 401 | Unauthorized | 認証失敗 |
| 403 | Forbidden | 権限不足 |
| 404 | Not Found | リソースが見つからない |
| 422 | Unprocessable Entity | バリデーションエラー |
| 429 | Too Many Requests | レート制限超過 |
| 500 | Internal Server Error | サーバーエラー |

### エラーレスポンス形式

```json
{
  "detail": "エラーの詳細メッセージ",
  "type": "error_type",
  "instance": "/api/endpoint",
  "status": 400
}
```

## レート制限

デフォルトで以下のレート制限が適用されます：

- **RPS (Requests Per Second)**: 10
- **バースト**: 20

レート制限に達した場合、`429 Too Many Requests`が返されます。

ヘッダー情報：
- `X-RateLimit-Limit`: 制限値
- `X-RateLimit-Remaining`: 残りリクエスト数
- `X-RateLimit-Reset`: リセット時刻

## ページネーション

大量データを返すエンドポイントはページネーションをサポート：

**パラメータ:**
- `page`: ページ番号（1から開始）
- `per_page`: 1ページあたりの件数（デフォルト: 100、最大: 1000）

**レスポンスヘッダー:**
- `X-Total-Count`: 総件数
- `X-Page`: 現在のページ
- `X-Per-Page`: 1ページあたりの件数

## WebSocket (将来実装予定)

リアルタイムイベントストリーミング用：

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New alert:', data);
};
```

## SDK使用例

### Python

```python
import requests

class BOLCDClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {'X-API-Key': api_key}
    
    def get_health(self):
        return requests.get(
            f"{self.base_url}/api/health",
            headers=self.headers
        ).json()
    
    def recompute_edges(self, events_path):
        return requests.post(
            f"{self.base_url}/api/edges/recompute",
            headers=self.headers,
            json={"events_path": events_path}
        ).json()

# 使用例
client = BOLCDClient('http://localhost:8080', 'admin:secret')
health = client.get_health()
print(f"Status: {health['status']}")
```

### JavaScript/TypeScript

```typescript
class BOLCDClient {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async getHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/health`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    return response.json();
  }

  async recomputeEdges(eventsPath: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/edges/recompute`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ events_path: eventsPath })
    });
    return response.json();
  }
}

// 使用例
const client = new BOLCDClient('http://localhost:8080', 'admin:secret');
const health = await client.getHealth();
console.log(`Status: ${health.status}`);
```

### cURL

```bash
# 基本的な使用
curl -H "X-API-Key: viewer:key" http://localhost:8080/api/health

# POSTリクエスト
curl -X POST \
  -H "X-API-Key: operator:key" \
  -H "Content-Type: application/json" \
  -d '{"events_path": "/data/events.jsonl"}' \
  http://localhost:8080/api/edges/recompute

# ファイルアップロード
curl -X POST \
  -H "X-API-Key: operator:key" \
  -F "file=@events.jsonl" \
  http://localhost:8080/api/upload

# ページネーション
curl -H "X-API-Key: viewer:key" \
  "http://localhost:8080/api/rules?page=2&per_page=50"
```

## ベストプラクティス

1. **API Keyの管理**
   - 環境変数で管理
   - 定期的なローテーション
   - ロール別のキー発行

2. **エラーハンドリング**
   - リトライロジックの実装
   - 指数バックオフ
   - サーキットブレーカー

3. **パフォーマンス**
   - 結果のキャッシング
   - バッチ処理の活用
   - 非同期処理

4. **セキュリティ**
   - HTTPS使用
   - 最小権限の原則
   - 監査ログの活用

## 変更履歴

### v1.0.0 (2025-09-05)
- 初回リリース
- 基本的なCRUD操作
- SIEM連携（Splunk, Sentinel, OpenSearch）

### v1.1.0 (予定)
- WebSocketサポート
- GraphQL API
- バッチ操作の拡充
