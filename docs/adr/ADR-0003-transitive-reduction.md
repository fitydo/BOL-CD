# ADR-0003: 推移簡約（Transitive Reduction）を適用

## 決定
- A→B, B→C があるとき A→C を削除。間接因果は注釈で保持。

## 理由
- 最小連鎖（minimal explanation set）により認知負荷を下げ、重複調査を削減。

## 影響
- 到達可能性を壊さないことを**形式テスト**で保証する。
