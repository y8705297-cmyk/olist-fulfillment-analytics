import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.proportion import confint_proportions_2indep


def risk_difference(label, late, timely):
    late_n, timely_n = len(late), len(timely)
    late_low, timely_low = int(late.sum()), int(timely.sum())
    lower, upper = confint_proportions_2indep(late_low, late_n, timely_low, timely_n, method="newcomb")
    return {
        "sample": label, "late_n": late_n, "timely_n": timely_n,
        "late_low": late_low, "timely_low": timely_low,
        "late_rate": late_low / late_n, "timely_rate": timely_low / timely_n,
        "risk_difference": late_low / late_n - timely_low / timely_n, "lower": lower, "upper": upper,
    }


def fit_logit(label, sample, adjusted=False, cluster=None, threshold=2):
    # Pool sparse levels before fitting. Pooling uses frequency independently of the outcome.
    delay = sample["is_delayed"].astype(float).rename("delayed")
    design = delay.to_frame()
    if adjusted:
        for feature in ("month", "customer_state", "category_key"):
            labels = sample[feature].fillna("(unknown)")
            common = labels.value_counts()
            pooled = labels.where(labels.isin(common[common >= 100].index), "(sparse)")
            design = design.join(pd.get_dummies(pooled, prefix=feature, drop_first=True, dtype=float))
    design = sm.add_constant(design)
    outcome = (sample["review_score"] <= threshold).astype(float)
    model = sm.GLM(outcome, design, family=sm.families.Binomial())
    kwargs = {"cov_type": "cluster", "cov_kwds": {"groups": sample[cluster].to_numpy()}} if cluster else {}
    result = model.fit(**kwargs)
    lower, upper = result.conf_int().loc["delayed"]
    if not result.converged or not np.isfinite([lower, upper, *result.params]).all():
        raise RuntimeError(f"Invalid fit for {label}")
    return {
        "model": label, "n": len(sample), "events": int(outcome.sum()),
        "delayed_n": int(delay.sum()), "parameters": len(result.params), "cluster": cluster,
        "clusters": sample[cluster].nunique() if cluster else None, "converged": result.converged,
        "iterations": result.fit_history["iteration"], "se_log_odds": result.bse["delayed"],
        "odds_ratio": np.exp(result.params["delayed"]), "lower": np.exp(lower), "upper": np.exp(upper),
    }


def review_results(con):
    orders = con.execute("""
        SELECT a.*, strftime(a.purchase_month, '%Y-%m') AS month,
               r.review_score AS earliest_score
        FROM (
            SELECT order_id, purchase_month, is_delayed, delay_band, review_score, mature,
                   seller_id, customer_unique_id, customer_state, category_key
            FROM analysis_orders WHERE is_delayed IS NOT NULL
        ) a
        LEFT JOIN (
            SELECT order_id, review_score FROM raw_order_reviews
            QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY
                review_answer_timestamp ASC NULLS LAST, review_creation_date ASC NULLS LAST,
                review_id ASC NULLS LAST, review_score ASC NULLS LAST) = 1
        ) r USING (order_id)
        ORDER BY a.order_id
    """).df()
    orders["rated"] = orders.review_score.between(1, 5)
    rated = orders[orders.rated]
    mature = rated[rated.mature]
    single = mature[mature.seller_id.notna()]
    nonpeak = mature[~mature.month.isin(["2017-11", "2018-02", "2018-03"])]
    risks = []
    for label, data, column, threshold in (
        ("Full snapshot", rated, "review_score", 2),
        ("Mature window", mature, "review_score", 2),
        ("Mature window excluding peaks", nonpeak, "review_score", 2),
        ("Mature window, score <= 3", mature, "review_score", 3),
        ("Full snapshot, earliest review", orders[orders.earliest_score.between(1, 5)], "earliest_score", 2),
    ):
        low = data[column] <= threshold
        risks.append(risk_difference(label, low[data.is_delayed], low[~data.is_delayed]))
    for label, late_missing_low in (("All missing assigned to minimize gap", False),
                                     ("All missing assigned to maximize gap", True)):
        low = orders.review_score.le(2).fillna(False)
        late_low = low.mask(~orders.rated & orders.is_delayed, late_missing_low)
        timely_low = low.mask(~orders.rated & ~orders.is_delayed, not late_missing_low)
        risks.append(risk_difference(label, late_low[orders.is_delayed], timely_low[~orders.is_delayed]))
    timely_reference = rated.loc[~rated.is_delayed, "review_score"] <= 2
    bands = []
    for band, label in enumerate(("<=0", "1-3", "4-7", "8-14", "15+")):
        band_sample = orders[orders.delay_band == band]
        band_low = band_sample.loc[band_sample.rated, "review_score"] <= 2
        row = {"band": label, "eligible": len(band_sample), "rated": len(band_low), "low_rate": band_low.mean()}
        if band > 0:
            contrast = risk_difference(label, band_low, timely_reference)
            for key in ("risk_difference", "lower", "upper"):
                row[key] = contrast[key]
        bands.append(row)
    models = [
        fit_logit("Full snapshot, crude", rated),
        fit_logit("Mature window, crude", mature),
        fit_logit("Mature window, adjusted", mature, adjusted=True),
        fit_logit("Mature window, customer-clustered", mature, adjusted=True, cluster="customer_unique_id"),
        fit_logit("Mature single seller, crude", single, cluster="seller_id"),
        fit_logit("Mature single seller, adjusted", single, adjusted=True, cluster="seller_id"),
        fit_logit("Mature excluding peaks, adjusted", nonpeak, adjusted=True),
        fit_logit("Mature score <= 3, adjusted", mature, threshold=3, adjusted=True),
        fit_logit("Full snapshot, adjusted", rated, adjusted=True),
    ]
    coverage = (
        orders.groupby("is_delayed", as_index=False).agg(eligible=("order_id", "size"), rated=("rated", "sum"))
    )
    coverage["rating_coverage"] = coverage.rated / coverage.eligible
    return {
        "review_risk_difference": pd.DataFrame(risks),
        "review_delay_bands": pd.DataFrame(bands),
        "review_logit": pd.DataFrame(models),
        "review_coverage": coverage,
    }
