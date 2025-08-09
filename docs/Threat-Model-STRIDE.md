# セキュリティ脅威モデル（STRIDE） / Threat Model

| 区分 | 具体例 | 影響 | 緩和策 |
|---|---|---|---|
| Spoofing | コネクタの偽装イベント投入 | 誤学習・誤抑制 | API 認証、SIEM 側の署名検証、source allowlist |
| Tampering | しきい/設定の改ざん | 誤検知・検知漏れ | RBAC、変更履歴の署名、2人承認 |
| Repudiation | 操作否認 | 監査困難 | 監査ログの WORM 化、時刻署名 |
| Information Disclosure | PII 混入 | コンプライアンス違反 | PII マスク、データ最小化（binarization後破棄） |
| Denial of Service | 高 EPS による遅延 | SLO 未達 | 前段レート制限、水平スケール、優先度制御 |
| Elevation of Privilege | 権限昇格 | 全権奪取 | 最小権限、Secrets 分離、CICD 署名検証 |
