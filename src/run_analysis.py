import platform

import duckdb
import matplotlib
import numpy as np
import pandas as pd
import scipy
import statsmodels

from src.analysis_audit import audit
from src.config import DB, PROCESSED, ROOT
from src.review_analysis import review_results
from src.seller_analysis import seller_stability


TABLES = {
    "audit_top10": "selection, rank",
    "monthly_delivery": "purchase_month",
    "state_delivery": "late DESC, customer_state",
    "primary_category_delivery": "late DESC, category_key",
    "delivery_by_category": "late_orders DESC, category_key",
    "stage_delivery": "stage, delayed",
    "peak_comparison": "comparison",
    "peak_state": "comparison, excess DESC, customer_state",
    "peak_weekly": "purchase_month, week_in_month",
    "november_daily": "purchase_day",
    "period_seller_scores": "period, score DESC, late DESC, seller_id",
    "threshold_ranks": "period, threshold, rank",
    "threshold_coverage": "period, threshold",
    "seller_followup": "early_rank, late_rank",
    "final_seller_queue": "queue_order",
    "final_seller_stages": "seller_id, delayed",
    "final_scenario": "scope, relative_improvement",
    "audit_cohort_peak_segments": "cohort_late DESC, customer_state, category_key",
    "final_seller_peak_sensitivity": "holdout_slice, group_name",
}


def verify_outputs(con, tables):
    assert con.execute("SELECT count(*) - count(DISTINCT order_id) FROM analysis_orders").fetchone() == (0,)
    for name in ("monthly_delivery", "state_delivery", "primary_category_delivery"):
        assert tuple(tables[name][["eligible", "late"]].sum()) == (96470, 6534)
    paired = tables["seller_followup"]
    queue = tables["final_seller_queue"]
    expected = paired[(paired.early_score > 0) & (paired.late_score > 0)
                      & (paired.peer_coverage >= .70) & (paired.peer_excess > 0)]
    assert queue.seller_id.is_unique and set(queue.seller_id) == set(expected.seller_id)
    assert (queue[["early_n", "late_n"]] >= 50).all().all()
    scenario = tables["final_scenario"]
    full = scenario[scenario.scope == "Full holdout"]
    peak = scenario[scenario.scope == "Feb-Mar peak"]
    assert (full.baseline_orders == queue.late_n.sum()).all()
    assert (full.baseline_late == queue.late_late.sum()).all()
    peak_segments = tables["audit_cohort_peak_segments"]
    assert (peak.baseline_orders == peak_segments.cohort_n.sum()).all()
    assert (peak.baseline_late == peak_segments.cohort_late.sum()).all()
    np.testing.assert_allclose(scenario.fewer_late_orders, scenario.relative_improvement * scenario.baseline_late)
    models = tables["review_logit"].set_index("model")
    assert models.converged.all()
    cross_tab = con.execute("SELECT rated, low FROM audit_ratings ORDER BY delayed").fetchall()
    (timely_n, timely_low), (late_n, late_low) = cross_tab
    crude_or = late_low * (timely_n - timely_low) / ((late_n - late_low) * timely_low)
    np.testing.assert_allclose(models.loc["Full snapshot, crude", "odds_ratio"], crude_or)
    np.testing.assert_allclose(models.loc["Mature window, adjusted", "odds_ratio"],
                               models.loc["Mature window, customer-clustered", "odds_ratio"])
    assert models.loc["Mature single seller, adjusted", "clusters"] > 1
    assert tuple(tables["review_delay_bands"][["eligible", "rated"]].sum()) == (96470, 95824)
    print("Formal analysis checks passed: grains, aggregations, cohort eligibility, scenario, "
          "regression convergence, crude OR and clustered coefficient reconciliation", flush=True)


def main():
    from src.analysis_figures import render

    print(f"Python {platform.python_version()}, DuckDB {duckdb.__version__}, "
          f"pandas {pd.__version__}, SciPy {scipy.__version__}, "
          f"statsmodels {statsmodels.__version__}, Matplotlib {matplotlib.__version__}", flush=True)
    with duckdb.connect(str(DB), read_only=True) as con:
        audit(con)
        for section in ("delivery", "sellers"):
            con.execute((ROOT / "analysis" / f"{section}.sql").read_text())
        tables = {name: con.execute(f"SELECT * FROM {name} ORDER BY {sort}").df() for name, sort in TABLES.items()}
        tables.update(seller_stability(tables["threshold_ranks"], tables["seller_followup"],
                                       tables["period_seller_scores"]))
        tables.update(review_results(con))
        verify_outputs(con, tables)
    target = PROCESSED / "analysis"
    target.mkdir(parents=True, exist_ok=True)
    for name, data in tables.items():
        data.to_csv(target / f"{name}.csv", index=False, float_format="%.10g")
        print(f"{name}: {len(data)} rows", flush=True)
    render(tables, ROOT / "figures")


if __name__ == "__main__":
    main()
