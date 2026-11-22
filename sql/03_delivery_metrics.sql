CREATE VIEW delivery_by_state AS
SELECT customer_state, count(is_delayed) AS eligible_orders,
       count(*) FILTER (WHERE is_delayed) AS late_orders, avg(is_delayed::INT) AS late_rate
FROM order_fact GROUP BY customer_state;

CREATE VIEW delivery_by_category AS
SELECT c.category_key, c.category, count(o.is_delayed) AS eligible_orders,
       count(*) FILTER (WHERE o.is_delayed) AS late_orders, avg(o.is_delayed::INT) AS late_rate
FROM order_category c JOIN order_fact o USING (order_id)
GROUP BY c.category_key, c.category;
