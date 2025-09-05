#!/usr/bin/env python3
"""
A/B Test Tuner - 抑制ルールと閾値の自動チューニング
"""
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib

class ABTuner:
    def __init__(self, config_file: str = "config/tuning_config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.suppression_cache = defaultdict(deque)
        self.metrics = {
            'events_processed': 0,
            'events_suppressed': 0,
            'events_passed': 0
        }
    
    def _load_config(self) -> Dict:
        """チューニング設定を読み込む"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            'threshold_adjustments': {},
            'suppression_rules': [],
            'false_positive_filters': []
        }
    
    def apply_threshold_adjustments(self, event: Dict) -> Dict:
        """閾値調整を適用"""
        entity = event.get('entity_id', '')
        rule = event.get('rule_id', '')
        
        # 該当する閾値調整を検索
        for key, adjustment in self.config['threshold_adjustments'].items():
            if key in entity or adjustment['rule'] in rule:
                # メトリック値を調整（閾値を緩和）
                if 'metric_value' in event:
                    event['metric_value'] *= adjustment.get('multiplier', 1.0)
                    event['_threshold_adjusted'] = True
                
                # 時間間隔チェック
                if 'min_interval' in adjustment:
                    event['_min_interval'] = adjustment['min_interval']
        
        return event
    
    def apply_suppression_rules(self, event: Dict) -> bool:
        """抑制ルールを適用（True=抑制、False=通過）"""
        entity = event.get('entity_id', '')
        rule = event.get('rule_id', '')
        signature = event.get('signature', '')
        
        # パターンキーを生成
        pattern_key = f"{entity}:{rule}:{signature}"
        
        # 各抑制ルールをチェック
        for supp_rule in self.config['suppression_rules']:
            pattern = supp_rule.get('pattern', '')
            
            # パターンマッチング
            if self._pattern_matches(pattern_key, pattern):
                # 時間ウィンドウ内のイベントを取得
                window = supp_rule.get('window', 3600)
                threshold = supp_rule.get('threshold', 3)
                suppress_duration = supp_rule.get('suppress_duration', 1800)
                
                now = datetime.now()
                cache_key = f"{pattern}:{pattern_key}"
                
                # キャッシュをクリーンアップ
                while self.suppression_cache[cache_key] and \
                      (now - self.suppression_cache[cache_key][0]).total_seconds() > window:
                    self.suppression_cache[cache_key].popleft()
                
                # 現在のイベントを追加
                self.suppression_cache[cache_key].append(now)
                
                # 閾値を超えた場合は抑制
                if len(self.suppression_cache[cache_key]) >= threshold:
                    # 最後の抑制から一定時間経過していれば再度抑制
                    last_suppression = event.get('_last_suppressed', 0)
                    if (now.timestamp() - last_suppression) > suppress_duration:
                        event['_last_suppressed'] = now.timestamp()
                        return True  # 抑制
        
        return False  # 通過
    
    def apply_false_positive_filters(self, event: Dict) -> bool:
        """誤検知フィルタを適用（True=フィルタ、False=通過）"""
        entity = event.get('entity_id', '')
        rule = event.get('rule_id', '')
        signature = event.get('signature', '')
        
        # パターンキーを生成
        pattern_key = f"{entity}:{rule}:{signature}"
        
        for fp_filter in self.config['false_positive_filters']:
            pattern = fp_filter.get('pattern', '')
            confidence = fp_filter.get('confidence', 0.8)
            
            # パターンマッチング
            if self._pattern_matches(pattern_key, pattern):
                # 信頼度チェック（ランダム性を入れる代わりにハッシュ値を使用）
                hash_val = int(hashlib.md5(f"{pattern_key}{event.get('timestamp', '')}".encode()).hexdigest()[:8], 16)
                if (hash_val % 100) / 100 < confidence:
                    if fp_filter.get('auto_suppress', False):
                        return True  # フィルタ
        
        return False  # 通過
    
    def _pattern_matches(self, text: str, pattern: str) -> bool:
        """パターンマッチング"""
        # ワイルドカード対応
        if '*' in pattern:
            parts = pattern.split('*')
            if len(parts) == 2:
                return text.startswith(parts[0]) and text.endswith(parts[1])
            elif pattern.startswith('*'):
                return text.endswith(pattern[1:])
            elif pattern.endswith('*'):
                return text.startswith(pattern[:-1])
        return pattern in text
    
    def process_event(self, event: Dict) -> Dict:
        """イベントを処理してチューニングを適用"""
        self.metrics['events_processed'] += 1
        
        # 1. 閾値調整を適用
        event = self.apply_threshold_adjustments(event)
        
        # 2. 誤検知フィルタを適用
        if self.apply_false_positive_filters(event):
            self.metrics['events_suppressed'] += 1
            event['_suppressed'] = True
            event['_suppression_reason'] = 'false_positive_filter'
            return event
        
        # 3. 抑制ルールを適用
        if self.apply_suppression_rules(event):
            self.metrics['events_suppressed'] += 1
            event['_suppressed'] = True
            event['_suppression_reason'] = 'suppression_rule'
            return event
        
        # イベントは通過
        self.metrics['events_passed'] += 1
        event['_suppressed'] = False
        return event
    
    def process_batch(self, events: List[Dict]) -> Tuple[List[Dict], Dict]:
        """バッチ処理"""
        processed_events = []
        suppressed_events = []
        
        for event in events:
            processed = self.process_event(event)
            if processed.get('_suppressed', False):
                suppressed_events.append(processed)
            else:
                processed_events.append(processed)
        
        # 削減率を計算
        total = len(events)
        suppressed = len(suppressed_events)
        reduction_rate = suppressed / total if total > 0 else 0
        
        return processed_events, {
            'total_events': total,
            'suppressed_events': suppressed,
            'passed_events': len(processed_events),
            'reduction_rate': reduction_rate,
            'metrics': self.metrics.copy()
        }
    
    def optimize_config(self, feedback: Dict) -> Dict:
        """フィードバックに基づいて設定を最適化"""
        current_reduction = feedback.get('current_reduction_rate', 0)
        target_reduction = feedback.get('target_reduction_rate', 0.6)
        
        if current_reduction < target_reduction:
            # 削減率が目標に達していない場合、ルールを強化
            gap = target_reduction - current_reduction
            
            # 閾値をさらに緩和
            for key in self.config['threshold_adjustments']:
                current_multiplier = self.config['threshold_adjustments'][key].get('multiplier', 1.0)
                self.config['threshold_adjustments'][key]['multiplier'] = max(0.5, current_multiplier - 0.1)
            
            # 抑制ルールの閾値を下げる
            for rule in self.config['suppression_rules']:
                current_threshold = rule.get('threshold', 3)
                rule['threshold'] = max(1, current_threshold - 1)
                rule['window'] = min(7200, rule.get('window', 3600) * 1.2)  # ウィンドウを拡大
            
            # 誤検知フィルタの信頼度を下げる（より多くフィルタ）
            for fp_filter in self.config['false_positive_filters']:
                current_confidence = fp_filter.get('confidence', 0.8)
                fp_filter['confidence'] = min(0.95, current_confidence + 0.05)
        
        # 設定を保存
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        return self.config


def main():
    parser = argparse.ArgumentParser(description='A/B Test Tuner')
    parser.add_argument('--input', default='data/raw/events_splunk_2025-09-05_170644.jsonl', 
                        help='Input events file')
    parser.add_argument('--output', default='data/ab/B_tuned.jsonl', 
                        help='Output tuned events file')
    parser.add_argument('--config', default='config/tuning_config.json', 
                        help='Tuning configuration file')
    parser.add_argument('--optimize', action='store_true', 
                        help='Optimize configuration based on results')
    
    args = parser.parse_args()
    
    # チューナーを初期化
    tuner = ABTuner(args.config)
    
    # イベントを読み込み
    events = []
    with open(args.input, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    print(f"📥 {len(events)}件のイベントを読み込みました")
    
    # チューニングを適用
    passed_events, stats = tuner.process_batch(events)
    
    # 結果を表示
    print("\n" + "="*60)
    print("🎯 チューニング結果")
    print("="*60)
    print(f"入力イベント数: {stats['total_events']}")
    print(f"抑制イベント数: {stats['suppressed_events']}")
    print(f"通過イベント数: {stats['passed_events']}")
    print(f"削減率: {stats['reduction_rate']*100:.1f}%")
    
    # 通過イベントを保存
    with open(args.output, 'w') as f:
        for event in passed_events:
            # 内部フィールドを削除
            cleaned_event = {k: v for k, v in event.items() if not k.startswith('_')}
            f.write(json.dumps(cleaned_event, ensure_ascii=False) + '\n')
    
    print(f"\n💾 チューニング済みイベントを保存: {args.output}")
    
    # 最適化モード
    if args.optimize:
        print("\n🔧 設定を最適化中...")
        feedback = {
            'current_reduction_rate': stats['reduction_rate'],
            'target_reduction_rate': 0.6
        }
        optimized_config = tuner.optimize_config(feedback)
        print(f"✅ 最適化完了: {args.config}")
        
        # 再度処理して改善を確認
        tuner_optimized = ABTuner(args.config)
        passed_events_opt, stats_opt = tuner_optimized.process_batch(events)
        
        print(f"\n📈 最適化後の削減率: {stats_opt['reduction_rate']*100:.1f}%")
        print(f"   改善幅: {(stats_opt['reduction_rate'] - stats['reduction_rate'])*100:.1f}%")
    
    return 0


if __name__ == '__main__':
    exit(main())
