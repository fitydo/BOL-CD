# Cursor 用プロンプト集 / Prompts for Cursor

## 1) Core 実装
「`docs/ADR-0001-bitset-popcnt.md` と `docs/design.md` に従い、
`src/core/implication.py` を実装。bitset を使い `k_{i\bar j} = popcnt(S_i & ~S_j)`。
0 反例のときは Rule‑of‑Three を計算し、>0 のときは片側二項 p 値を返して。
テストは `docs/test-plan.md` の U1–U4 を満たす PyTest を生成。」

## 2) 推移簡約
「`docs/ADR-0003-transitive-reduction.md` に従い、
`src/core/transitive_reduction.py` を実装。各辺 (u,v) を外して reachable(u,v) を
bitset BFS で判定、到達可能なら削除。P2 を満たすテストも作成。」

## 3) 連携
「`docs/Sigma-to-Chain.md` と `docs/Data-Schema-and-Mapping.md` を参照し、
Sigma ルールから `X,Y,Z` を抽出する変換器を `src/connectors/sigma.py` に実装。
3 つの SIEM への書き戻しモジュールのインタフェース定義を作れ。」
