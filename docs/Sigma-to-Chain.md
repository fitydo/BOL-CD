# Sigma → Chain 変換仕様 / Sigma-to-Chain Conversion

## 0) 目的
Sigma 検知を**因果連鎖**の構成要素へ変換し、**A→B→C** の**最小連鎖**を自動生成する。

## 1) ルール分解（Rule Decomposition）
- Sigma ルール R を `{condition, fields, timeframe}` に正規化。
- `condition` を満たすイベント集合を **基礎事象** \(E_R\) として定義。

## 2) 二値化（Binarization）
- 既知の指標に対ししきい \(a_i\) を適用、`S_i` を生成。
- Sigma が**存在判定**系の場合は `S_R := 1{E_R>0 within Δt}` とする（窓内発生で 1）。

## 3) 連鎖推定
- 2 つの事象 \(X,Y\) について、反例 \((X=1,Y=0)\) を `popcnt` で数える。
- 0 のとき **Rule‑of‑Three** で上限 \(3/n_{X*}\) を併記、>0 は片側二項→ **BH（FDR）**。

## 4) 推移簡約（Transitive Reduction）
- A→B, B→C が確定し、A→C も採択された場合は A→C を**削除**。
- UI には “via B” として**間接因果**を注記。

## 5) 例（擬似）
- Sigma: `selection: EventID=4688 and process_name: powershell.exe`
- 変換: `X = 1{ps_exec>0 within 5m}`
- 別ルール `Y = 1{network_beacon>0 within 10m}`, `Z = 1{credential_dump>0 within 20m}`
- 学習結果: `X→Y`, `Y→Z`（`X→Z` は**推移簡約**で削除）
