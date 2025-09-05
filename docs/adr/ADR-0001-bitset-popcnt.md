# ADR-0001: ビットセット＋`popcnt` による反例計数 / Choose bitset+popcnt

## 状態（Status）
Accepted (v0.1.0)

## 背景
イベント数 N と次元 d が大きく、(X,Y) ペア数 d(d-1) を高速に裁く必要。

## 決定（Decision）
- `S_i` をビットパック（64/128bit）し、`k_{i\bar j} = popcnt(S_i & ~S_j)` で計算。
- AVX2/AVX‑512／RoaringBitmap を段階的に採用。

## 代替案（Alternatives）
- 行列演算（dense/CSR）：メモリ負荷が高い。

## 影響（Consequences）
- CPU ベクトル化でスループットを稼げる。実装は低レベル化。
