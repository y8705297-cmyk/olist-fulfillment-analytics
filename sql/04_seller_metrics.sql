CREATE VIEW seller_metrics AS
SELECT seller_id, seller_state, count(*) AS linked_orders,
       count(*) FILTER (WHERE is_single_seller_order) AS single_seller_orders,
       count(DISTINCT customer_state) AS customer_states,
       sum(item_count) AS item_count, sum(item_value) AS item_value, sum(freight_value) AS freight_value,
       count(is_delayed) AS eligible_orders, count(*) FILTER (WHERE is_delayed) AS late_orders,
       avg(is_delayed::INT) AS late_rate
FROM order_seller_fact GROUP BY seller_id, seller_state;

CREATE VIEW seller_risk AS
WITH benchmark AS (
    SELECT sum(late_orders)::DOUBLE / nullif(sum(eligible_orders), 0) AS baseline
    FROM seller_metrics
), estimates AS (
    SELECT s.*, b.baseline,
           (s.late_orders + 50 * b.baseline) / (s.eligible_orders + 50) AS smoothed_rate
    FROM seller_metrics s CROSS JOIN benchmark b
    WHERE s.eligible_orders >= 50
)
SELECT *, greatest(0, (smoothed_rate - baseline) * eligible_orders) AS excess_late_orders
FROM estimates;

-- Give each order one category for seller mix comparisons.
CREATE VIEW order_primary_category AS
SELECT i.order_id, coalesce(p.product_category_name, '(unknown)') AS category_key
FROM raw_order_items i
LEFT JOIN raw_products p USING (product_id)
GROUP BY i.order_id, p.product_category_name
QUALIFY row_number() OVER (
    PARTITION BY i.order_id ORDER BY count(*) DESC, p.product_category_name ASC NULLS LAST
) = 1;

CREATE VIEW seller_segments AS
SELECT s.seller_id, s.customer_state, c.category_key,
       count(*) AS eligible_orders, count(*) FILTER (WHERE s.is_delayed) AS late_orders
FROM order_seller_fact s
JOIN order_primary_category c USING (order_id)
WHERE s.is_delayed IS NOT NULL
GROUP BY s.seller_id, s.customer_state, c.category_key;

CREATE VIEW seller_mix_adjusted AS
WITH strata AS (
    SELECT customer_state, category_key, sum(eligible_orders) AS stratum_n, sum(late_orders) AS stratum_late
    FROM seller_segments GROUP BY customer_state, category_key
)
SELECT s.seller_id, sum(s.eligible_orders) AS covered_orders, sum(s.late_orders) AS observed_late,
       sum(s.eligible_orders * (t.stratum_late - s.late_orders)::DOUBLE
           / nullif(t.stratum_n - s.eligible_orders, 0)) AS expected_late
FROM seller_segments s
JOIN strata t ON t.customer_state IS NOT DISTINCT FROM s.customer_state
             AND t.category_key = s.category_key
WHERE t.stratum_n - s.eligible_orders >= 50
GROUP BY s.seller_id;
