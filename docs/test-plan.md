# BOL‑CD for SOC 試験計画書 / Test & Validation Plan

## 0. 目的（Purpose）
設計仕様書に定義された機能/性能/説明可能性を検証し、**アラート削減・重複削減・誤検出削減**の効果を定量的に示す。

## 1. 試験範囲（Scope）
- 二値化、反例計数、統計判定（Rule‑of‑Three, 片側二項, BH）
- DAG 構築・推移簡約
- SIEM 連携（書き戻し）
- 性能（EPS/レイテンシ/メモリ）
- 可観測性/監査性

## 2. 試験環境（Environment）
- 単一ノード：16 vCPU / 64 GB RAM、NVMe SSD
- OS：Linux (x86_64)；AVX2/AVX‑512 利用可
- データ：合成・公開データ・実運用ログの 3 種
- 再現性：固定乱数 seed、Docker Compose による固定化

## 3. データセット（Datasets）
### 3.1 合成（Synthetic）
- 変数 d=100、レコード N=10^7（段階化：10^6 〜 10^7）
- 既知の連鎖：A→B→C を 40%、交絡：U→A, U→C を 10% 混入
- ノイズ：誤測定率 0.2–2.0%（\(\delta\) 調整でカバー）

### 3.2 公開（Public）
- 代表的 IDS/ネットワークログから特徴量を抽出し二値化
- 目的：ベースライン比較・汎化確認

### 3.3 実運用（Operational; PoC）
- 対象 SIEM から read‑only で取得、PII は匿名化/マスキング

## 4. テスト設計（Test Design）
### 4.1 単体（Unit）
- U1: **popcnt**・ビット論理の正しさ（ランダム/境界）
- U2: 二値化（\(\delta\) マージン；⊥の扱い）
- U3: Rule‑of‑Three 実装（0 反例時の上限 = 3/n）
- U4: 片側二項の p 値、**BH** による q 値の単調性
- U5: 推移簡約：各辺 (u,v) を除外時に reachable(u,v) なら削除

### 4.2 性質（Property‑based）
- P1: 反例が 0 → 含意は採択（q≤q_max かつ 3/n≤ε）
- P2: A→B, B→C が採択かつ A→C も採択された場合、最終グラフで A→C は存在しない（最小連鎖）
- P3: ⊥（unknown）を増やすとエッジ数は**非増加**

### 4.3 結合（Integration）
- I1: OCSF/ECS マッピング→二値化→辺→最小連鎖までの E2E
- I2: SIEM への書き戻し（SPL/KQL/Sigma）の構文整合性
- I3: セグメント別（資産階層/時間帯）でグラフが分離されること

### 4.4 性能（Performance）
- Perf1: EPS スケール：10k, 50k, 100k EPS で p95 レイテンシを測定
- Perf2: メモリ：d=100 で 1 レコード ≈16B を概ね満たす
- Perf3: スケールアウト：ノード 1→4 でスループット ≧ 3.2×

### 4.5 ポスト解析（Explainability）
- X1: 各辺に (n, k, 3/n, q) が付与されること
- X2: 抑制された A→C の注釈に “via B” が残ること

### 4.6 運用（Operational）
- O1: しきい変更（thresholds.yaml）反映のホットリロード
- O2: 監査ログに、辺の追加/削除/しきい変更が記録されること

## 5. 受け入れ基準（Acceptance Criteria）
- A1: **Alerts −25% 以上 / Dup −30% 以上 / FPR 相対 −20% 以上**
- A2: p95 レイテンシ **≤ 100ms**（50k EPS 条件）
- A3: すべての単体/結合テスト **合格率 100%**
- A4: 最小連鎖の**正当性**（到達可能性保存）が形式テストで確認できる

## 6. ベンチマーク手順（Benchmark Procedure）
1. 合成データ生成（seed 固定）→ 10^6 → 10^7 に増加
2. しきい \(a_i\)/\(\delta\)/q/ε を設定
3. ランでメトリクス収集（EPS、レイテンシ、エッジ数、削除率）
4. SIEM 連携で**事前/事後**のアラート件数・誤検知率を比較（A/B）
5. レポート自動生成（表/グラフ/差分）

## 7. リグレッション & リリース（Regression & Release）
- テストは CI（GitHub Actions 等）で PR ごと自動実行
- 主要 KPI に**しきい**（ガードレール）を設定し悪化を fail にする

## 8. トレーサビリティ（Traceability）
| 要求ID | テストID |
|---|---|
| FR1 | I1 |
| FR2 | U2, I1 |
| FR3 | U1 |
| FR4 | U3, U4 |
| FR5 | U5, P2 |
| FR6 | I2 |
| FR7 | X1, X2 |
| NFR (EPS/Latency) | Perf1–3 |

## 9. リスクと軽減策（Risks & Mitigations）
- 非単調関係の見落とし → **k‑ary 符号化**とセグメント分割で緩和
- データ欠損・⊥ の増加 → サンプルサイズを UI で可視化し警告
- しきい設計ミス → 変更履歴の監査・ロールバック

## 10. 実行方法（You’re on your own）
- `make test`：単体/結合/性質テスト
- `make bench EPS=50000`：性能ベンチ（p95 レイテンシ測定）
- `make abtest`：SIEM 連携の A/B 試験を自動化
- すべての結果は `/reports/YYYY‑MM‑DD/` に保存（CSV/MD）
