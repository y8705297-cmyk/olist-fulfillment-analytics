from src.config import ROOT


def audit(con):
    con.execute((ROOT / "analysis" / "audit.sql").read_text())
    checks = {
        "Order fact grain": """
            SELECT count(*), count(DISTINCT order_id), (SELECT count(*) FROM raw_orders)
            FROM order_fact
        """,
        "Order-seller fact grain": """
            SELECT count(*), count(DISTINCT (order_id, seller_id)),
              (SELECT count(DISTINCT (order_id, seller_id)) FROM raw_order_items)
            FROM order_seller_fact
        """,
        "Eligibility and late flags": """
            SELECT count(*) FROM audit_orders a FULL JOIN
                (SELECT order_id, is_delayed, review_score FROM order_fact WHERE is_delayed IS NOT NULL) f
                USING (order_id)
            WHERE a.delayed IS DISTINCT FROM f.is_delayed OR a.review_score IS DISTINCT FROM f.review_score
        """,
        "Seller priority": """
            SELECT count(*) FROM (SELECT * FROM audit_seller WHERE eligible >= 50) a
                FULL JOIN seller_risk s USING (seller_id)
            WHERE a.eligible IS DISTINCT FROM s.eligible_orders OR a.late IS DISTINCT FROM s.late_orders
                OR abs(a.score - s.excess_late_orders) > 1e-9
        """,
    }
    results = {label: con.execute(sql).fetchone() for label, sql in checks.items()}
    expected = {
        "Order fact grain": (99441, 99441, 99441),
        "Order-seller fact grain": (100010, 100010, 100010),
        "Eligibility and late flags": (0,),
        "Seller priority": (0,),
    }
    if results != expected:
        raise AssertionError(f"Raw audit mismatch: {results}")
    raw_ratings = con.execute("SELECT * FROM audit_ratings ORDER BY delayed").fetchall()
    if [row[1:4] for row in raw_ratings] != [(89936, 89443, 8289), (6534, 6381, 3983)]:
        raise AssertionError(f"Unexpected raw rating results: {raw_ratings}")
    top = con.execute("SELECT selection, sum(late) FROM audit_top10 GROUP BY 1 ORDER BY 1").fetchall()
    if top != [("late volume", 1019), ("smoothed excess", 906)]:
        raise AssertionError(f"Unexpected Top 10 totals: {top}")
    print(f"Raw audit: {results}\nRatings: {raw_ratings}\nTop 10 totals: {top}", flush=True)


if __name__ == "__main__":
    import duckdb

    from src.config import DB

    with duckdb.connect(str(DB), read_only=True) as connection:
        audit(connection)
