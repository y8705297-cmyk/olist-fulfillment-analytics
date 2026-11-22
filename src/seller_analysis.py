import pandas as pd
from scipy.stats import spearmanr


def seller_stability(ranks, followup, scores):
    all_ranks = ranks[ranks.period == "all"]
    default_top = set(all_ranks.loc[(all_ranks.threshold == 50) & (all_ranks["rank"] <= 10), "seller_id"])
    threshold_rows = []
    temporal_rows = []
    for threshold in (30, 50, 100):
        current = ranks[ranks.threshold == threshold]
        groups = {period: current[current.period == period] for period in ("all", "early", "late")}
        full_top = set(groups["all"].loc[groups["all"]["rank"] <= 10, "seller_id"])
        threshold_rows.append({
            "threshold": threshold, "top10_overlap_with_50": len(full_top & default_top),
            "top10_late": groups["all"].loc[groups["all"]["rank"] <= 10, "late"].sum(),
        })
        paired = groups["early"].merge(groups["late"], on="seller_id", suffixes=("_early", "_late"))
        early_top = set(groups["early"].loc[groups["early"]["rank"] <= 10, "seller_id"])
        late_top = set(groups["late"].loc[groups["late"]["rank"] <= 10, "seller_id"])
        correlation = spearmanr(paired.score_early, paired.score_late)
        validation = paired[paired.seller_id.isin(early_top)]
        holdout_top = scores[(scores.period == "late") & scores.seller_id.isin(early_top)]
        temporal_rows.append({
            "threshold": threshold, "paired_sellers": len(paired), "spearman_score": correlation.statistic,
            "top10_overlap": len(early_top & late_top), "early_top10_with_any_holdout": len(holdout_top),
            "early_top10_with_threshold_in_holdout": len(validation),
            "early_top10_positive_in_eligible_holdout": (validation.score_late > 0).sum(),
            "early_top10_holdout_n": holdout_top.eligible.sum(),
            "early_top10_holdout_late": holdout_top.late.sum(),
            "holdout_baseline": groups["late"].baseline.iloc[0],
        })
    assert followup.seller_id.nunique() == temporal_rows[1]["paired_sellers"]
    return {
        "seller_threshold_overlap": pd.DataFrame(threshold_rows),
        "seller_temporal_stability": pd.DataFrame(temporal_rows),
    }
