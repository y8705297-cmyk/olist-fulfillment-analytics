import unittest

import duckdb

from src.config import DB, KEYS, TABLES
from src.validate_data import TIME_RULES


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = duckdb.connect(str(DB), read_only=True)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def row(self, sql):
        return self.con.execute(sql).fetchone()

    def assert_empty(self, query):
        count, = self.row(f"SELECT count(*) FROM ({query}) AS violations")
        self.assertEqual(count, 0, f"{count} violations in {query}")

    def test_raw_model_input_keys(self):
        for name in TABLES:
            if name in {"order_reviews", "geolocation"}:
                continue
            with self.subTest(table=name):
                key = KEYS[name]
                null_keys = " OR ".join(f"{column} IS NULL" for column in key.split(", "))
                self.assert_empty(f"SELECT 1 FROM raw_{name} WHERE {null_keys}")
                self.assert_empty(f"SELECT {key} FROM raw_{name} GROUP BY {key} HAVING count(*) > 1")

    def test_order_key(self):
        self.assert_empty("SELECT order_id FROM order_fact GROUP BY order_id HAVING order_id IS NULL OR count(*) > 1")

    def test_same_order_ids_as_source(self):
        self.assertEqual(self.row("SELECT count(*) FROM order_fact"), self.row("SELECT count(*) FROM raw_orders"))
        for source, target in (("raw_orders", "order_fact"), ("order_fact", "raw_orders")):
            self.assert_empty(f"SELECT order_id FROM {source} EXCEPT SELECT order_id FROM {target}")

    def test_order_seller_key_and_coverage(self):
        self.assert_empty("""
            SELECT order_id, seller_id FROM order_seller_fact GROUP BY 1, 2
            HAVING order_id IS NULL OR seller_id IS NULL OR count(*) > 1
        """)
        self.assert_empty("SELECT order_id, seller_id FROM raw_order_items EXCEPT SELECT order_id, seller_id FROM order_seller_fact")
        self.assert_empty("SELECT order_id, seller_id FROM order_seller_fact EXCEPT SELECT order_id, seller_id FROM raw_order_items")

    def test_time_anomalies_remain_visible(self):
        aliases = {
            "order_purchase_timestamp": "purchase_timestamp",
            "order_approved_at": "approved_timestamp",
            "order_delivered_carrier_date": "carrier_timestamp",
            "order_delivered_customer_date": "delivered_timestamp",
            "order_estimated_delivery_date": "estimated_delivery_timestamp",
        }
        for label, predicate in TIME_RULES:
            with self.subTest(rule=label):
                modeled = predicate
                for raw, alias in aliases.items():
                    modeled = modeled.replace(raw, alias)
                self.assertEqual(
                    self.row(f"SELECT count(*) FROM raw_orders WHERE {predicate}"),
                    self.row(f"SELECT count(*) FROM order_fact WHERE {modeled}"),
                )
        self.assert_empty("""
            SELECT * FROM order_fact
            WHERE least(delivery_days, estimated_delivery_days,
                        purchase_to_carrier_days, carrier_to_delivery_days) < 0
                OR (carrier_timestamp < purchase_timestamp AND
                    (purchase_to_carrier_days IS NOT NULL OR carrier_to_delivery_days IS NOT NULL))
                OR (delivered_timestamp < carrier_timestamp AND carrier_to_delivery_days IS NOT NULL)
        """)

    def test_no_negative_money(self):
        self.assert_empty("SELECT * FROM raw_order_items WHERE price < 0 OR freight_value < 0")
        self.assert_empty("SELECT * FROM raw_order_payments WHERE payment_value < 0")
        self.assert_empty("SELECT * FROM order_fact WHERE least(item_value, freight_value, payment_value) < 0")
        self.assert_empty("SELECT * FROM order_seller_fact WHERE least(item_value, freight_value) < 0")

    def test_review_scores_and_low_rating(self):
        self.assert_empty("SELECT * FROM raw_order_reviews WHERE review_score NOT BETWEEN 1 AND 5 OR review_score IS NULL")
        self.assert_empty("SELECT * FROM order_fact WHERE is_low_rating IS DISTINCT FROM (review_score <= 2)")

    def test_review_selection_and_counts(self):
        self.assert_empty("""
            SELECT o.order_id FROM order_fact o
            WHERE o.review_count <> (SELECT count(*) FROM raw_order_reviews r WHERE r.order_id = o.order_id)
            OR (o.review_id, o.review_score, o.review_creation_date, o.review_answer_timestamp)
               IS DISTINCT FROM coalesce((
                   SELECT (r.review_id, r.review_score, r.review_creation_date, r.review_answer_timestamp)
                   FROM raw_order_reviews r WHERE r.order_id = o.order_id
                   ORDER BY r.review_answer_timestamp DESC NULLS LAST, r.review_creation_date DESC NULLS LAST,
                            r.review_id DESC NULLS LAST, r.review_score DESC NULLS LAST LIMIT 1
               ), (NULL, NULL, NULL, NULL))
        """)

    def test_delay_flags_and_day_differences(self):
        self.assert_empty("""
            SELECT * FROM order_fact
            WHERE is_delayed IS DISTINCT FROM (delay_days > 0)
               OR (delay_days IS NOT NULL AND delay_days <>
                   (CAST(delivered_timestamp AS DATE) - CAST(estimated_delivery_timestamp AS DATE)))
        """)
        self.assert_empty("""
            SELECT o.order_id FROM raw_orders o JOIN order_fact f USING (order_id)
            WHERE f.is_delayed IS DISTINCT FROM CASE WHEN o.order_status = 'delivered'
                    AND o.order_delivered_customer_date >= o.order_purchase_timestamp
                    AND o.order_estimated_delivery_date >= o.order_purchase_timestamp
                THEN CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE) END
        """)

    def test_seller_attribution(self):
        self.assert_empty("""
            SELECT o.order_id FROM order_fact o
            WHERE o.seller_count <> (SELECT count(DISTINCT seller_id) FROM raw_order_items i WHERE i.order_id = o.order_id)
        """)
        self.assert_empty("""
            SELECT s.order_id FROM order_seller_fact s JOIN order_fact f USING (order_id)
            WHERE s.is_single_seller_order IS DISTINCT FROM (f.seller_count = 1)
               OR (s.is_delayed, s.delay_days, s.review_score, s.is_low_rating) IS DISTINCT FROM
                   CASE WHEN f.seller_count = 1 THEN (f.is_delayed, f.delay_days, f.review_score, f.is_low_rating)
                        ELSE (NULL, NULL, NULL, NULL) END
        """)

    def test_item_and_payment_reconciliation_per_order(self):
        self.assert_empty("""
            SELECT order_id FROM order_fact o WHERE
                (item_count, item_value, freight_value) IS DISTINCT FROM
                    (SELECT (count(*), sum(price), sum(freight_value)) FROM raw_order_items i WHERE i.order_id = o.order_id)
                OR (payment_count, payment_value) IS DISTINCT FROM
                    (SELECT (count(*), sum(payment_value)) FROM raw_order_payments p WHERE p.order_id = o.order_id)
        """)

    def test_item_money_and_volume_reconcile_across_grains(self):
        expected = self.row("SELECT count(*), sum(price), sum(freight_value) FROM raw_order_items")
        for name in ("order_fact", "order_seller_fact"):
            self.assertEqual(expected, self.row(f"SELECT sum(item_count), sum(item_value), sum(freight_value) FROM {name}"))
        self.assertEqual(self.row("SELECT sum(payment_value) FROM order_fact"),
                         self.row("SELECT sum(payment_value) FROM raw_order_payments"))

    def test_business_kpis_from_raw_orders(self):
        totals = self.row("""
            WITH eligible AS (
                SELECT order_delivered_customer_date AS actual, order_estimated_delivery_date AS promised
                FROM raw_orders WHERE order_status = 'delivered'
                AND order_delivered_customer_date >= order_purchase_timestamp
                AND order_estimated_delivery_date >= order_purchase_timestamp
            )
            SELECT (SELECT count(*) FROM raw_orders),
                   (SELECT count(*) FROM raw_orders WHERE order_status = 'delivered'),
                   count(*), count(*) FILTER (WHERE actual::DATE > promised::DATE),
                   avg((actual::DATE > promised::DATE)::INT)
            FROM eligible
        """)
        self.assertEqual(totals, self.row("SELECT orders, delivered_status_orders, delay_eligible, delayed, delay_rate FROM business_kpis"))
        item_value, freight_value, average = self.row("""
            SELECT sum(items), sum(freight), avg(items)
            FROM (SELECT sum(price) items, sum(freight_value) freight FROM raw_order_items GROUP BY order_id)
        """)
        self.assertEqual((item_value, freight_value, average), self.row(
            "SELECT item_value, freight_value, average_order_item_value FROM business_kpis"
        ))

    def test_category_keys(self):
        self.assert_empty("SELECT order_id, category_key FROM order_category GROUP BY 1, 2 HAVING count(*) > 1")
        self.assert_empty("SELECT order_id FROM order_primary_category GROUP BY 1 HAVING count(*) > 1")
        self.assert_empty("SELECT order_id FROM raw_order_items EXCEPT SELECT order_id FROM order_primary_category")

    def test_seller_segments_reconcile(self):
        self.assert_empty("""
            SELECT m.seller_id FROM seller_metrics m
            LEFT JOIN (
                SELECT seller_id, sum(eligible_orders) eligible, sum(late_orders) late
                FROM seller_segments GROUP BY seller_id
            ) s USING (seller_id)
            WHERE m.eligible_orders <> coalesce(s.eligible, 0) OR m.late_orders <> coalesce(s.late, 0)
        """)
        self.assert_empty("""
            SELECT r.seller_id FROM seller_risk r LEFT JOIN seller_mix_adjusted m USING (seller_id)
            WHERE r.eligible_orders < 50 OR m.covered_orders > r.eligible_orders
               OR m.observed_late > r.late_orders OR m.expected_late NOT BETWEEN 0 AND m.covered_orders
        """)
