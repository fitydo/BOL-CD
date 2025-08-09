# PoC プレイブック / Proof-of-Concept Playbook

## 1) 目的
- 既存 SIEM に**寄生（read‑only）**して**削減効果**と**遅延**を測る。

## 2) 手順
1. データ接続（read-only）：Sysmon/Zeek/Suricata/クラウドログ
2. 1 週間の事前データで初期学習（q=0.01, ε=0.005, δ=2–5%）
3. 2 週間の A/B：
   - A（従来）：そのまま
   - B（本製品）：最小連鎖で抑制→ダッシュボード
4. 指標を比較：Alerts/Duplicate/FPR/Latency
5. レポート出力：削減率、(n,k,3/n,q) の分布、代表連鎖の可視化

## 3) 判定基準
- Alerts −25% / Duplicate −30% / FPR −20% / p95 ≤ 100ms

## 4) 成功後のアクション（You’re on your own）
- SIEM 書き戻しを有効化、抑制ポリシーを本番適用。
