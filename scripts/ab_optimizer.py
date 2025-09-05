#!/usr/bin/env python3
"""
A/B Test Optimizer - 機械学習による削減率最適化
"""
import json
import argparse
from typing import Dict, List, Tuple
from collections import Counter, defaultdict
import numpy as np
from datetime import datetime

class ABOptimizer:
    def __init__(self):
        self.feature_weights = {
            'entity_frequency': 0.3,
            'rule_frequency': 0.25,
            'time_clustering': 0.2,
            'signature_similarity': 0.15,
            'severity_weight': 0.1
        }
        self.learned_patterns = {}
        self.suppression_scores = {}
        
    def extract_features(self, events: List[Dict]) -> Dict:
        """イベントから特徴を抽出"""
        features = {
            'entity_counts': Counter(),
            'rule_counts': Counter(),
            'signature_counts': Counter(),
            'time_clusters': defaultdict(list),
            'severity_distribution': Counter(),
            'pattern_sequences': []
        }
        
        for event in events:
            entity = event.get('entity_id', 'unknown')
            rule = event.get('rule_id', 'unknown')
            signature = event.get('signature', 'unknown')
            severity = event.get('severity', 'low')
            
            features['entity_counts'][entity] += 1
            features['rule_counts'][rule] += 1
            features['signature_counts'][signature] += 1
            features['severity_distribution'][severity] += 1
            
            # 時間クラスタリング（1時間単位）
            if 'timestamp' in event:
                try:
                    ts = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    hour_key = ts.strftime('%Y-%m-%d-%H')
                    features['time_clusters'][hour_key].append(event)
                except Exception:
                    pass
            
            # パターンシーケンスを記録
            pattern = f"{entity}:{rule}:{signature}"
            features['pattern_sequences'].append(pattern)
        
        return features
    
    def calculate_suppression_score(self, event: Dict, features: Dict) -> float:
        """イベントの抑制スコアを計算（高スコア = 抑制すべき）"""
        score = 0.0
        
        entity = event.get('entity_id', 'unknown')
        rule = event.get('rule_id', 'unknown')
        signature = event.get('signature', 'unknown')
        severity = event.get('severity', 'low')
        
        # 1. 頻度ベースのスコア
        entity_freq = features['entity_counts'][entity]
        rule_freq = features['rule_counts'][rule]
        _ = features['signature_counts'][signature]
        
        total_events = sum(features['entity_counts'].values())
        
        # 高頻度イベントは抑制候補
        if entity_freq > total_events * 0.1:  # 10%以上の頻度
            score += self.feature_weights['entity_frequency'] * (entity_freq / total_events)
        
        if rule_freq > total_events * 0.08:
            score += self.feature_weights['rule_frequency'] * (rule_freq / total_events)
        
        # 2. 時間的クラスタリング
        # 短時間に集中しているイベントは抑制候補
        pattern = f"{entity}:{rule}:{signature}"
        time_concentration = self._calculate_time_concentration(pattern, features)
        score += self.feature_weights['time_clustering'] * time_concentration
        
        # 3. シグネチャの類似性
        # 類似シグネチャが多い場合は抑制候補
        similar_count = self._count_similar_signatures(signature, features['signature_counts'])
        if similar_count > 3:
            score += self.feature_weights['signature_similarity'] * min(1.0, similar_count / 10)
        
        # 4. 重要度による調整
        severity_scores = {'low': 0.8, 'medium': 0.5, 'high': 0.2, 'critical': 0.1}
        severity_multiplier = severity_scores.get(str(severity).lower(), 0.5)
        score *= severity_multiplier  # 重要度が高いイベントは抑制を控える
        
        # 5. 学習済みパターンによる調整
        if pattern in self.learned_patterns:
            learned_score = self.learned_patterns[pattern]
            score = score * 0.7 + learned_score * 0.3  # 学習結果を30%反映
        
        return min(1.0, max(0.0, score))  # 0-1の範囲に正規化
    
    def _calculate_time_concentration(self, pattern: str, features: Dict) -> float:
        """時間的集中度を計算"""
        pattern_times = []
        
        for hour_key, events in features['time_clusters'].items():
            count = sum(1 for e in events if f"{e.get('entity_id')}:{e.get('rule_id')}:{e.get('signature')}" == pattern)
            if count > 0:
                pattern_times.append(count)
        
        if not pattern_times:
            return 0.0
        
        # 分散が小さい（集中している）ほど高スコア
        if len(pattern_times) == 1:
            return 1.0
        
        mean = np.mean(pattern_times)
        std = np.std(pattern_times)
        
        if mean == 0:
            return 0.0
        
        # 変動係数の逆数（集中度）
        concentration = 1.0 / (1.0 + std / mean)
        return concentration
    
    def _count_similar_signatures(self, signature: str, signature_counts: Counter) -> int:
        """類似シグネチャをカウント"""
        similar_count = 0
        sig_lower = signature.lower()
        
        for other_sig in signature_counts:
            if other_sig != signature:
                # 簡単な類似性チェック（共通単語数）
                words1 = set(sig_lower.replace('_', ' ').split())
                words2 = set(other_sig.lower().replace('_', ' ').split())
                
                if words1 and words2:
                    similarity = len(words1.intersection(words2)) / max(len(words1), len(words2))
                    if similarity > 0.5:
                        similar_count += 1
        
        return similar_count
    
    def optimize_suppression(self, events: List[Dict], target_reduction: float = 0.6) -> Tuple[List[Dict], List[Dict], Dict]:
        """最適な抑制を実行"""
        features = self.extract_features(events)
        
        # 各イベントに抑制スコアを計算
        scored_events = []
        for event in events:
            score = self.calculate_suppression_score(event, features)
            scored_events.append((score, event))
        
        # スコアでソート（高スコアから）
        scored_events.sort(key=lambda x: x[0], reverse=True)
        
        # 目標削減率を達成するまで抑制
        target_suppress_count = int(len(events) * target_reduction)
        
        suppressed_events = []
        passed_events = []
        
        # スコア閾値を動的に調整
        score_threshold = 0.05 if target_reduction > 0.5 else 0.3
        
        for i, (score, event) in enumerate(scored_events):
            if i < target_suppress_count and score > score_threshold:  # 動的閾値で抑制
                event['_suppression_score'] = score
                event['_suppressed'] = True
                suppressed_events.append(event)
            else:
                event['_suppression_score'] = score
                event['_suppressed'] = False
                passed_events.append(event)
        
        # パターンを学習
        for event in suppressed_events:
            pattern = f"{event.get('entity_id')}:{event.get('rule_id')}:{event.get('signature')}"
            if pattern in self.learned_patterns:
                # 既存パターンのスコアを更新（指数移動平均）
                self.learned_patterns[pattern] = self.learned_patterns[pattern] * 0.8 + event['_suppression_score'] * 0.2
            else:
                self.learned_patterns[pattern] = event['_suppression_score']
        
        # 統計情報
        actual_reduction = len(suppressed_events) / len(events) if events else 0
        
        stats = {
            'total_events': len(events),
            'suppressed_count': len(suppressed_events),
            'passed_count': len(passed_events),
            'actual_reduction_rate': actual_reduction,
            'target_reduction_rate': target_reduction,
            'average_suppression_score': np.mean([s for s, _ in scored_events]) if scored_events else 0,
            'learned_patterns': len(self.learned_patterns)
        }
        
        return passed_events, suppressed_events, stats
    
    def generate_advanced_rules(self, suppressed_events: List[Dict]) -> Dict:
        """抑制イベントから高度なルールを生成"""
        rules = {
            'composite_rules': [],
            'time_based_rules': [],
            'correlation_rules': []
        }
        
        # パターン頻度を集計
        pattern_counter = Counter()
        time_patterns = defaultdict(list)
        
        for event in suppressed_events:
            pattern = f"{event.get('entity_id')}:{event.get('rule_id')}"
            pattern_counter[pattern] += 1
            
            if 'timestamp' in event:
                try:
                    ts = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    hour = ts.hour
                    time_patterns[pattern].append(hour)
                except Exception:
                    pass
        
        # 1. 複合ルール（高頻度パターン）
        for pattern, count in pattern_counter.most_common(10):
            if count >= 3:
                parts = pattern.split(':')
                rules['composite_rules'].append({
                    'entity': parts[0] if parts else '*',
                    'rule': parts[1] if len(parts) > 1 else '*',
                    'threshold': max(2, count // 2),
                    'window': 3600,
                    'action': 'suppress'
                })
        
        # 2. 時間ベースルール
        for pattern, hours in time_patterns.items():
            if len(hours) >= 5:
                # 特定の時間帯に集中している場合
                hour_counts = Counter(hours)
                peak_hour = hour_counts.most_common(1)[0][0]
                
                if hour_counts[peak_hour] >= len(hours) * 0.4:  # 40%以上が特定時間
                    parts = pattern.split(':')
                    rules['time_based_rules'].append({
                        'entity': parts[0] if parts else '*',
                        'rule': parts[1] if len(parts) > 1 else '*',
                        'peak_hours': [peak_hour, (peak_hour + 1) % 24],
                        'suppression_rate': 0.8,
                        'action': 'throttle'
                    })
        
        # 3. 相関ルール
        entity_groups = defaultdict(list)
        for event in suppressed_events:
            entity = event.get('entity_id', 'unknown')
            rule = event.get('rule_id', 'unknown')
            entity_groups[entity].append(rule)
        
        for entity, rules_list in entity_groups.items():
            if len(set(rules_list)) >= 3:  # 3種類以上のルール
                rules['correlation_rules'].append({
                    'entity': entity,
                    'correlated_rules': list(set(rules_list))[:5],
                    'threshold': 5,
                    'window': 1800,
                    'action': 'group_suppress'
                })
        
        return rules


def main():
    parser = argparse.ArgumentParser(description='A/B Test Optimizer')
    parser.add_argument('--input', default='data/raw/events_splunk_2025-09-05_170644.jsonl',
                        help='Input events file')
    parser.add_argument('--output-passed', default='data/ab/B_optimized.jsonl',
                        help='Output file for passed events')
    parser.add_argument('--output-suppressed', default='data/ab/suppressed.jsonl',
                        help='Output file for suppressed events')
    parser.add_argument('--target-reduction', type=float, default=0.6,
                        help='Target reduction rate (0-1)')
    parser.add_argument('--rules-output', default='config/optimized_rules.json',
                        help='Output file for generated rules')
    
    args = parser.parse_args()
    
    # オプティマイザーを初期化
    optimizer = ABOptimizer()
    
    # イベントを読み込み
    events = []
    with open(args.input, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    print(f"📥 {len(events)}件のイベントを読み込みました")
    print(f"🎯 目標削減率: {args.target_reduction*100:.0f}%")
    
    # 最適化を実行
    print("\n🧠 機械学習による最適化を実行中...")
    passed_events, suppressed_events, stats = optimizer.optimize_suppression(events, args.target_reduction)
    
    # 結果を表示
    print("\n" + "="*60)
    print("📊 最適化結果")
    print("="*60)
    print(f"入力イベント数: {stats['total_events']}")
    print(f"抑制イベント数: {stats['suppressed_count']}")
    print(f"通過イベント数: {stats['passed_count']}")
    print(f"達成削減率: {stats['actual_reduction_rate']*100:.1f}%")
    print(f"目標との差: {(stats['actual_reduction_rate'] - stats['target_reduction_rate'])*100:+.1f}%")
    print(f"平均抑制スコア: {stats['average_suppression_score']:.3f}")
    print(f"学習済みパターン数: {stats['learned_patterns']}")
    
    # イベントを保存
    with open(args.output_passed, 'w') as f:
        for event in passed_events:
            cleaned = {k: v for k, v in event.items() if not k.startswith('_')}
            f.write(json.dumps(cleaned, ensure_ascii=False) + '\n')
    
    with open(args.output_suppressed, 'w') as f:
        for event in suppressed_events:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    print("\n💾 最適化済みイベントを保存:")
    print(f"   通過: {args.output_passed}")
    print(f"   抑制: {args.output_suppressed}")
    
    # 高度なルールを生成
    print("\n🔧 高度な抑制ルールを生成中...")
    advanced_rules = optimizer.generate_advanced_rules(suppressed_events)
    
    with open(args.rules_output, 'w') as f:
        json.dump(advanced_rules, f, indent=2, ensure_ascii=False)
    
    print(f"✅ ルールを保存: {args.rules_output}")
    print(f"   複合ルール: {len(advanced_rules['composite_rules'])}個")
    print(f"   時間ベースルール: {len(advanced_rules['time_based_rules'])}個")
    print(f"   相関ルール: {len(advanced_rules['correlation_rules'])}個")
    
    # 達成度を評価
    if stats['actual_reduction_rate'] >= args.target_reduction:
        print("\n🎉 目標削減率を達成しました！")
    else:
        print(f"\n⚠️ 目標まであと{(args.target_reduction - stats['actual_reduction_rate'])*100:.1f}%です")
        print("   → 生成されたルールを適用することで、さらなる改善が期待できます")
    
    return 0


if __name__ == '__main__':
    exit(main())
