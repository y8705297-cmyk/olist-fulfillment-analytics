CREATE VIEW business_kpis AS
SELECT count(*) AS orders,
       count(*) FILTER (WHERE order_status = 'delivered') AS delivered_status_orders,
       avg((order_status = 'delivered')::INT) AS delivered_share,
       sum(item_value) AS item_value, sum(freight_value) AS freight_value,
       sum(payment_value) AS payment_value, avg(item_value) AS average_order_item_value,
       count(is_delayed) AS delay_eligible, count(*) FILTER (WHERE is_delayed) AS delayed,
       avg(is_delayed::INT) AS delay_rate,
       count(is_low_rating) AS rated_orders, avg(is_low_rating::INT) AS low_rating_rate,
       avg(delivery_days) AS mean_delivery_days,
       median(delay_days) FILTER (WHERE is_delayed) AS median_late_days
FROM order_fact;
