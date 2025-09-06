#!/usr/bin/env python3
"""
False Suppression Validator - 誤抑制の検証と追跡システム
誤抑制を正確に判定するための多層的な検証フレームワーク
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, Counter
import numpy as np
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""
    total_suppressed: int
    confirmed_false_suppressions: int
    suspected_false_suppressions: int
    confidence_level: float
    validation_method: str
    details: Dict

class FalseSuppressionValidator:
    """誤抑制を多角的に検証するバリデータ"""
    
    def __init__(self, suppressed_file: str, passed_file: str, original_file: str = None):
        self.suppressed = self._load_events(suppressed_file)
        self.passed = self._load_events(passed_file)
        self.original = self._load_events(original_file) if original_file else []
        
        # 検証結果を格納
        self.validation_results = {}
        
        # インシデント判定のための重要パターン
        self.incident_patterns = {
            'critical_auth': [
                'authentication.*failed.*admin',
                'privilege.*escalation',
                'unauthorized.*root.*access',
                'brute.*force.*detected',
                'account.*lockout.*multiple'
            ],
            'data_breach': [
                'data.*exfiltration',
                'sensitive.*data.*exposed',
                'database.*dump',
                'unauthorized.*download.*large',
                'confidential.*file.*accessed'
            ],
            'malware': [
                'malware.*detected',
                'ransomware.*activity',
                'trojan.*found',
                'virus.*signature.*matched',
                'suspicious.*executable'
            ],
            'network_attack': [
                'ddos.*attack',
                'port.*scan.*aggressive',
                'sql.*injection.*successful',
                'remote.*code.*execution',
                'zero.*day.*exploit'
            ]
        }
        
    def _load_events(self, file_path: str) -> List[Dict]:
        """イベントファイルを読み込み"""
        if not file_path or not Path(file_path).exists():
            return []
        
        events = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        return events
    
    def validate_by_severity_rules(self) -> ValidationResult:
        """
        方法1: Severity/Signatureベースの検証
        High/Criticalイベントの抑制を誤抑制として判定
        """
        false_suppressions = []
        suspected = []
        
        for event in self.suppressed:
            severity = event.get('severity', 'unknown').lower()
            # signature not used presently; derive features from raw only
            raw = event.get('_raw', '').lower()
            
            # Critical/Highは原則誤抑制
            if severity in ['critical', 'high']:
                false_suppressions.append(event)
            
            # 特定のキーワードを含む場合は疑い
            danger_keywords = ['failed', 'denied', 'error', 'attack', 'malware', 
                             'unauthorized', 'breach', 'exploit', 'injection']
            if any(kw in raw for kw in danger_keywords):
                if event not in false_suppressions:
                    suspected.append(event)
        
        confidence = 0.9 if len(false_suppressions) == 0 else 0.7
        
        return ValidationResult(
            total_suppressed=len(self.suppressed),
            confirmed_false_suppressions=len(false_suppressions),
            suspected_false_suppressions=len(suspected),
            confidence_level=confidence,
            validation_method="Severity/Keyword Rules",
            details={
                'false_suppression_events': [e.get('event_id', e.get('rule_id')) for e in false_suppressions[:5]],
                'suspected_events': [e.get('event_id', e.get('rule_id')) for e in suspected[:5]]
            }
        )
    
    def validate_by_incident_correlation(self) -> ValidationResult:
        """
        方法2: インシデント相関による検証
        抑制イベントの後に関連する重大イベントが発生したかチェック
        """
        false_suppressions = []
        time_window = timedelta(hours=1)  # 1時間以内の相関を見る
        
        # 時系列でソート
        all_events = self.suppressed + self.passed
        all_events.sort(key=lambda x: x.get('timestamp', ''))
        
        # 各抑制イベントについて後続イベントをチェック
        for supp_event in self.suppressed:
            supp_time = datetime.fromisoformat(supp_event.get('timestamp', datetime.now().isoformat()))
            supp_entity = supp_event.get('entity_id', '')
            
            # 同じエンティティで後続の重大イベントを探す
            for event in all_events:
                event_time = datetime.fromisoformat(event.get('timestamp', datetime.now().isoformat()))
                
                # 時間窓内で同じエンティティ
                if (event_time > supp_time and 
                    event_time - supp_time <= time_window and
                    event.get('entity_id') == supp_entity):
                    
                    # 重大イベントかチェック
                    if (event.get('severity') in ['critical', 'high'] or
                        self._is_incident_pattern(event)):
                        false_suppressions.append({
                            'suppressed_event': supp_event,
                            'correlated_incident': event,
                            'time_delta': str(event_time - supp_time)
                        })
                        break
        
        confidence = 0.85  # 相関ベースなので少し控えめ
        
        return ValidationResult(
            total_suppressed=len(self.suppressed),
            confirmed_false_suppressions=len(false_suppressions),
            suspected_false_suppressions=0,
            confidence_level=confidence,
            validation_method="Incident Correlation",
            details={
                'correlated_pairs': len(false_suppressions),
                'examples': false_suppressions[:3]
            }
        )
    
    def _is_incident_pattern(self, event: Dict) -> bool:
        """イベントがインシデントパターンに合致するかチェック"""
        raw = event.get('_raw', '').lower()
        
        for category, patterns in self.incident_patterns.items():
            for pattern in patterns:
                # 簡易的な正規表現マッチング
                keywords = pattern.split('.*')
                if all(kw in raw for kw in keywords):
                    return True
        return False
    
    def validate_by_statistical_anomaly(self) -> ValidationResult:
        """
        方法3: 統計的異常検知による検証
        レアイベントや異常パターンの抑制を検出
        """
        false_suppressions = []
        
        # エンティティごとのイベント頻度を計算
        entity_counts = Counter()
        for event in self.passed + self.suppressed:
            entity_counts[event.get('entity_id')] += 1
        
        # 平均と標準偏差
        counts = list(entity_counts.values())
        if counts:
            mean_count = np.mean(counts)
            std_count = np.std(counts)
            
            # レアエンティティ（平均-2σ以下）のイベント抑制をチェック
            rare_threshold = max(1, mean_count - 2 * std_count)
            
            for event in self.suppressed:
                entity = event.get('entity_id')
                if entity_counts[entity] <= rare_threshold:
                    false_suppressions.append({
                        'event': event,
                        'reason': 'rare_entity',
                        'entity_frequency': entity_counts[entity],
                        'threshold': rare_threshold
                    })
        
        # バースト検知（短時間に集中）
        time_buckets = defaultdict(list)
        for event in self.suppressed:
            timestamp = event.get('timestamp', '')
            if timestamp:
                # 10分単位でバケット化
                bucket = timestamp[:15] + '0:00'
                time_buckets[bucket].append(event)
        
        # バースト判定（10分で5件以上）
        for bucket, events in time_buckets.items():
            if len(events) >= 5:
                for event in events:
                    if not any(fs['event'] == event for fs in false_suppressions):
                        false_suppressions.append({
                            'event': event,
                            'reason': 'burst_pattern',
                            'burst_size': len(events),
                            'time_bucket': bucket
                        })
        
        confidence = 0.75  # 統計的手法なので中程度の信頼度
        
        return ValidationResult(
            total_suppressed=len(self.suppressed),
            confirmed_false_suppressions=len(false_suppressions),
            suspected_false_suppressions=0,
            confidence_level=confidence,
            validation_method="Statistical Anomaly",
            details={
                'rare_entity_suppressions': sum(1 for fs in false_suppressions if fs['reason'] == 'rare_entity'),
                'burst_suppressions': sum(1 for fs in false_suppressions if fs['reason'] == 'burst_pattern')
            }
        )
    
    def validate_by_shadow_mode(self, shadow_results: Optional[Dict] = None) -> ValidationResult:
        """
        方法4: Shadow Modeによる検証
        実際のSOCアナリストの判定と比較（シミュレーション）
        """
        if not shadow_results:
            # シミュレーション：ランダムに10%をサンプリングして人手判定を模擬
            sample_size = max(1, len(self.suppressed) // 10)
            sampled = random.sample(self.suppressed, min(sample_size, len(self.suppressed)))
            
            # 実際にはSOCアナリストの判定が必要
            # ここではヒューリスティックで模擬
            shadow_results = {}
            for event in sampled:
                # 判定ロジック（実際は人手）
                is_false = (
                    event.get('severity') in ['critical', 'high'] or
                    'error' in event.get('_raw', '').lower() or
                    self._is_incident_pattern(event)
                )
                shadow_results[event.get('rule_id', '')] = {
                    'should_pass': is_false,
                    'analyst_confidence': 0.9 if is_false else 0.8
                }
        
        # Shadow結果から誤抑制を集計
        false_suppressions = []
        for event in self.suppressed:
            rule_id = event.get('rule_id', '')
            if rule_id in shadow_results and shadow_results[rule_id]['should_pass']:
                false_suppressions.append(event)
        
        # サンプリングから全体を推定
        sample_rate = len(shadow_results) / max(1, len(self.suppressed))
        estimated_false = int(len(false_suppressions) / sample_rate) if sample_rate > 0 else 0
        
        # 信頼区間を計算（Clopper-Pearson）
        n_samples = len(shadow_results)
        n_false = len(false_suppressions)
        if n_samples > 0:
            # 簡易的な95%信頼区間
            p = n_false / n_samples
            margin = 1.96 * np.sqrt(p * (1 - p) / n_samples)
            ci_lower = max(0, p - margin)
            ci_upper = min(1, p + margin)
        else:
            ci_lower, ci_upper = 0, 1
        
        confidence = 0.95 if n_samples >= 30 else 0.8
        
        return ValidationResult(
            total_suppressed=len(self.suppressed),
            confirmed_false_suppressions=len(false_suppressions),
            suspected_false_suppressions=estimated_false - len(false_suppressions),
            confidence_level=confidence,
            validation_method="Shadow Mode (Sampled)",
            details={
                'sample_size': n_samples,
                'sample_false_suppressions': n_false,
                'estimated_total_false': estimated_false,
                'confidence_interval': f"[{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]"
            }
        )
    
    def validate_all_methods(self) -> Dict:
        """
        すべての検証方法を実行して総合判定
        """
        results = {}
        
        print("🔍 誤抑制の多層的検証を開始...")
        print("="*70)
        
        # 各検証方法を実行
        methods = [
            ('severity_rules', self.validate_by_severity_rules),
            ('incident_correlation', self.validate_by_incident_correlation),
            ('statistical_anomaly', self.validate_by_statistical_anomaly),
            ('shadow_mode', self.validate_by_shadow_mode)
        ]
        
        for name, method in methods:
            print(f"\n📊 検証方法: {name}")
            result = method()
            results[name] = result
            
            print(f"  抑制総数: {result.total_suppressed}")
            print(f"  確定誤抑制: {result.confirmed_false_suppressions}")
            print(f"  疑い誤抑制: {result.suspected_false_suppressions}")
            print(f"  信頼度: {result.confidence_level:.1%}")
            
            # 詳細表示
            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"  {key}: {value[:3]}...")
                    else:
                        print(f"  {key}: {value}")
        
        # 総合判定
        all_confirmed = sum(r.confirmed_false_suppressions for r in results.values())
        _ = sum(r.suspected_false_suppressions for r in results.values())
        avg_confidence = np.mean([r.confidence_level for r in results.values()])
        
        # 重み付き平均（信頼度で重み付け）
        weighted_false = sum(
            r.confirmed_false_suppressions * r.confidence_level 
            for r in results.values()
        ) / sum(r.confidence_level for r in results.values())
        
        print("\n" + "="*70)
        print("📈 総合判定結果:")
        print(f"  検証方法数: {len(results)}")
        print(f"  平均信頼度: {avg_confidence:.1%}")
        print(f"  最大誤抑制数: {all_confirmed}")
        print(f"  重み付き誤抑制推定: {weighted_false:.1f}")
        
        # 最終的な誤抑制率
        if self.suppressed:
            false_suppression_rate = weighted_false / len(self.suppressed)
            print(f"\n🎯 推定誤抑制率: {false_suppression_rate:.2%}")
            
            if false_suppression_rate < 0.01:
                print("  ✅ 誤抑制率は許容範囲内です（<1%）")
            elif false_suppression_rate < 0.05:
                print("  ⚠️ 誤抑制率がやや高めです（1-5%）")
            else:
                print("  ❌ 誤抑制率が高すぎます（>5%）- 調整が必要")
        
        return {
            'individual_results': results,
            'summary': {
                'total_suppressed': len(self.suppressed),
                'weighted_false_suppressions': weighted_false,
                'estimated_false_rate': false_suppression_rate if self.suppressed else 0,
                'average_confidence': avg_confidence,
                'recommendation': self._get_recommendation(false_suppression_rate if self.suppressed else 0)
            }
        }
    
    def _get_recommendation(self, false_rate: float) -> str:
        """誤抑制率に基づく推奨事項"""
        if false_rate < 0.01:
            return "現在の設定は適切です。運用を継続してください。"
        elif false_rate < 0.05:
            return "High/Criticalイベントの抑制基準を見直すことを推奨します。"
        else:
            return "抑制ルールの大幅な見直しが必要です。Shadow Modeでの運用を検討してください。"
    
    def export_validation_report(self, output_file: str = "reports/false_suppression_validation.json"):
        """検証結果をレポートとして出力"""
        results = self.validate_all_methods()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_files': {
                'suppressed_count': len(self.suppressed),
                'passed_count': len(self.passed)
            },
            'validation_results': results,
            'metadata': {
                'validator_version': '1.0.0',
                'methods_used': list(results['individual_results'].keys())
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 検証レポートを保存: {output_path}")
        return output_path

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="誤抑制の検証")
    parser.add_argument('--suppressed', required=True, help='抑制されたイベントファイル')
    parser.add_argument('--passed', required=True, help='通過したイベントファイル')
    parser.add_argument('--original', help='元のイベントファイル（オプション）')
    parser.add_argument('--output', default='reports/false_suppression_validation.json', help='出力レポート')
    args = parser.parse_args()
    
    validator = FalseSuppressionValidator(args.suppressed, args.passed, args.original)
    validator.export_validation_report(args.output)

if __name__ == "__main__":
    main()
