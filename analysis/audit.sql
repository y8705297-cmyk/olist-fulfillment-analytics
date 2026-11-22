CREATE TEMP TABLE audit_orders AS
WITH source_orders AS (
    SELECT order_id, order_delivered_customer_date::DATE > order_estimated_delivery_date::DATE AS delayed
    FROM raw_orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date >= order_purchase_timestamp
      AND order_estimated_delivery_date >= order_purchase_timestamp
), source_sellers AS (
    SELECT order_id, min(seller_id) AS seller_id
    FROM raw_order_items GROUP BY order_id HAVING count(DISTINCT seller_id) = 1
)
SELECT o.*, s.seller_id, r.review_score
FROM source_orders o
LEFT JOIN source_sellers s USING (order_id)
LEFT JOIN LATERAL (
    SELECT review_score FROM raw_order_reviews r
    WHERE r.order_id = o.order_id
    ORDER BY review_answer_timestamp DESC NULLS LAST, review_creation_date DESC NULLS LAST,
             review_id DESC NULLS LAST, review_score DESC NULLS LAST LIMIT 1
) r ON TRUE;

CREATE TEMP VIEW audit_ratings AS
SELECT delayed, count(*) AS orders, count(review_score) AS rated,
       count(*) FILTER (WHERE review_score <= 2) AS low,
       avg((review_score <= 2)::INT) AS low_rate
FROM audit_orders GROUP BY delayed;

CREATE TEMP VIEW audit_seller AS
WITH counts AS (
    SELECT seller_id, count(*) AS eligible, sum(delayed::INT) AS late
    FROM audit_orders WHERE seller_id IS NOT NULL GROUP BY seller_id
), totals AS (
    SELECT *, sum(late) OVER ()::DOUBLE / sum(eligible) OVER () AS baseline FROM counts
)
SELECT *, eligible * greatest(0, (late - baseline * eligible) / (eligible + 50)) AS score
FROM totals;

CREATE TEMP VIEW audit_top10 AS
WITH volume AS (
    SELECT *, row_number() OVER (ORDER BY late DESC, seller_id) AS rank FROM audit_seller
), excess AS (
    SELECT *, row_number() OVER (ORDER BY score DESC, late DESC, seller_id) AS rank
    FROM audit_seller WHERE eligible >= 50 AND score > 0
)
SELECT 'late volume' AS selection, rank, seller_id, eligible, late, score FROM volume WHERE rank <= 10
UNION ALL
SELECT 'smoothed excess' AS selection, rank, seller_id, eligible, late, score FROM excess WHERE rank <= 10;
