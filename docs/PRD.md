# PRD: ChainLite for SOC（BOL‑CD搭載アラート重複削減） / Product Requirements Document

## 0. 背景（Background）
SOC はアラート疲れ（alert fatigue）と重複調査が慢性化。SIEM 本体を置換せず、**添付（augmentation layer）**として**反例ゼロ含意＋推移簡約**で**最小連鎖**を提示する。

## 1. 目的（Goals）
- **アラート総量 −25% 以上**
- **重複インシデント −30% 以上**
- **FPR（False Positive Rate）相対 −20% 以上**
- **p95 レイテンシ +100ms 以内（前/後段いずれでも）**

## 2. ペルソナ（Personas）
- L1 アナリスト（SOC Analyst L1）：大量アラートの一次トリアージ
- L2 アナリスト：原因追跡、横展開の判断
- CISO/マネージャ：SLA/SLO 達成の責任者

## 3. ユースケース（User Stories）
- US1: 「同一インシデントに属するアラートを 1 本の**短い因果連鎖**で表示してほしい」
- US2: 「**A→B→C** があるときの **A→C** は“間接（via B）”として自動抑制してほしい」
- US3: 「各連鎖の**根拠**（n, k, 3/n, q）を監査用に出力してほしい」

## 4. スコープ（In） / 非スコープ（Out）
- In: OCSF/ECS 正規化、二値化、含意抽出、FDR、推移簡約、SIEM 書き戻し
- Out: UEBA の再実装、LLM 支援、フル SOAR

## 5. 指標（Metrics）
- Core: Alerts Reduction / Duplicate Reduction / FPR / p95 Latency / EPS
- Explainability: 辺ごとの (n, k, 3/n, q) 出力率 100%

CI 注記: PR CI では緩い性能閾と回帰チェックを適用（`perf-guard`）。本番 SLO は SLO/SLI を参照。

## 6. 非機能（NFR）
- スループット ≥ 50k EPS/ノード、水平スケール可
- セキュリティ：RBAC/監査ログ/暗号化、PII 最小化

## 7. リスクと対策（Risks & Mitigations）
- 非単調関係 → **k‑ary** 符号化、セグメント分割
- データ標準の変動 → OCSF/ECS の定期追随
- 誤しきい設定 → 変更履歴/ロールバック、AB テスト運用

## 8. リリース計画（Release Plan）
- M0: MVP（単一 SIEM + OCSF/ECS + 最小 UI）
- M1: 3 SIEM 連携、ATT&CK マッピング、STIX/TAXII
- M2: MSSP 連携 & SaaS
