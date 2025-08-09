# データモデルと OCSF/ECS マッピング / Data Schema & Mapping

## 1) Event スキーマ（OCSF/ECS 対応）
| Logical Field | OCSF | ECS | 例 |
|---|---|---|---|
| timestamp | `time` | `@timestamp` | `2025-08-01T12:00:00Z` |
| src_ip | `src_endpoint.ip` | `source.ip` | `10.0.0.1` |
| dst_ip | `dst_endpoint.ip` | `destination.ip` | `10.0.0.2` |
| user | `user.name` | `user.name` | `alice` |
| process | `process.name` | `process.name` | `powershell.exe` |
| action | `activity_id` | `event.action` | `dns_query` |
| technique | custom:`attack.technique_id` | `threat.technique.id` | `T1059` |

## 2) BOL ベクトル（Binary Orthant Label）
- 長さ d のビット列（1/0）。境界不確実は `unknown_mask` で別管理（⊥）。
- 生成規則（英: binarization）：`x_i > a_i + δ → 1`、`x_i < a_i − δ → 0`。

## 3) Edge（含意）
```json
{ "src":"X", "dst":"Y", "n_src1": 12345, "k_counterex": 0, "ci95_upper": 0.00024, "q_value": 0.004 }
```

## 4) ストレージ
- ログ：Parquet（列指向）
- BOL：bit‑packed（Roaring Bitmap 可）
- グラフ：Edge list（Parquet/GraphML）
