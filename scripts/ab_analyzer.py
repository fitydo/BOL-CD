#!/usr/bin/env python3
"""
A/B Test Analyzer - データ解析と削減率向上のための分析ツール
"""
import json
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, List
from datetime import datetime

class ABAnalyzer:
    def __init__(self, data_dir: str = "data/ab", reports_dir: str = "reports"):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        self.analysis_results = {}
        
    def load_events(self, file_path: str) -> List[Dict]:
        """イベントデータを読み込む"""
        events = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        return events
    
    def analyze_patterns(self, events_a: List[Dict], events_b: List[Dict]) -> Dict:
        """イベントパターンを分析"""
        # A群とB群の特徴を抽出
        patterns_a = self._extract_patterns(events_a)
        patterns_b = self._extract_patterns(events_b)
        
        # 削減されたパターンを特定
        reduced_patterns = []
        for pattern, count_a in patterns_a.items():
            count_b = patterns_b.get(pattern, 0)
            if count_b < count_a:
                reduction_rate = (count_a - count_b) / count_a if count_a > 0 else 0
                reduced_patterns.append({
                    'pattern': pattern,
                    'count_a': count_a,
                    'count_b': count_b,
                    'reduction_rate': reduction_rate,
                    'impact': count_a - count_b  # 削減数
                })
        
        # 削減率が低いパターンを特定（改善余地あり）
        low_reduction_patterns = [
            p for p in reduced_patterns 
            if p['reduction_rate'] < 0.3 and p['count_a'] > 5
        ]
        
        # B群にのみ存在するパターン（リグレッション）
        new_in_b = []
        for pattern, count_b in patterns_b.items():
            if pattern not in patterns_a and count_b > 0:
                new_in_b.append({
                    'pattern': pattern,
                    'count': count_b,
                    'severity': self._estimate_severity(pattern)
                })
        
        return {
            'total_patterns_a': len(patterns_a),
            'total_patterns_b': len(patterns_b),
            'reduced_patterns': sorted(reduced_patterns, key=lambda x: x['impact'], reverse=True)[:20],
            'low_reduction_patterns': sorted(low_reduction_patterns, key=lambda x: x['count_a'], reverse=True)[:10],
            'new_in_b': sorted(new_in_b, key=lambda x: x['count'], reverse=True)[:10],
            'overall_reduction': self._calculate_overall_reduction(events_a, events_b)
        }
    
    def _extract_patterns(self, events: List[Dict]) -> Dict[str, int]:
        """イベントからパターンを抽出"""
        patterns = Counter()
        
        for event in events:
            # 複数の特徴を組み合わせたパターンを生成
            entity = event.get('entity_id', 'unknown')
            rule = event.get('rule_id', 'unknown')
            signature = event.get('signature', 'unknown')
            severity = event.get('severity', 'unknown')
            
            # パターン1: エンティティ + ルール
            patterns[f"{entity}:{rule}"] += 1
            
            # パターン2: シグネチャ + 重要度
            patterns[f"{signature}:{severity}"] += 1
            
            # パターン3: エンティティ + シグネチャ
            patterns[f"{entity}:{signature}"] += 1
            
        return dict(patterns)
    
    def _estimate_severity(self, pattern: str) -> str:
        """パターンの重要度を推定"""
        critical_keywords = ['critical', 'high', 'escalation', 'malware', 'exfiltration']
        medium_keywords = ['medium', 'unauthorized', 'failed', 'injection']
        
        pattern_lower = pattern.lower()
        for keyword in critical_keywords:
            if keyword in pattern_lower:
                return 'critical'
        for keyword in medium_keywords:
            if keyword in pattern_lower:
                return 'medium'
        return 'low'
    
    def _calculate_overall_reduction(self, events_a: List[Dict], events_b: List[Dict]) -> float:
        """全体の削減率を計算"""
        count_a = len(events_a)
        count_b = len(events_b)
        if count_a == 0:
            return 0.0
        return (count_a - count_b) / count_a
    
    def suggest_optimizations(self, analysis: Dict) -> List[Dict]:
        """最適化の提案を生成"""
        suggestions = []
        
        # 1. 低削減率パターンの改善提案
        for pattern in analysis['low_reduction_patterns'][:5]:
            suggestions.append({
                'type': 'threshold_adjustment',
                'pattern': pattern['pattern'],
                'current_reduction': pattern['reduction_rate'],
                'target_reduction': 0.6,
                'action': f"閾値を調整: {pattern['pattern']} の重複判定基準を緩和",
                'expected_impact': pattern['count_a'] * 0.3  # 30%追加削減を期待
            })
        
        # 2. 高頻度パターンの抑制ルール追加
        for pattern in analysis['reduced_patterns'][:5]:
            if pattern['reduction_rate'] < 0.5:
                suggestions.append({
                    'type': 'suppression_rule',
                    'pattern': pattern['pattern'],
                    'current_count': pattern['count_b'],
                    'action': f"抑制ルール追加: {pattern['pattern']} の連続発生を抑制",
                    'expected_impact': pattern['count_b'] * 0.5
                })
        
        # 3. リグレッションの対処
        for pattern in analysis['new_in_b'][:3]:
            if pattern['severity'] != 'critical':
                suggestions.append({
                    'type': 'false_positive_filter',
                    'pattern': pattern['pattern'],
                    'action': f"誤検知フィルタ: {pattern['pattern']} を除外候補に追加",
                    'expected_impact': pattern['count']
                })
        
        # 期待される改善効果を計算
        total_expected_reduction = sum(s.get('expected_impact', 0) for s in suggestions)
        current_total = len(analysis.get('events_a', [])) if 'events_a' in analysis else 1000
        expected_reduction_rate = analysis['overall_reduction'] + (total_expected_reduction / current_total)
        
        return {
            'suggestions': suggestions,
            'current_reduction_rate': analysis['overall_reduction'],
            'expected_reduction_rate': min(expected_reduction_rate, 0.8),  # 最大80%
            'total_expected_impact': total_expected_reduction
        }
    
    def generate_tuning_config(self, suggestions: Dict) -> Dict:
        """チューニング設定を生成"""
        config = {
            'timestamp': datetime.now().isoformat(),
            'target_reduction_rate': 0.6,
            'threshold_adjustments': {},
            'suppression_rules': [],
            'false_positive_filters': []
        }
        
        for suggestion in suggestions['suggestions']:
            if suggestion['type'] == 'threshold_adjustment':
                # パターンから閾値調整対象を抽出
                parts = suggestion['pattern'].split(':')
                if len(parts) >= 2:
                    config['threshold_adjustments'][parts[0]] = {
                        'rule': parts[1],
                        'multiplier': 0.7,  # 閾値を30%緩和
                        'min_interval': 300  # 5分間の最小間隔
                    }
            
            elif suggestion['type'] == 'suppression_rule':
                parts = suggestion['pattern'].split(':')
                config['suppression_rules'].append({
                    'pattern': suggestion['pattern'],
                    'entity': parts[0] if parts else '*',
                    'rule': parts[1] if len(parts) > 1 else '*',
                    'window': 3600,  # 1時間のウィンドウ
                    'threshold': 3,  # 3回以上で抑制
                    'suppress_duration': 1800  # 30分間抑制
                })
            
            elif suggestion['type'] == 'false_positive_filter':
                config['false_positive_filters'].append({
                    'pattern': suggestion['pattern'],
                    'confidence': 0.8,
                    'auto_suppress': True
                })
        
        return config
    
    def run_analysis(self) -> Dict:
        """完全な分析を実行"""
        # A/Bデータを読み込み
        a_file = self.data_dir / "A.jsonl"
        b_file = self.data_dir / "B.jsonl"
        
        if not a_file.exists() or not b_file.exists():
            return {'error': 'A/B data files not found'}
        
        events_a = self.load_events(a_file)
        events_b = self.load_events(b_file)
        
        # パターン分析
        analysis = self.analyze_patterns(events_a, events_b)
        analysis['events_a'] = events_a  # 後の計算用
        
        # 最適化提案
        optimizations = self.suggest_optimizations(analysis)
        
        # チューニング設定生成
        tuning_config = self.generate_tuning_config(optimizations)
        
        return {
            'analysis': analysis,
            'optimizations': optimizations,
            'tuning_config': tuning_config,
            'summary': {
                'current_reduction': f"{analysis['overall_reduction']*100:.1f}%",
                'expected_reduction': f"{optimizations['expected_reduction_rate']*100:.1f}%",
                'improvement': f"{(optimizations['expected_reduction_rate'] - analysis['overall_reduction'])*100:.1f}%",
                'suggestions_count': len(optimizations['suggestions'])
            }
        }


def main():
    parser = argparse.ArgumentParser(description='A/B Test Analyzer')
    parser.add_argument('--data-dir', default='data/ab', help='A/B data directory')
    parser.add_argument('--reports-dir', default='reports', help='Reports directory')
    parser.add_argument('--output', help='Output file for analysis results')
    
    args = parser.parse_args()
    
    analyzer = ABAnalyzer(args.data_dir, args.reports_dir)
    results = analyzer.run_analysis()
    
    # 結果を表示
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return 1
    
    print("\n" + "="*60)
    print("📊 A/B削減率分析レポート")
    print("="*60)
    
    summary = results['summary']
    print(f"\n現在の削減率: {summary['current_reduction']}")
    print(f"期待削減率: {summary['expected_reduction']}")
    print(f"改善幅: {summary['improvement']}")
    print(f"提案数: {summary['suggestions_count']}")
    
    print("\n🎯 改善提案TOP5:")
    for i, suggestion in enumerate(results['optimizations']['suggestions'][:5], 1):
        print(f"\n{i}. {suggestion['type']}")
        print(f"   対象: {suggestion['pattern']}")
        print(f"   アクション: {suggestion['action']}")
        print(f"   期待効果: {suggestion.get('expected_impact', 0):.0f}件削減")
    
    # 結果を保存
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = Path(args.reports_dir) / f"ab_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 詳細分析結果を保存: {output_file}")
    
    # チューニング設定を保存
    tuning_file = Path("config") / "tuning_config.json"
    tuning_file.parent.mkdir(exist_ok=True)
    with open(tuning_file, 'w') as f:
        json.dump(results['tuning_config'], f, indent=2, ensure_ascii=False)
    
    print(f"⚙️ チューニング設定を保存: {tuning_file}")
    
    return 0


if __name__ == '__main__':
    exit(main())
