# マルチテナントアーキテクチャ設計書

## 概要

BOL-CDのエンタープライズ版では、複数の組織（テナント）を単一のインスタンスでサポートするマルチテナント機能を提供します。

## アーキテクチャ

### 1. テナント分離レベル

#### データ分離
- **論理分離**: 同一データベース内でtenant_idによる分離
- **物理分離**: テナント毎に独立したディレクトリ/ストレージ
- **ハイブリッド**: メタデータは共有、実データは分離

現在の実装: **物理分離**（セキュリティ重視）

### 2. コンポーネント構成

```
┌─────────────────────────────────────────┐
│            API Gateway                   │
│         (認証・ルーティング)              │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│        Tenant Manager                    │
│    (テナント識別・リソース管理)           │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┬──────────┬─────────┐
      │             │          │         │
┌─────▼────┐ ┌─────▼────┐ ┌──▼───┐ ┌───▼───┐
│Tenant A  │ │Tenant B  │ │...   │ │Tenant N│
│          │ │          │ │      │ │       │
│ - Data   │ │ - Data   │ │      │ │       │
│ - Rules  │ │ - Rules  │ │      │ │       │
│ - Config │ │ - Config │ │      │ │       │
└──────────┘ └──────────┘ └──────┘ └───────┘
```

## 実装詳細

### 1. テナント識別

#### APIキーベース
```python
# APIキー形式: {tenant_id}:{role}:{key}
X-API-Key: abc-123:admin:secret-key-here
```

#### JWTトークンベース
```json
{
  "sub": "user@example.com",
  "tenant_id": "abc-123",
  "roles": ["admin"],
  "exp": 1234567890
}
```

### 2. リソース制限

各テナントには以下の制限を設定可能：

| リソース | デフォルト | 最大値 |
|---------|-----------|--------|
| イベント/日 | 1,000,000 | 10,000,000 |
| ルール数 | 1,000 | 10,000 |
| ユーザー数 | 100 | 1,000 |
| API呼出/時 | 10,000 | 100,000 |
| ストレージ | 100GB | 1TB |

### 3. 機能フラグ

テナント毎に有効/無効を制御：

- `ml_optimization`: ML最適化
- `advanced_rules`: 高度なルール
- `siem_writeback`: SIEM書き戻し
- `custom_dashboards`: カスタムダッシュボード
- `sso_integration`: SSO連携
- `audit_logs`: 監査ログ
- `data_export`: データエクスポート

### 4. データ構造

#### ディレクトリ構成
```
/var/lib/bolcd/tenants/
├── tenants.json          # テナントメタデータ
├── {tenant_id}/
│   ├── data/            # イベントデータ
│   ├── rules/           # ルール定義
│   ├── reports/         # レポート
│   ├── logs/            # ログ
│   └── usage.json       # 使用量統計
└── archived/            # 削除済みテナント
```

#### テナント設定
```json
{
  "tenant_id": "abc-123",
  "name": "Acme Corp",
  "organization": "Acme Corporation",
  "created_at": "2025-09-05T12:00:00Z",
  "max_events_per_day": 1000000,
  "max_rules": 1000,
  "features": {
    "ml_optimization": true,
    "sso_integration": false
  },
  "siem_configs": [
    {
      "type": "splunk",
      "config": {
        "url": "https://splunk.acme.com",
        "token_hash": "abc123"
      }
    }
  ]
}
```

## API使用例

### テナント作成
```python
from bolcd.tenant.manager import get_tenant_manager

manager = get_tenant_manager()
tenant = manager.create_tenant(
    name="Acme Corp",
    organization="Acme Corporation",
    max_events_per_day=5000000,
    features={
        'ml_optimization': True,
        'sso_integration': True
    }
)
print(f"Created tenant: {tenant.tenant_id}")
```

### テナントコンテキストでの処理
```python
from bolcd.tenant.manager import get_tenant_context

# APIリクエストからtenant_idを取得
tenant_id = extract_tenant_from_request(request)

# テナントコンテキストで処理
ctx = get_tenant_context(tenant_id)

# 機能チェック
if not ctx.check_feature('ml_optimization'):
    raise PermissionError("ML optimization not enabled")

# クォータチェック
if not ctx.check_quota('events', 1000):
    raise QuotaExceededError("Event quota exceeded")

# テナント固有のデータディレクトリ
data_dir = ctx.get_data_dir('data')
process_events(data_dir / 'events.jsonl')
```

### API統合例
```python
from fastapi import Depends, HTTPException
from bolcd.tenant.manager import get_tenant_context

async def get_current_tenant(x_api_key: str = Header()):
    # APIキーからtenant_idを抽出
    parts = x_api_key.split(':')
    if len(parts) != 3:
        raise HTTPException(400, "Invalid API key format")
    
    tenant_id = parts[0]
    
    try:
        return get_tenant_context(tenant_id)
    except ValueError as e:
        raise HTTPException(403, str(e))

@app.post("/api/events")
async def process_events(
    events: List[Event],
    tenant: TenantContext = Depends(get_current_tenant)
):
    # テナント固有の処理
    if not tenant.check_quota('events', len(events)):
        raise HTTPException(429, "Event quota exceeded")
    
    data_dir = tenant.get_data_dir('data')
    # ... イベント処理 ...
```

## セキュリティ考慮事項

### 1. データ分離
- ファイルシステムレベルで完全分離
- データベースアクセス時は必ずtenant_id条件を付与
- クロステナントアクセスの防止

### 2. 認証・認可
- テナントIDの改竄防止（署名付きトークン）
- ロールベースアクセス制御（RBAC）
- 監査ログの記録

### 3. リソース保護
- DoS攻撃対策（レート制限）
- リソース枯渇防止（クォータ管理）
- 公平なリソース配分

## 運用

### 1. テナント管理CLI
```bash
# テナント作成
bolcd-tenant create --name "Acme Corp" --org "Acme Corporation"

# テナント一覧
bolcd-tenant list --active

# テナント更新
bolcd-tenant update abc-123 --max-events 5000000

# テナント削除（ソフト削除）
bolcd-tenant delete abc-123

# テナント削除（完全削除）
bolcd-tenant delete abc-123 --hard
```

### 2. 監視メトリクス
- `bolcd_tenant_count`: アクティブテナント数
- `bolcd_tenant_events_total{tenant_id}`: テナント別イベント数
- `bolcd_tenant_api_calls{tenant_id}`: テナント別API呼出数
- `bolcd_tenant_quota_usage{tenant_id,resource}`: クォータ使用率

### 3. バックアップ・リストア
```bash
# テナントデータのバックアップ
bolcd-backup tenant abc-123 --output /backup/abc-123.tar.gz

# テナントデータのリストア
bolcd-restore tenant abc-123 --input /backup/abc-123.tar.gz
```

## 移行計画

### Phase 1: 基本実装（完了）
- ✅ テナント管理システム
- ✅ リソース制限
- ✅ 機能フラグ

### Phase 2: API統合（次期）
- API Gateway統合
- 認証・認可の強化
- メトリクス収集

### Phase 3: UI対応（将来）
- テナント管理UI
- テナント切替機能
- 使用量ダッシュボード

## まとめ

このマルチテナント設計により、BOL-CDは以下を実現：

1. **スケーラビリティ**: 単一インスタンスで複数組織対応
2. **セキュリティ**: 完全なデータ分離
3. **柔軟性**: テナント毎の機能制御
4. **効率性**: リソースの最適利用
5. **管理性**: 統一された運用管理
