#!/usr/bin/env python3
"""
AB Validation Harness - 再現性/有意性の検証
- 固定ソルトでのA/B分割（再現性確保）
- baseline vs tuned（チューニング適用後）
- 直近3データセットで平均・分散・95%CIを算出
- 同一入力での決定性（determinism）チェック
"""
import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib
import shutil
import random
import math

RAW_DIR = Path("data/raw")
SCRIPTS_DIR = Path("scripts")
AB_DIR = Path("data/ab")
TMP_DIR = Path("tmp/validate")
TMP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SALT = "REPRO-VALIDATION-001"

@dataclass
class Metrics:
    reduction_by_count: float
    reduction_by_unique: float
    A_total: int
    B_total: int


def run(cmd: str) -> None:
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")


def latest_three_raw_files() -> List[Path]:
    files = sorted(RAW_DIR.glob("events_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:3]


def run_ab_split(inp: Path, out_dir: Path, salt: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = (
        f"python scripts/ab/ab_split.py --in {inp} --out-dir {out_dir} "
        f"--key-fields entity_id,rule_id --salt {salt}"
    )
    run(cmd)


def run_ab_report(a: Path, b: Path, out_dir: Path, label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    before = set(out_dir.glob("ab_*.json"))
    cmd = (
        f"python scripts/ab/ab_report.py --in-a {a} --in-b {b} "
        f"--out-dir {out_dir} --date-label {label}"
    )
    run(cmd)
    after = set(out_dir.glob("ab_*.json"))
    created = list(after - before)
    if not created:
        # fallback: pick latest
        created = sorted(list(after), key=lambda p: p.stat().st_mtime, reverse=True)[:1]
    if not created:
        raise SystemExit("ab_report did not create any JSON output")
    return created[0]


def parse_metrics(report_json: Path) -> Metrics:
    data = json.loads(report_json.read_text(encoding="utf-8"))
    A_total = int(data.get("A", {}).get("total", 0))
    B_total = int(data.get("B", {}).get("total", 0))
    reduction_by_count = float(data.get("reduction_by_count", 0.0))
    reduction_by_unique = float(data.get("reduction_by_unique", 0.0))
    return Metrics(
        reduction_by_count=reduction_by_count,
        reduction_by_unique=reduction_by_unique,
        A_total=A_total,
        B_total=B_total,
    )


def run_tuner_on_b(b_path: Path, out_path: Path) -> None:
    # 既存のチューナーを使用（決定的動作）
    cmd = f"python scripts/ab_tuner.py --input {b_path} --output {out_path}"
    run(cmd)


def run_optimizer_on_b(b_path: Path, out_path: Path) -> None:
    """ab_optimizer を使って B を最適化し、出力を out_path に配置"""
    # 実行（固定ターゲット削減率）
    cmd = f"python scripts/ab_optimizer.py --target-reduction 0.6 --input {b_path}"
    run(cmd)
    # ツール既定の出力を拾ってコピー（衝突回避のため移動）
    src = Path("data/ab/B_optimized.jsonl")
    if not src.exists():
        raise SystemExit("ab_optimizer output not found: data/ab/B_optimized.jsonl")
    shutil.copy(src, out_path)


def apply_production_rules_to_b(b_path: Path, rules_json: Path, out_path: Path) -> None:
    """production_rules.json を用いて B をフィルタリングし out_path を生成"""
    import json as _json
    rules = _json.loads(rules_json.read_text(encoding="utf-8"))
    suppression = set()
    for rule in rules.get("suppression_rules", []):
        pat = rule.get("pattern", "")
        if pat:
            suppression.add(pat)
    # イベントを読み込み、pattern が suppression にあれば除外
    passed = []
    with b_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = _json.loads(line)
            pattern = f"{ev.get('entity_id')}:{ev.get('rule_id')}"
            if pattern in suppression:
                continue
            passed.append(ev)
    with out_path.open("w") as f:
        for ev in passed:
            f.write(_json.dumps(ev, ensure_ascii=False) + "\n")


def generate_production_rules_from_raw(raw_files: List[Path], out_rules_path: Path) -> None:
    """raw の複数ファイルを結合して堅牢最適化から本番ルールを生成"""
    tmp = Path("tmp/validate/train_combined.jsonl")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w") as w:
        for rf in raw_files:
            with rf.open() as r:
                shutil.copyfileobj(r, w)
    cmd = (
        f"python scripts/ab_robust_optimizer.py --input {tmp} "
        f"--cv-folds 3 --output-rules {out_rules_path}"
    )
    run(cmd)


def _severity_weight(sev: str) -> float:
    s = str(sev).lower() if sev is not None else ""
    # 数値を許容（1-5など）: 高い数値=高重要度とみなす
    try:
        val = float(s)
        # 5/4=critical, 3=high, 2=medium, 1=low相当
        if val >= 4.5:
            return 0.1
        if val >= 3.5:
            return 0.3
        if val >= 2.5:
            return 0.7
        return 1.0
    except Exception:
        pass
    # ラベルでの判定
    if any(k in s for k in ["critical", "crit"]):
        return 0.1
    if any(k in s for k in ["high", "sev:high"]):
        return 0.3
    if any(k in s for k in ["medium", "med"]):
        return 0.7
    if any(k in s for k in ["low"]):
        return 1.0
    # 既知でない場合は中庸
    return 0.7


def _load_events(path: Path) -> List[Dict]:
    events: List[Dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


def compute_additional_metrics(a_path: Path, b_orig_path: Path, b_variant_path: Path) -> Dict:
    """重み付き削減率・誤抑制率など追加指標を計算"""
    a_events = _load_events(a_path)
    b_orig = _load_events(b_orig_path)
    b_var = _load_events(b_variant_path)

    # 重み付き削減率（重要度に応じた重み）
    wA = sum(_severity_weight(
        e.get("severity", e.get("AlertSeverity", e.get("event.severity")))
    ) for e in a_events)
    wB = sum(_severity_weight(
        e.get("severity", e.get("AlertSeverity", e.get("event.severity")))
    ) for e in b_var)
    weighted_reduction = (wA - wB) / wA if wA > 0 else 0.0

    # 誤抑制率（重大度の高いイベントがBでどれだけ削減されたか）
    severe = {"high", "critical", "4", "5"}
    def _sev_level(e):
        s = str(e.get("severity", e.get("AlertSeverity", e.get("event.severity", "")))).lower()
        if any(k in s for k in ["critical", "5"]):
            return "critical"
        if any(k in s for k in ["high", "4"]):
            return "high"
        if any(k in s for k in ["medium", "3"]):
            return "medium"
        if any(k in s for k in ["low", "2", "1"]):
            return "low"
        # シグネチャから推定
        sig = str(e.get("signature", "")).lower()
        if any(k in sig for k in ["escalation", "malware", "exfiltration", "ransom"]):
            return "critical"
        if any(k in sig for k in ["sql", "ddos", "injection", "bruteforce"]):
            return "high"
        if any(k in sig for k in ["failed", "unauthorized", "scan", "port_scan"]):
            return "medium"
        return "low"
    b_severe_total = sum(1 for e in b_orig if _sev_level(e) in {"high", "critical"})
    b_severe_after = sum(1 for e in b_var if _sev_level(e) in {"high", "critical"})
    false_suppress_rate = (b_severe_total - b_severe_after) / b_severe_total if b_severe_total > 0 else 0.0

    return {
        "weighted_reduction": weighted_reduction,
        "false_suppression_rate": false_suppress_rate,
        "A_weight_sum": wA,
        "B_weight_sum": wB,
        "B_severe_total": b_severe_total,
        "B_severe_after": b_severe_after,
    }


def determinism_check(inp: Path, salt: str) -> bool:
    # 同一入力・同一SALTで2回分割→A/Bの行数が一致するか
    d1 = TMP_DIR / f"det_{inp.stem}_1"
    d2 = TMP_DIR / f"det_{inp.stem}_2"
    for d in (d1, d2):
        if d.exists():
            for f in d.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
    run_ab_split(inp, d1, salt)
    run_ab_split(inp, d2, salt)
    a1 = sum(1 for _ in (d1 / "A.jsonl").open())
    b1 = sum(1 for _ in (d1 / "B.jsonl").open())
    a2 = sum(1 for _ in (d2 / "A.jsonl").open())
    b2 = sum(1 for _ in (d2 / "B.jsonl").open())
    return (a1, b1) == (a2, b2)


def mean_std_ci(values: List[float]) -> Tuple[float, float, Tuple[float, float]]:
    import math
    if not values:
        return 0.0, 0.0, (0.0, 0.0)
    n = len(values)
    mean = sum(values) / n
    if n == 1:
        return mean, 0.0, (mean, mean)
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(var)
    # 95% CI using t-distribution (n<=30)
    # t for df=2 (~4.303), df=3 (~3.182)
    t_map = {2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571}
    t_val = t_map.get(n, 1.96)
    half = t_val * std / (n ** 0.5)
    return mean, std, (mean - half, mean + half)


def bootstrap_ci(values: List[float], n_boot: int = 1000, seed: int = 42) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    random.seed(seed)
    size = len(values)
    samples = []
    for _ in range(n_boot):
        draw = [values[random.randrange(size)] for _ in range(size)]
        samples.append(sum(draw) / size)
    samples.sort()
    lo_idx = int(0.025 * n_boot)
    hi_idx = int(0.975 * n_boot)
    return (samples[lo_idx], samples[hi_idx])


def validate_extended(files: List[Path], salts: List[str], modes: List[str], counterfactual: bool = False) -> Dict:
    """拡張検証: 複数SALT・複数モード（tuner/optimizer/rules）"""
    results: List[Dict] = []
    det_flags: List[bool] = []

    for i, inp in enumerate(files, 1):
        base = inp.stem
        for salt in salts:
            # 決定性チェック（AB分割）
            det_ok = determinism_check(inp, salt)
            det_flags.append(det_ok)

            out_dir = TMP_DIR / f"run_{i}_{base}_{hashlib.sha1(salt.encode()).hexdigest()[:6]}"
            out_dir.mkdir(parents=True, exist_ok=True)

            # 分割
            run_ab_split(inp, out_dir, salt)

            # baseline
            baseline_json = run_ab_report(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir, f"baseline_{base}_{salt}")
            baseline = parse_metrics(baseline_json)

            record = {
                "file": str(inp),
                "salt": salt,
                "baseline": baseline.__dict__,
                "modes": {}
            }

            # baselineの追加指標
            record["baseline_extra"] = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir / "B.jsonl")

            # 各モードで評価
            if "tuner" in modes:
                b_tuned = out_dir / "B_tuned.jsonl"
                run_tuner_on_b(out_dir / "B.jsonl", b_tuned)
                tuned_json = run_ab_report(out_dir / "A.jsonl", b_tuned, out_dir, f"tuned_{base}_{salt}")
                record["modes"]["tuner"] = parse_metrics(tuned_json).__dict__
                record.setdefault("modes_extra", {})["tuner"] = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", b_tuned)

            if "optimizer" in modes:
                b_opt = out_dir / "B_opt.jsonl"
                run_optimizer_on_b(out_dir / "B.jsonl", b_opt)
                opt_json = run_ab_report(out_dir / "A.jsonl", b_opt, out_dir, f"opt_{base}_{salt}")
                record["modes"]["optimizer"] = parse_metrics(opt_json).__dict__
                record.setdefault("modes_extra", {})["optimizer"] = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", b_opt)

                # 反事実テスト（必要に応じてA側にも適用して挙動確認）
                if counterfactual:
                    a_opt = out_dir / "A_opt.jsonl"
                    # A を最適化して B と比較（指標の解釈に注意）
                    run_optimizer_on_b(out_dir / "A.jsonl", a_opt)
                    opt_cf_json = run_ab_report(a_opt, out_dir / "B.jsonl", out_dir, f"opt_cf_{base}_{salt}")
                    record["modes"]["optimizer_cf_A"] = parse_metrics(opt_cf_json).__dict__
                    record.setdefault("modes_extra", {})["optimizer_cf_A"] = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir / "B.jsonl")

            results.append(record)

    # LOOCV（rules モードのみ）：各ファイルをテスト、他ファイルの raw で学習
    if "rules" in modes and len(files) >= 2:
        for i, test_file in enumerate(files):
            train_raw = [p for j, p in enumerate(files) if j != i]
            rules_out = TMP_DIR / f"rules_{i}.json"
            generate_production_rules_from_raw(train_raw, rules_out)
            for salt in salts:
                out_dir = TMP_DIR / f"rules_run_{i}_{hashlib.sha1(salt.encode()).hexdigest()[:6]}"
                out_dir.mkdir(parents=True, exist_ok=True)
                run_ab_split(test_file, out_dir, salt)
                b_rules = out_dir / "B_rules.jsonl"
                apply_production_rules_to_b(out_dir / "B.jsonl", rules_out, b_rules)
                rules_json = run_ab_report(out_dir / "A.jsonl", b_rules, out_dir, f"rules_{test_file.stem}_{salt}")
                record = {
                    "file": str(test_file),
                    "salt": salt,
                    "baseline": parse_metrics(run_ab_report(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir, f"baseline_rules_{test_file.stem}_{salt}")).__dict__,
                    "modes": {"rules": parse_metrics(rules_json).__dict__},
                    "loocv": True
                }
                results.append(record)

    # 集計（baseline と各モードについて）
    def collect_rates(key: str) -> List[float]:
        vals: List[float] = []
        for r in results:
            if key == "baseline":
                vals.append(r["baseline"]["reduction_by_count"])
            else:
                if key in r.get("modes", {}):
                    vals.append(r["modes"][key]["reduction_by_count"])
        return vals

    def collect_weighted(key: str) -> List[float]:
        vals: List[float] = []
        for r in results:
            if key == "baseline":
                m = r.get("baseline_extra")
                if m:
                    vals.append(m.get("weighted_reduction", 0.0))
            else:
                m = r.get("modes_extra", {}).get(key)
                if m:
                    vals.append(m.get("weighted_reduction", 0.0))
        return vals

    def collect_false_suppress(key: str) -> Tuple[List[float], int, int]:
        rates: List[float] = []
        total_before = 0
        total_after = 0
        for r in results:
            if key == "baseline":
                m = r.get("baseline_extra")
            else:
                m = r.get("modes_extra", {}).get(key)
            if m:
                rates.append(m.get("false_suppression_rate", 0.0))
                total_before += int(m.get("B_severe_total", 0))
                total_after += int(m.get("B_severe_after", 0))
        return rates, total_before, total_after

    def paired_sign_test(b_list: List[float], o_list: List[float]) -> Dict:
        pairs = list(zip(b_list, o_list))
        diffs = [o - b for b, o in pairs]
        n = len(diffs)
        if n == 0:
            return {"n": 0, "pos": 0, "p_value": 1.0}
        pos = sum(1 for d in diffs if d > 0)
        # two-sided binomial sign test
        def binom_pmf(k, n):
            return math.comb(n, k) * (0.5 ** n)
        p_tail = sum(binom_pmf(k, n) for k in range(0, min(pos, n - pos) + 1))
        p_value = min(1.0, 2 * p_tail)
        return {"n": n, "pos": pos, "p_value": p_value}

    summary = {
        "n": len(results),
        "deterministic_all": all(det_flags) if det_flags else True,
        "baseline": {},
        "tuner": {},
        "optimizer": {},
        "rules": {},
        "weighted": {},
        "false_suppression": {},
        "sign_test_optimizer_vs_baseline": {},
    }
    for key in ["baseline", "tuner", "optimizer", "rules"]:
        rates = collect_rates(key)
        mean, std, ci = mean_std_ci(rates)
        boot_lo, boot_hi = bootstrap_ci(rates) if len(rates) >= 2 else (mean, mean)
        summary[key] = {"mean": mean, "std": std, "ci95": ci, "boot_ci95": (boot_lo, boot_hi), "samples": len(rates)}

    # 追加（重み付き）
    for key in ["baseline", "tuner", "optimizer", "rules"]:
        wr = collect_weighted(key)
        if wr:
            mean, std, ci = mean_std_ci(wr)
            boot_lo, boot_hi = bootstrap_ci(wr) if len(wr) >= 2 else (mean, mean)
            summary.setdefault("weighted", {})[key] = {"mean": mean, "std": std, "ci95": ci, "boot_ci95": (boot_lo, boot_hi), "samples": len(wr)}

    # 追加（誤抑制）
    for key in ["baseline", "tuner", "optimizer", "rules"]:
        rates, tot_bef, tot_aft = collect_false_suppress(key)
        if rates:
            mean, std, ci = mean_std_ci(rates)
            boot_lo, boot_hi = bootstrap_ci(rates) if len(rates) >= 2 else (mean, mean)
            summary.setdefault("false_suppression", {})[key] = {
                "rate": {"mean": mean, "std": std, "ci95": ci, "boot_ci95": (boot_lo, boot_hi), "samples": len(rates)},
                "counts": {"total_severe_before": tot_bef, "total_severe_after": tot_aft}
            }

    # 有意差検定（paired, non-param: sign test）
    base_rates = collect_rates("baseline")
    opt_rates = collect_rates("optimizer")
    m = min(len(base_rates), len(opt_rates))
    if m > 0:
        st = paired_sign_test(base_rates[:m], opt_rates[:m])
        summary["sign_test_optimizer_vs_baseline"] = st

    return {"summary": summary, "results": results}


def timeseries_rules_cv(files: List[Path], salts: List[str]) -> Dict:
    """時系列CV: 先行データで学習し、後続データで評価（rulesモード）"""
    # ファイルを時系列でソート（mtime昇順）
    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)
    if len(files_sorted) < 2:
        return {"error": "Not enough files for time-series CV"}
    split = max(1, int(len(files_sorted) * 0.6))
    train_files = files_sorted[:split]
    test_files = files_sorted[split:]

    rules_out = TMP_DIR / "ts_rules.json"
    generate_production_rules_from_raw(train_files, rules_out)

    records: List[Dict] = []
    for test in test_files:
        for salt in salts:
            out_dir = TMP_DIR / f"ts_{test.stem}_{hashlib.sha1(salt.encode()).hexdigest()[:6]}"
            out_dir.mkdir(parents=True, exist_ok=True)
            run_ab_split(test, out_dir, salt)
            base_json = run_ab_report(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir, f"ts_base_{test.stem}_{salt}")
            b_rules = out_dir / "B_rules.jsonl"
            apply_production_rules_to_b(out_dir / "B.jsonl", rules_out, b_rules)
            rules_json = run_ab_report(out_dir / "A.jsonl", b_rules, out_dir, f"ts_rules_{test.stem}_{salt}")
            extra_base = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", out_dir / "B.jsonl")
            extra_rules = compute_additional_metrics(out_dir / "A.jsonl", out_dir / "B.jsonl", b_rules)
            rec = {
                "file": str(test),
                "salt": salt,
                "baseline": parse_metrics(base_json).__dict__,
                "rules": parse_metrics(rules_json).__dict__,
                "baseline_extra": extra_base,
                "rules_extra": extra_rules,
            }
            records.append(rec)

    def coll(key: str) -> List[float]:
        vals: List[float] = []
        for r in records:
            vals.append(r[key]["reduction_by_count"])
        return vals

    base_rates = coll("baseline")
    rules_rates = coll("rules")
    mean_b, std_b, ci_b = mean_std_ci(base_rates)
    mean_r, std_r, ci_r = mean_std_ci(rules_rates)
    boot_b = bootstrap_ci(base_rates) if len(base_rates) >= 2 else (mean_b, mean_b)
    boot_r = bootstrap_ci(rules_rates) if len(rules_rates) >= 2 else (mean_r, mean_r)

    # 追加指標の集計
    def coll_weighted(key: str) -> List[float]:
        vals: List[float] = []
        for r in records:
            m = r.get(f"{key}_extra")
            if m:
                vals.append(m.get("weighted_reduction", 0.0))
        return vals

    def coll_false(key: str) -> Tuple[int, int]:
        bef = 0
        aft = 0
        for r in records:
            m = r.get(f"{key}_extra")
            if m:
                bef += int(m.get("B_severe_total", 0))
                aft += int(m.get("B_severe_after", 0))
        return bef, aft

    w_base = coll_weighted("baseline")
    w_rules = coll_weighted("rules")
    w_base_mean, w_base_std, w_base_ci = mean_std_ci(w_base) if w_base else (0.0, 0.0, (0.0, 0.0))
    w_rules_mean, w_rules_std, w_rules_ci = mean_std_ci(w_rules) if w_rules else (0.0, 0.0, (0.0, 0.0))
    w_base_boot = bootstrap_ci(w_base) if len(w_base) >= 2 else (w_base_mean, w_base_mean)
    w_rules_boot = bootstrap_ci(w_rules) if len(w_rules) >= 2 else (w_rules_mean, w_rules_mean)

    fs_base = coll_false("baseline")
    fs_rules = coll_false("rules")

    return {
        "train_files": [str(p) for p in train_files],
        "test_files": [str(p) for p in test_files],
        "summary": {
            "baseline": {"mean": mean_b, "std": std_b, "ci95": ci_b, "boot_ci95": boot_b, "samples": len(base_rates)},
            "rules": {"mean": mean_r, "std": std_r, "ci95": ci_r, "boot_ci95": boot_r, "samples": len(rules_rates)},
            "weighted": {
                "baseline": {"mean": w_base_mean, "std": w_base_std, "ci95": w_base_ci, "boot_ci95": w_base_boot, "samples": len(w_base)},
                "rules": {"mean": w_rules_mean, "std": w_rules_std, "ci95": w_rules_ci, "boot_ci95": w_rules_boot, "samples": len(w_rules)}
            },
            "false_suppression_counts": {
                "baseline": {"total_severe_before": fs_base[0], "total_severe_after": fs_base[1]},
                "rules": {"total_severe_before": fs_rules[0], "total_severe_after": fs_rules[1]}
            }
        },
        "results": records,
    }


def main():
    parser = argparse.ArgumentParser(description="A/B再現性検証ハーネス（拡張版）")
    parser.add_argument("--files", nargs="*", help="raw events jsonl files")
    parser.add_argument("--out", default="reports/ab_validation_extended.json", help="output json path")
    parser.add_argument("--salts", nargs="*", default=[DEFAULT_SALT, "REPRO-VALIDATION-002", "REPRO-VALIDATION-003"], help="salts for A/B split")
    parser.add_argument("--modes", nargs="*", default=["tuner", "optimizer", "rules"], help="tuning modes")
    parser.add_argument("--counterfactual", action="store_true", help="apply optimizer to A for counterfactual test")
    args = parser.parse_args()

    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = latest_three_raw_files()

    if not files:
        print("No raw files found in data/raw")
        return 1

    print("検証対象ファイル:")
    for f in files:
        print(f" - {f}")

    result = validate_extended(files, args.salts, args.modes, counterfactual=args.counterfactual)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    s = result["summary"]
    print("\n==== 検証サマリー（拡張） ====")
    print(f"サンプル数: {s['n']}")
    print(f"決定性（同一入力で一致）: {'OK' if s['deterministic_all'] else 'NG'}")
    for key in ["baseline", "tuner", "optimizer", "rules"]:
        if s.get(key):
            print(f"{key:9s}: mean={s[key]['mean']*100:.1f}% (std={s[key]['std']*100:.1f}%, CI95=[{s[key]['ci95'][0]*100:.1f}%, {s[key]['ci95'][1]*100:.1f}%], bootCI=[{s[key]['boot_ci95'][0]*100:.1f}%, {s[key]['boot_ci95'][1]*100:.1f}%], n={s[key]['samples']})")
    print(f"詳細: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
