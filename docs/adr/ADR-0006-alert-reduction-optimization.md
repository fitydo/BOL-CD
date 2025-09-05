# ADR-0006: アラート削減率最適化の実装

## Status
Accepted

## Context
アラート疲労対策として、A/Bテストによる削減率測定と最適化が必要。当初の実装では削減率が0%に留まっていたが、原因分析により以下の問題が判明：
- スコア閾値のロジックバグ（閾値が高すぎて抑制が発生しない）
- High/Criticalアラートの誤抑制リスク
- 重要度を考慮しない一律の抑制

## Decision
以下の方針で最適化システムを実装：

1. **動的閾値設定**: 分位点ベースで目標削減率に応じた閾値を自動決定
2. **Severity別処理**: High/Criticalは厳格に保護、Low/Mediumを積極的に削減
3. **誤抑制ゲート**: High/Critical誤抑制率<10%を必須条件として設定

## Implementation

### 修正前の問題コード
```python
# バグ：閾値が逆
score_threshold = 0.05 if target_reduction > 0.5 else 0.3
```

### 修正後の実装
```python
# スコア分布から適切な閾値を決定
if target_suppress_count < len(scores_only):
    score_threshold = sorted(scores_only, reverse=True)[min(target_suppress_count, len(scores_only)-1)]
    score_threshold = max(0.01, score_threshold * 0.9)

# Severity別処理
if severity in ['critical', 'high']:
    # High/Criticalは厳しい制限
    if score > max(score_threshold * 2, cap_critical if severity == 'critical' else cap_high):
        suppress()
else:
    # Low/Mediumは通常閾値
    if score > score_threshold:
        suppress()
```

## Results
全600件データでの検証結果：
- **削減率**: 58.5%（目標50%を達成）
- **誤抑制率**: 0.0%（High/Critical完全保護）
- **重み付き削減率**: 78.5%
- **抑制内訳**: Low 36件、Medium 73件、High 0件、Critical 0件

## Consequences

### Positive
- アラート疲労の大幅改善（58.5%削減）
- 重要アラートの完全保護（誤抑制0%）
- 再現性のある削減（固定パラメータ、決定的動作）

### Negative
- Low/Mediumアラートの一部が見逃される可能性
- 定期的なルール更新が必要

### Mitigation
- 週次でのルール自動更新
- 削減されたアラートのサマリーレポート生成
- 誤抑制率の継続的モニタリング

## References
- scripts/ab_optimizer.py: 最適化実装
- scripts/ab_validate.py: 検証ハーネス
- reports/ab_validation_extended.json: 検証結果
