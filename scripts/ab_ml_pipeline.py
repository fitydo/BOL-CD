#!/usr/bin/env python3
"""
A/B ML Pipeline - 機械学習パイプラインによる自動最適化
"""
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime
import numpy as np

class ABMLPipeline:
    def __init__(self, config_path: str = "config/production_rules.json"):
        self.config_path = Path(config_path)
        self.metrics_history = []
        self.models = {}
        
    def run_command(self, cmd: str) -> Tuple[int, str, str]:
        """コマンド実行"""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    
    def collect_data(self, source: str = "splunk", hours: int = 24) -> Path:
        """データ収集フェーズ"""
        print(f"📥 データ収集中 (source={source}, hours={hours})...")
        
        # SIEMからデータ取得
        cmd = f"python scripts/siem_connector.py --source {source} --mode fetch"
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode != 0:
            print(f"❌ データ収集エラー: {stderr}")
            return None
        
        # 最新ファイルを特定
        latest_files = sorted(Path("data/raw").glob("events_*.jsonl"), 
                            key=lambda p: p.stat().st_mtime, reverse=True)
        
        if latest_files:
            return latest_files[0]
        return None
    
    def feature_engineering(self, input_file: Path) -> Dict:
        """特徴量エンジニアリング"""
        print("🔧 特徴量エンジニアリング中...")
        
        events = []
        with open(input_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        features = {
            'total_events': len(events),
            'unique_entities': len(set(e.get('entity_id', '') for e in events)),
            'unique_rules': len(set(e.get('rule_id', '') for e in events)),
            'severity_distribution': {},
            'time_distribution': {},
            'top_patterns': []
        }
        
        # 重要度分布
        severity_counts = {}
        for e in events:
            sev = e.get('severity', 'unknown')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        features['severity_distribution'] = severity_counts
        
        # パターン頻度TOP10
        pattern_counts = {}
        for e in events:
            pattern = f"{e.get('entity_id')}:{e.get('rule_id')}"
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        features['top_patterns'] = [{'pattern': p, 'count': c} for p, c in top_patterns]
        
        return features
    
    def train_model(self, input_file: Path) -> Dict:
        """モデル学習フェーズ"""
        print("🧠 モデル学習中...")
        
        # Robust Optimizerで学習
        cmd = f"python scripts/ab_robust_optimizer.py --input {input_file} --target-reduction 0.5"
        returncode, stdout, stderr = self.run_command(cmd)
        
        if returncode != 0:
            print(f"❌ 学習エラー: {stderr}")
            return None
        
        # 学習結果を解析
        lines = stdout.split('\n')
        metrics = {}
        for line in lines:
            if '削減率:' in line and '最終モデル' in line:
                # 削減率を抽出
                parts = line.split(':')
                if len(parts) >= 2:
                    rate_str = parts[-1].strip().replace('%', '')
                    try:
                        metrics['reduction_rate'] = float(rate_str) / 100
                    except Exception:
                        pass
            elif 'アンサンブル合意度:' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        metrics['ensemble_agreement'] = float(parts[-1].strip())
                    except Exception:
                        pass
        
        return metrics
    
    def apply_rules(self, input_file: Path, rules_file: Path) -> Tuple[Path, Dict]:
        """ルール適用フェーズ"""
        print("📋 ルール適用中...")
        
        # ルールを読み込み
        with open(rules_file, 'r') as f:
            rules = json.load(f)
        
        # イベントを読み込み
        events = []
        with open(input_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        # ルール適用ロジック
        suppressed = []
        passed = []
        
        for event in events:
            should_suppress = False
            
            # 抑制ルールをチェック
            for rule in rules.get('suppression_rules', []):
                pattern = f"{event.get('entity_id')}:{event.get('rule_id')}"
                if pattern == rule['pattern']:
                    should_suppress = True
                    break
            
            if should_suppress:
                suppressed.append(event)
            else:
                passed.append(event)
        
        # 結果を保存
        output_file = Path(f"data/ab/pipeline_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            for event in passed:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        
        metrics = {
            'total_events': len(events),
            'suppressed_count': len(suppressed),
            'passed_count': len(passed),
            'reduction_rate': len(suppressed) / len(events) if events else 0
        }
        
        return output_file, metrics
    
    def evaluate(self, metrics: Dict) -> Dict:
        """評価フェーズ"""
        print("📊 パフォーマンス評価中...")
        
        evaluation = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'performance': {}
        }
        
        # 目標との比較
        target_reduction = 0.5
        actual_reduction = metrics.get('reduction_rate', 0)
        
        evaluation['performance']['target_achievement'] = actual_reduction / target_reduction
        evaluation['performance']['is_acceptable'] = actual_reduction >= target_reduction * 0.9
        
        # 履歴に追加
        self.metrics_history.append(evaluation)
        
        # 移動平均を計算（直近5回）
        if len(self.metrics_history) >= 2:
            recent_rates = [h['metrics'].get('reduction_rate', 0) 
                          for h in self.metrics_history[-5:]]
            evaluation['performance']['moving_average'] = np.mean(recent_rates)
            evaluation['performance']['trend'] = 'improving' if recent_rates[-1] > recent_rates[0] else 'declining'
        
        return evaluation
    
    def run_pipeline(self, source: str = "splunk") -> Dict:
        """完全なパイプライン実行"""
        print("\n" + "="*60)
        print("🚀 A/B最適化パイプライン開始")
        print("="*60)
        
        results = {}
        
        # 1. データ収集
        data_file = self.collect_data(source)
        if not data_file:
            return {'error': 'Data collection failed'}
        results['data_file'] = str(data_file)
        
        # 2. 特徴量エンジニアリング
        features = self.feature_engineering(data_file)
        results['features'] = features
        
        # 3. モデル学習
        train_metrics = self.train_model(data_file)
        if train_metrics:
            results['training'] = train_metrics
        
        # 4. ルール適用
        output_file, apply_metrics = self.apply_rules(data_file, self.config_path)
        results['application'] = apply_metrics
        results['output_file'] = str(output_file)
        
        # 5. 評価
        evaluation = self.evaluate(apply_metrics)
        results['evaluation'] = evaluation
        
        # サマリー表示
        print("\n" + "="*60)
        print("📈 パイプライン実行結果")
        print("="*60)
        print(f"入力データ: {features['total_events']}件")
        print(f"削減率: {apply_metrics['reduction_rate']*100:.1f}%")
        print(f"目標達成度: {evaluation['performance']['target_achievement']*100:.1f}%")
        
        if evaluation['performance']['is_acceptable']:
            print("✅ パフォーマンス基準を満たしています")
        else:
            print("⚠️ パフォーマンス改善が必要です")
        
        if 'moving_average' in evaluation['performance']:
            print(f"移動平均: {evaluation['performance']['moving_average']*100:.1f}%")
            print(f"トレンド: {evaluation['performance']['trend']}")
        
        return results
    
    def continuous_learning(self, interval_minutes: int = 60):
        """継続学習モード"""
        print(f"♾️ 継続学習モード開始 (間隔: {interval_minutes}分)")
        
        while True:
            try:
                # パイプライン実行
                results = self.run_pipeline()
                
                # 結果を保存
                report_file = Path(f"reports/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                report_file.parent.mkdir(parents=True, exist_ok=True)
                with open(report_file, 'w') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 レポート保存: {report_file}")
                
                # 待機
                print(f"\n⏰ 次回実行まで{interval_minutes}分待機...")
                import time
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n🛑 継続学習を停止しました")
                break
            except Exception as e:
                print(f"\n❌ エラー: {e}")
                print(f"⏰ {interval_minutes}分後に再試行...")
                import time
                time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description='A/B ML Pipeline')
    parser.add_argument('--mode', choices=['single', 'continuous'], default='single',
                       help='Execution mode')
    parser.add_argument('--source', default='splunk',
                       help='Data source')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval for continuous mode (minutes)')
    
    args = parser.parse_args()
    
    pipeline = ABMLPipeline()
    
    if args.mode == 'single':
        # 単発実行
        results = pipeline.run_pipeline(args.source)
        
        # 結果を保存
        output_file = Path(f"reports/ml_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 完全なレポート: {output_file}")
        
    else:
        # 継続学習モード
        pipeline.continuous_learning(args.interval)
    
    return 0


if __name__ == '__main__':
    exit(main())
