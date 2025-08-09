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

## 4) 実装ガイド（完全版） / Full Implementation Guide
Please read and adhere to all the design and testing requirements specified in `docs/design.md` and `docs/test-plan.md` of the `BOL‑CD` repository. Your task is to:

1. Core Implementation: Ensure that the binarization, implication detection, FDR calculation, and transitive reduction modules function exactly as described. Use efficient bitset and popcount operations, implement Rule‑of‑Three for zero counterexamples, and apply the Benjamini–Hochberg procedure for multiple testing control.
2. Missing Components: Review the current repository for missing functionality (e.g., SIEM connectors, segmentation logic, full test suite). Implement Splunk, Microsoft Sentinel, and OpenSearch connectors for ingesting and writing back alerts, including OCSF/ECS normalization. Add segmentation support using `segments.yaml`.
3. Testing: Implement all unit, property-based, integration, and performance tests outlined in `docs/test-plan.md`. Ensure all tests pass under CI and that key performance metrics (EPS, latency, memory) meet the specified thresholds.
4. API and CLI: Finish the FastAPI service per `api/openapi.yaml`, and ensure the CLI can recompute graphs from real data using configurable thresholds and margins.
5. Documentation and Config: Update documentation to reflect implementation details. Maintain a logically complete and self-consistent codebase, with clear comments and mathematical rigor.
6. Verification: After implementation, run the full test suite and produce a report summarizing compliance with the acceptance criteria. Mark any remaining limitations clearly.

Ensure that each step is fully completed before moving to the next, and seek clarification only if a critical ambiguity blocks progress.
