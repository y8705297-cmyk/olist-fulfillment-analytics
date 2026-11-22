CREATE TEMP VIEW analysis_orders AS
SELECT f.*, date_trunc('month', f.purchase_timestamp)::DATE AS purchase_month,
       coalesce(p.category_key, '(unknown)') AS category_key,
       coalesce(t.product_category_name_english, p.category_key, '(unknown)') AS category,
       s.seller_id,
       f.purchase_timestamp >= DATE '2017-01-01' AND f.purchase_timestamp < DATE '2018-08-01' AS mature,
       CASE WHEN f.purchase_timestamp >= DATE '2017-01-01' AND f.purchase_timestamp < DATE '2018-01-01' THEN 'early'
            WHEN f.purchase_timestamp >= DATE '2018-01-01' AND f.purchase_timestamp < DATE '2018-08-01' THEN 'late' END AS period,
       carrier_timestamp BETWEEN f.purchase_timestamp AND delivered_timestamp AND f.is_delayed IS NOT NULL AS valid_phases,
       CASE WHEN f.delay_days <= 0 THEN 0 WHEN f.delay_days <= 3 THEN 1
            WHEN f.delay_days <= 7 THEN 2 WHEN f.delay_days <= 14 THEN 3 WHEN f.delay_days > 14 THEN 4 END AS delay_band
FROM order_fact f
LEFT JOIN order_primary_category p USING (order_id)
LEFT JOIN raw_product_category_name_translation t ON t.product_category_name = p.category_key
LEFT JOIN order_seller_fact s ON s.order_id = f.order_id AND s.is_single_seller_order;

CREATE TEMP VIEW monthly_delivery AS
SELECT purchase_month, count(*) AS orders,
       count(*) FILTER (WHERE order_status = 'delivered') AS delivered,
       count(is_delayed) AS eligible, count(*) FILTER (WHERE is_delayed) AS late,
       avg(is_delayed::INT) AS late_rate,
       median(delay_days) FILTER (WHERE is_delayed) AS late_days_p50
FROM analysis_orders GROUP BY 1;

CREATE TEMP VIEW state_delivery AS
SELECT customer_state, count(is_delayed) AS eligible, count(*) FILTER (WHERE is_delayed) AS late,
       avg(is_delayed::INT) AS late_rate
FROM analysis_orders GROUP BY 1;

CREATE TEMP VIEW primary_category_delivery AS
SELECT category_key, category, count(is_delayed) AS eligible, count(*) FILTER (WHERE is_delayed) AS late,
       avg(is_delayed::INT) AS late_rate
FROM analysis_orders GROUP BY 1, 2;

CREATE TEMP VIEW stage_delivery AS
SELECT is_delayed AS delayed, s.stage, count(*) AS orders,
       quantile_cont(s.days, [.10, .25, .50, .75, .90]) AS quantiles
FROM analysis_orders
CROSS JOIN LATERAL (
    VALUES ('Purchase to carrier', purchase_to_carrier_days),
           ('Carrier to delivery', carrier_to_delivery_days)
) s(stage, days)
WHERE valid_phases GROUP BY 1, 2;

CREATE TEMP VIEW peak_orders AS
SELECT *, CASE WHEN purchase_month IN (DATE '2017-11-01', DATE '2018-02-01', DATE '2018-03-01')
               THEN purchase_month::VARCHAR ELSE 'Other mature months' END AS comparison
FROM analysis_orders WHERE mature AND is_delayed IS NOT NULL;

CREATE TEMP VIEW peak_comparison AS
SELECT comparison, count(*) AS eligible, sum(is_delayed::INT) AS late, avg(is_delayed::INT) AS late_rate,
       count(*) FILTER (WHERE valid_phases) AS stage_n,
       median(estimated_delivery_days) AS promised_p50_days,
       median(delivery_days) AS actual_p50_days,
       median(purchase_to_carrier_days) FILTER (WHERE valid_phases) AS handoff_p50_days,
       quantile_cont(purchase_to_carrier_days, .9) FILTER (WHERE valid_phases) AS handoff_p90_days,
       median(carrier_to_delivery_days) FILTER (WHERE valid_phases) AS transit_p50_days,
       quantile_cont(carrier_to_delivery_days, .9) FILTER (WHERE valid_phases) AS transit_p90_days
FROM peak_orders GROUP BY 1;

CREATE TEMP VIEW peak_state AS
WITH split AS (
    SELECT comparison, customer_state, count(*) AS eligible, sum(is_delayed::INT) AS late
    FROM peak_orders GROUP BY 1, 2
), reference AS (
    SELECT customer_state, late::DOUBLE / eligible AS baseline
    FROM split WHERE comparison = 'Other mature months'
)
SELECT s.*, s.late::DOUBLE / s.eligible AS late_rate, r.baseline,
       s.eligible * r.baseline AS expected_at_reference_mix,
       s.late - s.eligible * r.baseline AS excess
FROM split s LEFT JOIN reference r USING (customer_state);

CREATE TEMP VIEW peak_weekly AS
SELECT purchase_month, (1 + (day(purchase_timestamp) - 1) // 7) AS week_in_month,
       count(*) AS eligible, sum(is_delayed::INT) AS late, avg(is_delayed::INT) AS late_rate
FROM peak_orders
WHERE comparison <> 'Other mature months' GROUP BY 1, 2;

CREATE TEMP VIEW november_daily AS
SELECT purchase_timestamp::DATE AS purchase_day, count(*) AS eligible, sum(is_delayed::INT) AS late,
       avg(is_delayed::INT) AS late_rate
FROM peak_orders WHERE comparison = '2017-11-01' GROUP BY 1;
