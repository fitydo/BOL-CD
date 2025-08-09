# BOL‑CD for SOC（サイバーセキュリティ）設計仕様書 / System Design Specification

## 0. 概要（Overview）
**BOL‑CD（Binary‑Orthant Causal Discovery：二進数オーソント符号＋反例ゼロ判定＋推移簡約）** を核に、SIEM/XDR のアラートを**重複なく、短い因果連鎖（minimal chains）**で提示し、**誤検出（False Positive, FP）と重複調査**を削減する中間レイヤ製品の設計を定義する。

- 対象：Splunk / Microsoft Sentinel / OpenSearch Security Analytics などの SIEM/XDR（添付＝augmentation layer）
- 目的：**アラート総量 −25%以上、重複 −30%以上、FPR 相対 −20%以上、p95 レイテンシ +100ms 以内**
- 非目的：SIEM の完全置換、UEBA/LLM 助手の再実装

## 1. 用語（Terminology）
- **二値化（binarization；not available in Japanese, but…）**：連続/カテゴリ値を 0/1（＋未知 ⊥）に写像
- **反例（counterexample）**：含意 \(X\to Y\) における \((X{=}1, Y{=}0)\)
- **推移簡約（transitive reduction）**：DAG の到達可能性を保ったまま冗長辺（A→C など）を削除

## 2. 要求（Requirements）
### 2.1 機能要件（FR）
- FR1: イベントを OCSF/ECS に正規化して受入れる
- FR2: しきい \(a_i\) とマージン \(\delta\) で二値化（1/0/⊥）
- FR3: 反例数 \(k_{i\bar{j}}\) を **bitset + popcnt** で算出
- FR4: **Rule‑of‑Three**（0 反例時 95% 上限 \(3/n_{i*}\)）と片側二項検定＋**BH（FDR）**で辺採択
- FR5: DAG 構築と**推移簡約**で最小連鎖を生成
- FR6: SIEMへ**ルール/タグ**書き戻し（抑制・連鎖可視化）
- FR7: 各辺に「支持数 \(n_{i*}\)・反例 \(k\)・95% 上限・q 値」を付与（説明可能性）

### 2.2 非機能要件（NFR）
- NFR1: スループット：**≥ 50k EPS/ノード**
- NFR2: レイテンシ：**p95 ≤ 100ms**（前段/後段どちらでも）
- NFR3: メモリ：**d=100** のとき **16B/レコード**（ビットパック）を目安
- NFR4: 可観測性：メトリクス（EPS, popcnt/sec, FDR しきい通過率）とトレース
- NFR5: セキュリティ：RBAC、監査ログ、保存時/転送時暗号化

## 3. アーキテクチャ（Architecture）
```
[Ingestors]
  ├─ Sysmon / Zeek / Suricata / Cloud Logs
  ├─ Normalizer: OCSF / ECS
  ├─ BOL Encoder (0/1/⊥ with margin δ)
  ├─ Implication Engine (bitset + popcnt)
  ├─ FDR Controller (BH), Rule‑of‑Three Annotator
  ├─ DAG Builder → Transitive Reduction
  ├─ Alert Graph Store (edges with stats)
  └─ SIEM Connectors (write-back: SPL/KQL/Sigma)
```

### 3.1 データモデル（Data Model）
- **Event**：`{ts, host, user, process, action, metric[], tags[]}`（OCSF/ECS フィールド準拠）
- **BOL Vector**：長さ d のビット列（unknown ⊥ は別ビットまたはマスク）
- **Edge**：`{src, dst, n_src1, k_counterex, ci95_upper=3/n_src1, p, q}`
- **Graph**：DAG（到達可能性を維持）

## 4. アルゴリズム（Algorithms）
### 4.1 二値化（Binarization）
\[
S_i(x)=\begin{cases}
1 & (x_i>a_i+\delta)\\
0 & (x_i<a_i-\delta)\\
\bot & (|x_i-a_i|\le \delta)
\end{cases}
\]
- \(\delta\)：境界ノイズ用マージン（3値/Kleene 的 unknown）
- 実装：ビットパック（1/0）＋ unknown マスク

### 4.2 含意判定（Implication Test）
- 反例数：\(k_{i\bar{j}}=\mathrm{popcnt}(S_i \land \lnot S_j)\)
- 0 反例時：**Rule‑of‑Three** → \(\Pr(Y=0|X=1)\le 3/n_{i*}\)（95%）
- >0 反例時：片側二項検定で p 値、**BH** で q 値に調整

### 4.3 グラフ構築と推移簡約（Graph & Transitive Reduction）
- 初期辺集合 \(E=\{i\to j | q\le q_{max} \land (3/n_{i*}\le \epsilon)\}\)
- **Transitive Reduction**：
  - 方法A：各辺 \((u,v)\) について、辺を一時に外し **reachable(u,v)** を BFS/bitset で判定。到達可能なら削除。
  - 方法B：**Transitive Closure**（ワーシャル/ビット行列）から差分。
- 出力：**最小連鎖**（minimal explanation set）

## 5. 設定（Configuration）
- `thresholds`: 各指標の \(a_i\)
- `margin_delta`: \(\delta\)（例：分位点幅の 2–5%）
- `fdr_q`: 例 0.01
- `epsilon`: Rule‑of‑Three 閾（例 0.005）
- `segment_by`: 層別キー（例：asset.tier, time_of_day）
- `connectors`: Splunk/Sentinel/OpenSearch の接続/書き戻し設定

## 6. スケーラビリティ（Scalability）
- 計算量：\(\tilde O\big((N/64)\cdot d(d-1)\big)\)
- シャーディング：Z‑order の粗キー or ハッシュで水平分割
- ハードウェア最適化：AVX2/AVX‑512 の `popcnt`、GPU/FPGA も選択可

## 7. セキュリティ/プライバシ（Security & Privacy）
- データ最小化（binarization 後は原値を保持しないオプション）
- 監査ログ、KMS による鍵管理、PII/秘匿のためのトークナイズ

## 8. 可観測性（Observability）
- メトリクス：EPS、q≤q_max 辺率、削除された推移辺率、p95 レイテンシ
- ログ：各辺の更新履歴としきい変更差分
- トレース：エッジ生成→削除までのスパン

## 9. API（Interface）
- `POST /encode`：イベント→BOL ベクトル
- `POST /edges/recompute`：再学習（FDR/しきい反映）
- `GET /graph`：最小連鎖グラフ（JSON/GraphML）
- `POST /siem/writeback`：連鎖ルールの生成・配布（SPL/KQL/Sigma）

## 10. UI（UX）
- 連鎖可視化：A→B→C を 1–3 ステップで提示、各辺に（n, k, 3/n, q）バッジ
- 抑制ポリシー：A→C を “間接（via B）” として注釈残し、抑制/解放を選択

## 11. 制約・限界（Limitations）
- 非単調関係には弱い → **多段階（k‑ary）符号化**で一部緩和
- 交絡は残る → **層別**・**時間遅延**・**介入**を別モジュールで補完
- 0 反例 ≠ 真 0 → **Rule‑of‑Three の上限**を必ず表示

## 12. リポジトリ構成（Repository Layout）
```
/docs
  ├─ design.md (本書)
  └─ test-plan.md
/src
  ├─ core/ (binarize, implication, fdr, tr)
  ├─ connectors/ (splunk, sentinel, opensearch)
  ├─ ui/ (graph, reports)
  └─ cli/
/configs
  ├─ thresholds.yaml
  └─ segments.yaml
```

## 13. 受け入れ基準（Acceptance）
- KPI を達成：Alerts −25%/Dup −30%/FPR −20%/p95 ≤100ms
- ドキュメント：設計・試験・運用 Runbook・SIEM 連携手順が揃う
- セキュリティ：RBAC・監査・暗号化の有効化
