# BOL-CD アラートワークフロー

## 🚨 削減後のアラート取得方法

BOL-CDは「アラート削減エンジン」として動作し、削減後の重要アラートは以下の方法で取得できます：

## 1. アラートの流れ

```
[SIEM] → [BOL-CD削減エンジン] → [出力先]
                ↓
        削減率: 58.5%
        (Low/Medium を削減)
                ↓
    [High/Critical アラートのみ通過]
```

## 2. 削減後アラートの取得方法

### 方法1: SIEMへの書き戻し（推奨）
```python
# BOL-CDが削減ルールをSIEMに書き戻し
POST /api/siem/writeback
{
  "target": "splunk",
  "rules": [
    {
      "name": "BOLCD_Critical_Only",
      "spl": "index=security severity IN (high, critical) | where NOT match(signature, \"^(Info Log|Debug Message|Warning Alert)\")"
    }
  ]
}
```

**ユーザーの操作:**
- Splunk/Sentinel/OpenSearchの既存ダッシュボードを使用
- BOL-CDが作成した削減ルールが適用済み
- High/Criticalアラートのみが表示される

### 方法2: BOL-CD APIから直接取得
```bash
# 削減後のアラートを取得
GET /api/alerts/filtered?severity=high,critical&suppressed=false

# レスポンス
{
  "alerts": [
    {
      "id": "alert-001",
      "severity": "critical",
      "signature": "Privilege Escalation",
      "entity_id": "host-prod-01",
      "timestamp": "2025-09-05T12:00:00Z",
      "suppressed": false,
      "suppression_score": 0.15
    }
  ],
  "total": 42,
  "suppressed_count": 5850
}
```

### 方法3: リアルタイムストリーミング
```python
# WebSocket接続でリアルタイムアラート受信
ws = WebSocket("ws://localhost:8080/ws/alerts")
ws.on_message = lambda msg: 
    if msg['severity'] in ['high', 'critical']:
        send_to_soc_dashboard(msg)
```

### 方法4: 統合ダッシュボード
```javascript
// React UIでフィルタ済みアラート表示
const CriticalAlertsView = () => {
  const [alerts, setAlerts] = useState([]);
  
  useEffect(() => {
    // 30秒ごとに重要アラートを取得
    const interval = setInterval(async () => {
      const response = await fetch('/api/alerts/filtered?suppressed=false');
      const data = await response.json();
      setAlerts(data.alerts.filter(a => a.severity === 'critical'));
    }, 30000);
  }, []);
  
  return (
    <div>
      <h2>対応が必要なアラート（{alerts.length}件）</h2>
      {alerts.map(alert => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
};
```

## 3. 実装例：アラート配信パイプライン

### A. Splunkインテグレーション
```python
# scripts/alert_forwarder.py
import requests
from bolcd.api import get_filtered_alerts

def forward_critical_alerts():
    """削減後のアラートをSOCツールに転送"""
    
    # BOL-CDから重要アラートを取得
    alerts = get_filtered_alerts(
        severity=['high', 'critical'],
        suppressed=False
    )
    
    for alert in alerts:
        # 1. Splunk HECに送信
        splunk_hec_send(alert)
        
        # 2. ServiceNowチケット作成
        if alert['severity'] == 'critical':
            create_incident_ticket(alert)
        
        # 3. Slack通知
        if alert['suppression_score'] < 0.2:  # 特に重要
            send_slack_notification(alert)
        
        # 4. PagerDuty呼び出し
        if is_after_hours() and alert['severity'] == 'critical':
            trigger_pagerduty(alert)
```

### B. 既存SOARとの連携
```yaml
# deploy/integrations/soar-webhook.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bolcd-soar-integration
data:
  webhook_config.json: |
    {
      "endpoints": [
        {
          "name": "Phantom/Splunk SOAR",
          "url": "https://phantom.example.com/webhook",
          "events": ["critical_alert_passed"],
          "headers": {
            "Authorization": "Bearer ${SOAR_TOKEN}"
          }
        },
        {
          "name": "Cortex XSOAR",
          "url": "https://xsoar.example.com/incidents",
          "events": ["high_severity_cluster"],
          "transform": "xsoar_incident_format"
        }
      ]
    }
```

## 4. Web UIでの確認

### ダッシュボードに追加する「アクションが必要なアラート」セクション
```typescript
// web/src/components/ActionableAlerts.tsx
export default function ActionableAlerts() {
  return (
    <div className="bg-red-50 border-l-4 border-red-400 p-4">
      <div className="flex">
        <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            即座の対応が必要
          </h3>
          <div className="mt-2 text-sm text-red-700">
            <ul className="list-disc pl-5 space-y-1">
              <li>Privilege Escalation on prod-db-01</li>
              <li>Ransomware signature detected on fin-app-02</li>
              <li>Data exfiltration attempt from hr-server</li>
            </ul>
          </div>
          <div className="mt-4">
            <button className="text-sm font-medium text-red-800 hover:text-red-600">
              SOCダッシュボードで詳細を見る →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

## 5. 運用フロー

### 日常運用
1. **朝のチェック**: Web UIダッシュボードで削減率と重要アラート確認
2. **SIEM確認**: Splunk/Sentinelで削減ルール適用後のアラート対応
3. **週次レビュー**: 削減されたアラートのサンプリング確認

### アラートエスカレーション
```
Critical Alert → 即座にSOCチームに通知
     ↓
High Alert → 15分以内に初期トリアージ
     ↓
Medium (非削減) → 1時間以内にレビュー
     ↓
Low (削減済み) → 週次でサマリー確認
```

## 6. 設定例

### 環境変数
```bash
# アラート転送先
export BOLCD_ALERT_FORWARD_URL="https://soc-dashboard.example.com/api/alerts"
export BOLCD_CRITICAL_WEBHOOK="https://slack.com/api/webhook/xxx"
export BOLCD_SOAR_ENDPOINT="https://phantom.example.com/rest/container"

# 削減しないパターン（必ず通過させる）
export BOLCD_NEVER_SUPPRESS="severity:critical,signature:ransomware"
```

### 削減ポリシー
```yaml
# config/suppression_policy.yaml
policies:
  - name: "Never suppress critical"
    condition:
      severity: critical
    action: pass
    
  - name: "Always suppress info logs"
    condition:
      severity: info
      signature_pattern: ".*log.*"
    action: suppress
    
  - name: "Pass high with low suppression score"
    condition:
      severity: high
      suppression_score: "< 0.3"
    action: pass
```

## まとめ

**ユーザーは以下の方法で重要アラートを取得します：**

1. **既存SIEM** - BOL-CDが削減ルールを書き戻し、フィルタ済みビュー提供
2. **BOL-CD API** - `/api/alerts/filtered`で直接取得
3. **Web UI** - ダッシュボードの「対応が必要なアラート」セクション
4. **Webhook/WebSocket** - リアルタイム配信
5. **SOAR連携** - 自動的にインシデントチケット作成

**重要：BOL-CDは「削減エンジン」であり、削減後のアラートは必ず何らかの形でSOCチームに届きます。**
