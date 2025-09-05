# app/metrics/kpi_metrics.py
import json
import pathlib
from prometheus_client import Gauge

g_red_count = Gauge("bolcd_ab_reduction_by_count", "AB reduction by count")
g_red_unique = Gauge("bolcd_ab_reduction_by_unique", "AB reduction by unique")
g_new_in_b = Gauge("bolcd_ab_new_in_b", "New uniques only in B")

g_tot = Gauge("bolcd_ab_total_alerts", "AB total alerts", ["arm"])
g_uni = Gauge("bolcd_ab_unique_alerts", "AB unique alerts", ["arm"])
g_dup = Gauge("bolcd_ab_duplicates", "AB duplicates", ["arm"])

g_tri_p50 = Gauge("bolcd_triage_p50_seconds", "Triage P50 seconds")
g_tri_p90 = Gauge("bolcd_triage_p90_seconds", "Triage P90 seconds")
g_cases = Gauge("bolcd_cases_processed_daily", "Cases processed (daily)")

g_ing_gb = Gauge("bolcd_cost_ingest_gb", "Ingest GB", ["arm"])
g_costpgb = Gauge("bolcd_cost_per_gb_usd", "Cost per GB (USD)")
g_save = Gauge("bolcd_cost_savings_usd", "Cost savings (USD)")

g_backlog = Gauge("bolcd_backlog_untriaged", "Backlog (untriaged)")
g_br_ratio = Gauge("bolcd_backlog_ratio", "Backlog ratio")
g_mttd = Gauge("bolcd_mttd_median_seconds", "MTTD median seconds")
g_mttr = Gauge("bolcd_mttr_median_seconds", "MTTR median seconds")


def _latest(path: pathlib.Path, prefix: str):
    cand = sorted(path.glob(f"{prefix}_*.json"))
    return cand[-1] if cand else None


def update_from_reports(reports_dir: str = "/reports"):
    d = pathlib.Path(reports_dir)
    if not d.exists():
        return
    
    # 1) KPI daily
    kpi = _latest(d, "kpi")
    if kpi:
        try:
            data = json.loads(kpi.read_text(encoding='utf-8'))

            noise = data.get("noise", {})
            if noise:
                if noise.get("reduction_by_count") is not None:
                    g_red_count.set(noise["reduction_by_count"])
                if noise.get("reduction_by_unique") is not None:
                    g_red_unique.set(noise["reduction_by_unique"])
                if noise.get("new_in_b") is not None:
                    g_new_in_b.set(noise["new_in_b"])

                for arm in ("A", "B"):
                    if noise.get(f"{arm}_total") is not None:
                        g_tot.labels(arm=arm).set(noise[f"{arm}_total"])
                    if noise.get(f"{arm}_unique") is not None:
                        g_uni.labels(arm=arm).set(noise[f"{arm}_unique"])
                    if noise.get(f"{arm}_duplicates") is not None:
                        g_dup.labels(arm=arm).set(noise[f"{arm}_duplicates"])

            ops = data.get("ops", {})
            if ops:
                if ops.get("triage_p50_seconds") is not None:
                    g_tri_p50.set(ops["triage_p50_seconds"])
                if ops.get("triage_p90_seconds") is not None:
                    g_tri_p90.set(ops["triage_p90_seconds"])
                if ops.get("cases_processed_daily") is not None:
                    g_cases.set(ops["cases_processed_daily"])

            cost = data.get("cost", {})
            if cost:
                if cost.get("ingest_gb_A") is not None:
                    g_ing_gb.labels(arm="A").set(cost["ingest_gb_A"])
                if cost.get("ingest_gb_B") is not None:
                    g_ing_gb.labels(arm="B").set(cost["ingest_gb_B"])
                if cost.get("cost_per_gb_usd") is not None:
                    g_costpgb.set(cost["cost_per_gb_usd"])
                if cost.get("savings_usd") is not None:
                    g_save.set(cost["savings_usd"])

            risk = data.get("risk", {})
            if risk:
                if risk.get("backlog_untriaged") is not None:
                    g_backlog.set(risk["backlog_untriaged"])
                if risk.get("backlog_ratio") is not None:
                    g_br_ratio.set(risk["backlog_ratio"])
                if risk.get("mttd_median_seconds") is not None:
                    g_mttd.set(risk["mttd_median_seconds"])
                if risk.get("mttr_median_seconds") is not None:
                    g_mttr.set(risk["mttr_median_seconds"])
        except Exception:
            # never fail metrics endpoint due to parsing errors
            return
