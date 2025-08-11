# SLO/SLI 定義 / Service Level Objectives

## SLI（測るもの）
- **EPS**：1 秒あたりイベント件数
- **p95 レイテンシ**：前/後段の処理遅延
- **Edges Kept/Pruned**：採択辺と推移簡約で削除された辺の比
- **Alerts Reduction / Duplicate Reduction / FPR**：A/B で事前/事後を比較

## SLO（目標値）
- p95 レイテンシ ≤ **100ms**
- EPS/ノード ≥ **50k**
- Alerts Reduction ≥ **25%**
- Duplicate Reduction ≥ **30%**

## エラーバジェット（Error Budget）
- p95 違反時間が月 5% を超えた場合、新機能停止→性能改善スプリントへ転換。

## CI との整合（Notes）
- GitHub Actions ではランナー性能のばらつきが大きいため、CI での `perf-guard` は緩い閾値（EPS ≥ 7k, p95 ≤ 30s）と回帰判定（ベースライン比）で検知。
- 本番/検証環境の SLO は上記（p95 ≤ 100ms, EPS ≥ 50k/ノード）を適用。ナイトリー/専用ランナーで厳密チェック。
