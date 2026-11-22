CREATE TEMP VIEW period_seller_orders AS
SELECT period, seller_id, customer_state, category_key, is_delayed, valid_phases,
       purchase_to_carrier_days, carrier_to_delivery_days
FROM analysis_orders WHERE period IS NOT NULL AND seller_id IS NOT NULL AND is_delayed IS NOT NULL
UNION ALL
SELECT 'all', seller_id, customer_state, category_key, is_delayed, valid_phases,
       purchase_to_carrier_days, carrier_to_delivery_days
FROM analysis_orders WHERE seller_id IS NOT NULL AND is_delayed IS NOT NULL;

CREATE TEMP VIEW period_seller_scores AS
WITH counts AS (
    SELECT period, seller_id, count(*) AS eligible, sum(is_delayed::INT)::BIGINT AS late
    FROM period_seller_orders GROUP BY 1, 2
), benchmarks AS (
    SELECT *, sum(late) OVER (PARTITION BY period)::DOUBLE
              / sum(eligible) OVER (PARTITION BY period) AS baseline
    FROM counts
)
SELECT *, late::DOUBLE / eligible AS late_rate,
       (late + 50 * baseline) / (eligible + 50) AS smoothed_rate,
       greatest(0, ((late + 50 * baseline) / (eligible + 50) - baseline) * eligible) AS score
FROM benchmarks;

CREATE TEMP VIEW threshold_ranks AS
SELECT t.threshold, p.*,
       row_number() OVER (
           PARTITION BY t.threshold, period ORDER BY score DESC, late DESC, seller_id
       ) AS rank
FROM period_seller_scores p CROSS JOIN (VALUES (30), (50), (100)) t(threshold)
WHERE eligible >= threshold;

CREATE TEMP VIEW threshold_coverage AS
WITH totals AS (
    SELECT period, sum(eligible) AS eligible, sum(late) AS late FROM period_seller_scores GROUP BY 1
)
SELECT r.period, r.threshold, count(*) AS sellers, sum(r.eligible) AS eligible, sum(r.late) AS late,
       sum(r.eligible)::DOUBLE / t.eligible AS eligible_share,
       sum(r.late)::DOUBLE / t.late AS late_share
FROM threshold_ranks r JOIN totals t USING (period)
GROUP BY r.period, r.threshold, t.eligible, t.late;

CREATE TEMP VIEW holdout_peers AS
WITH seller_strata AS (
    SELECT seller_id, customer_state, category_key, count(*) AS eligible, sum(is_delayed::INT) AS late
    FROM period_seller_orders WHERE period = 'late' GROUP BY 1, 2, 3
), peer_totals AS (
    SELECT *, sum(eligible) OVER strata - eligible AS peer_n, sum(late) OVER strata - late AS peer_late
    FROM seller_strata
    WINDOW strata AS (PARTITION BY customer_state, category_key)
)
SELECT seller_id, sum(eligible)::BIGINT AS covered, sum(late)::BIGINT AS observed,
       sum(eligible * peer_late::DOUBLE / peer_n) AS expected
FROM peer_totals WHERE peer_n >= 50 GROUP BY seller_id;

CREATE TEMP VIEW seller_followup AS
SELECT e.seller_id, e.rank AS early_rank, l.rank AS late_rank, e.eligible AS early_n, e.late AS early_late,
       e.score AS early_score, l.eligible AS late_n, l.late AS late_late, l.score AS late_score,
       l.late_rate AS holdout_rate, l.baseline AS holdout_baseline, p.covered AS covered_n,
       p.covered::DOUBLE / l.eligible AS peer_coverage, p.observed, p.expected,
       p.observed - p.expected AS peer_excess
FROM threshold_ranks e JOIN threshold_ranks l USING (seller_id, threshold)
LEFT JOIN holdout_peers p USING (seller_id)
WHERE e.period = 'early' AND l.period = 'late' AND e.threshold = 50;

CREATE TEMP VIEW final_seller_queue AS
SELECT *, row_number() OVER (ORDER BY peer_excess DESC, late_late DESC, seller_id) AS queue_order
FROM seller_followup
WHERE early_score > 0 AND late_score > 0 AND peer_coverage >= .70 AND peer_excess > 0;

CREATE TEMP VIEW final_seller_stages AS
SELECT q.seller_id, o.is_delayed AS delayed, count(*) AS stage_n,
       median(o.purchase_to_carrier_days) AS handoff_p50_days,
       median(o.carrier_to_delivery_days) AS transit_p50_days
FROM final_seller_queue q JOIN period_seller_orders o USING (seller_id)
WHERE o.period = 'late' AND o.valid_phases GROUP BY 1, 2;

CREATE TEMP VIEW final_scenario AS
WITH seller_scopes AS (
    SELECT 'Full holdout' AS scope, seller_id, late_n AS eligible, late_late AS late FROM final_seller_queue
    UNION ALL
    SELECT 'Feb-Mar peak' AS scope, a.seller_id, count(*) AS eligible, sum(a.is_delayed::INT) AS late
    FROM analysis_orders a JOIN final_seller_queue q USING (seller_id)
    WHERE a.purchase_month IN (DATE '2018-02-01', DATE '2018-03-01')
      AND a.is_delayed IS NOT NULL
    GROUP BY a.seller_id
)
SELECT scope, relative_improvement, count(*) AS sellers, sum(eligible) AS baseline_orders,
       sum(late) AS baseline_late, sum(late)::DOUBLE / sum(eligible) AS baseline_late_rate,
       sum(late)::DOUBLE / sum(eligible) * (1 - relative_improvement) AS scenario_late_rate,
       sum(late) * relative_improvement AS fewer_late_orders
FROM seller_scopes CROSS JOIN (VALUES (.10), (.20)) s(relative_improvement)
GROUP BY scope, relative_improvement;

CREATE TEMP VIEW final_seller_peak_sensitivity AS
SELECT CASE WHEN a.purchase_month IN (DATE '2018-02-01', DATE '2018-03-01')
            THEN 'Feb-Mar 2018' ELSE 'Other holdout months' END AS holdout_slice,
       CASE WHEN q.seller_id IS NOT NULL THEN 'Audit cohort' ELSE 'Other single-seller orders' END AS group_name,
       count(*) AS eligible, sum(a.is_delayed::INT) AS late, avg(a.is_delayed::INT) AS late_rate
FROM analysis_orders a LEFT JOIN final_seller_queue q USING (seller_id)
WHERE a.period = 'late' AND a.seller_id IS NOT NULL AND a.is_delayed IS NOT NULL
GROUP BY 1, 2;


CREATE TEMP VIEW audit_cohort_peak_segments AS
WITH sliced AS (
    SELECT a.customer_state, a.category_key, q.seller_id IS NOT NULL AS in_cohort, a.is_delayed
    FROM analysis_orders a LEFT JOIN final_seller_queue q USING (seller_id)
    WHERE a.purchase_month IN (DATE '2018-02-01', DATE '2018-03-01')
      AND a.seller_id IS NOT NULL AND a.is_delayed IS NOT NULL
)
SELECT customer_state, category_key,
       count(*) FILTER (WHERE in_cohort) AS cohort_n,
       sum(is_delayed::INT) FILTER (WHERE in_cohort) AS cohort_late,
       avg(is_delayed::INT) FILTER (WHERE in_cohort) AS cohort_rate,
       count(*) FILTER (WHERE NOT in_cohort) AS peer_n,
       sum(is_delayed::INT) FILTER (WHERE NOT in_cohort) AS peer_late,
       avg(is_delayed::INT) FILTER (WHERE NOT in_cohort) AS peer_rate
FROM sliced GROUP BY 1, 2 HAVING count(*) FILTER (WHERE in_cohort) > 0;
