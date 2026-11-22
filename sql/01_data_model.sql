CREATE TABLE order_fact AS
WITH items AS (
    SELECT order_id, count(*) AS item_count, count(DISTINCT seller_id) AS seller_count,
           sum(price) AS item_value, sum(freight_value) AS freight_value
    FROM raw_order_items GROUP BY order_id
), payments AS (
    SELECT order_id, count(*) AS payment_count, sum(payment_value) AS payment_value
    FROM raw_order_payments GROUP BY order_id
), reviews AS (
    SELECT order_id, review_score, review_id, review_creation_date, review_answer_timestamp,
           count(*) OVER (PARTITION BY order_id) AS review_count
    FROM raw_order_reviews
    QUALIFY row_number() OVER (
        PARTITION BY order_id
        ORDER BY review_answer_timestamp DESC NULLS LAST, review_creation_date DESC NULLS LAST,
                 review_id DESC NULLS LAST, review_score DESC NULLS LAST
    ) = 1
), orders AS (
    SELECT o.order_id, o.customer_id, c.customer_unique_id, c.customer_state,
           o.order_status, o.order_purchase_timestamp AS purchase_timestamp,
           o.order_approved_at AS approved_timestamp, o.order_delivered_carrier_date AS carrier_timestamp,
           o.order_delivered_customer_date AS delivered_timestamp,
           o.order_estimated_delivery_date AS estimated_delivery_timestamp,
           coalesce(i.item_count, 0) AS item_count, coalesce(i.seller_count, 0) AS seller_count,
           i.item_value, i.freight_value, coalesce(p.payment_count, 0) AS payment_count,
           p.payment_value, r.review_score, r.review_id, r.review_creation_date,
           r.review_answer_timestamp, coalesce(r.review_count, 0) AS review_count
    FROM raw_orders o
    LEFT JOIN raw_customers c USING (customer_id)
    LEFT JOIN items i USING (order_id)
    LEFT JOIN payments p USING (order_id)
    LEFT JOIN reviews r USING (order_id)
), eligible AS (
    SELECT *, order_status = 'delivered' AND purchase_timestamp IS NOT NULL
                  AND delivered_timestamp >= purchase_timestamp
                  AND estimated_delivery_timestamp >= purchase_timestamp AS valid_comparison
    FROM orders
)
SELECT * EXCLUDE (valid_comparison),
       CASE WHEN delivered_timestamp >= purchase_timestamp AND order_status = 'delivered'
            THEN epoch(delivered_timestamp - purchase_timestamp) / 86400 END AS delivery_days,
       CASE WHEN estimated_delivery_timestamp >= purchase_timestamp
            THEN epoch(estimated_delivery_timestamp - purchase_timestamp) / 86400 END AS estimated_delivery_days,
       CASE WHEN valid_comparison THEN datediff('day', estimated_delivery_timestamp, delivered_timestamp)
            END AS delay_days,
       CASE WHEN valid_comparison THEN delivered_timestamp::DATE > estimated_delivery_timestamp::DATE
            END AS is_delayed,
       CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score <= 2 END AS is_low_rating,
       CASE WHEN carrier_timestamp >= purchase_timestamp
            THEN epoch(carrier_timestamp - purchase_timestamp) / 86400 END AS purchase_to_carrier_days,
       CASE WHEN carrier_timestamp >= purchase_timestamp AND delivered_timestamp >= carrier_timestamp
                 AND order_status = 'delivered'
            THEN epoch(delivered_timestamp - carrier_timestamp) / 86400 END AS carrier_to_delivery_days
FROM eligible;

CREATE TABLE order_seller_fact AS
WITH seller_items AS (
    SELECT order_id, seller_id, count(*) AS item_count, sum(price) AS item_value,
           sum(freight_value) AS freight_value
    FROM raw_order_items GROUP BY order_id, seller_id
)
SELECT i.*, s.seller_state, o.customer_state, o.order_status, o.purchase_timestamp,
       o.seller_count = 1 AS is_single_seller_order,
       CASE WHEN o.seller_count = 1 THEN o.is_delayed END AS is_delayed,
       CASE WHEN o.seller_count = 1 THEN o.delay_days END AS delay_days,
       CASE WHEN o.seller_count = 1 THEN o.review_score END AS review_score,
       CASE WHEN o.seller_count = 1 THEN o.is_low_rating END AS is_low_rating
FROM seller_items i
JOIN order_fact o USING (order_id)
LEFT JOIN raw_sellers s USING (seller_id);

CREATE TABLE order_category AS
SELECT DISTINCT i.order_id, p.product_category_name AS category_key,
       coalesce(t.product_category_name_english, p.product_category_name, '(unknown)') AS category
FROM raw_order_items i
LEFT JOIN raw_products p USING (product_id)
LEFT JOIN raw_product_category_name_translation t USING (product_category_name);
