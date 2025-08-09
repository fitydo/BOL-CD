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
