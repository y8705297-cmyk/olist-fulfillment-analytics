import json

import duckdb

from src.config import DB, KEYS, RAW, REFERENCES, REPORTS, SNAPSHOT, SOURCE, VERSION
from src.fetch_data import verify_csvs
from src.reporting import markdown_table, query_table, write_report

TIME_RULES = (
    ("审批早于下单", "order_approved_at < order_purchase_timestamp"),
    ("交承运方早于下单", "order_delivered_carrier_date < order_purchase_timestamp"),
    ("交承运方早于审批", "order_delivered_carrier_date < order_approved_at"),
    ("签收早于下单", "order_delivered_customer_date < order_purchase_timestamp"),
    ("签收早于交承运方", "order_delivered_customer_date < order_delivered_carrier_date"),
    ("预计送达早于下单", "order_estimated_delivery_date < order_purchase_timestamp"),
    ("delivered 缺实际签收", "order_status = 'delivered' AND order_delivered_customer_date IS NULL"),
    ("非 delivered 有签收时间", "order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL"),
)
OTHER_RULES = (
    ("商品负价", "order_items", "price < 0"),
    ("零商品价", "order_items", "price = 0"),
    ("负运费", "order_items", "freight_value < 0"),
    ("零运费", "order_items", "freight_value = 0"),
    ("负支付额", "order_payments", "payment_value < 0"),
    ("零支付额", "order_payments", "payment_value = 0"),
    ("零支付期数", "order_payments", "payment_installments = 0"),
    ("评分越界或缺失", "order_reviews", "review_score NOT BETWEEN 1 AND 5 OR review_score IS NULL"),
    ("评价答复早于创建", "order_reviews", "review_answer_timestamp < review_creation_date"),
    ("商品重量为零", "products", "product_weight_g = 0"),
    ("负商品重量或尺寸", "products", "least(product_weight_g, product_length_cm, product_width_cm, product_height_cm) < 0"),
    ("经纬度超出全球范围", "geolocation", "abs(geolocation_lat) > 90 OR abs(geolocation_lng) > 180"),
    ("经纬度超出巴西粗略范围", "geolocation",
     "geolocation_lat NOT BETWEEN -34 AND 6 OR geolocation_lng NOT BETWEEN -74 AND -28"),
)


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def generate(con):
    sections = [
        "# Olist 原始数据质量检查",
        "以下计数基于已加载的原始表，保留源数据异常。邮编前缀是地理观测的分组键。评价候选键为评价 ID 与订单 ID 的组合。",
    ]
    snapshot = json.loads(SNAPSHOT.read_text())
    fingerprints = verify_csvs(RAW)
    sections += [
        (f"Kaggle v{VERSION}，版本 ID {snapshot['kaggle_version_id']}。"
         f"官方归档 SHA-256 为 `{snapshot['archive_sha256']}`。"
         f"[固定版本下载]({SOURCE})"),
        "## 文件指纹",
        markdown_table(("CSV", "SHA-256"), fingerprints.items()),
    ]
    key_rows, column_sections = [], []
    for table, key in KEYS.items():
        raw = f"raw_{table}"
        missing_key = " OR ".join(f"{column} IS NULL" for column in key.split(", "))
        count, null_keys = con.execute(f"SELECT count(*), count(*) FILTER (WHERE {missing_key}) FROM {raw}").fetchone()
        groups, excess = con.execute(f"""
            SELECT count(*), coalesce(sum(n - 1), 0)
            FROM (SELECT count(*) n FROM {raw} GROUP BY {key} HAVING count(*) > 1)
        """).fetchone()
        distinct_rows = scalar(con, f"SELECT count(*) FROM (SELECT DISTINCT * FROM {raw})")
        key_rows.append((table, count, key, null_keys, groups, excess, count - distinct_rows))
        profile = []
        for column, kind, *_ in con.execute(f"DESCRIBE {raw}").fetchall():
            quoted = '"' + column.replace('"', '""') + '"'
            ranges = f", min({quoted}), max({quoted})" if kind != "VARCHAR" else ", NULL, NULL"
            values = con.execute(f"SELECT count(*) - count({quoted}) {ranges} FROM {raw}").fetchone()
            profile.append((column, kind, *values))
        column_sections += [f"### {table}", markdown_table(("列名", "载入类型", "缺失", "最小", "最大"), profile)]
    sections += [
        "## 原始表与键",
        markdown_table(("表", "行数", "键", "空键行", "重复键组", "重复键额外行", "完全重复额外行"), key_rows),
    ]
    links = []
    for child, key, parent, parent_key in REFERENCES:
        total, missing, unmatched = con.execute(f"""
            SELECT count(*), count(*) FILTER (WHERE c.{key} IS NULL),
                   count(*) FILTER (WHERE c.{key} IS NOT NULL AND NOT EXISTS (
                       SELECT 1 FROM raw_{parent} p WHERE p.{parent_key} = c.{key}
                   ))
            FROM raw_{child} c
        """).fetchone()
        base = total - missing
        links.append((f"{child}.{key} → {parent}.{parent_key}", base, missing, unmatched,
                      f"{(base - unmatched) / base:.2%}" if base else None))
    sections += [
        "## 外键覆盖",
        markdown_table(("关联", "非空引用", "空引用", "非空未匹配", "非空匹配率"), links),
        "## 状态与一对多",
        query_table(con, "SELECT order_status, count(*) AS orders FROM raw_orders GROUP BY 1 ORDER BY 2 DESC, 1"),
    ]
    multiplicity = []
    for label, table, expression in (
        ("多卖家订单", "order_items", "count(DISTINCT seller_id)"),
        ("多商品行订单", "order_items", "count(*)"),
        ("多评价订单", "order_reviews", "count(*)"),
        ("重复评价 ID", "order_reviews", "count(*)"),
        ("多支付订单", "order_payments", "count(*)"),
    ):
        key = "review_id" if label == "重复评价 ID" else "order_id"
        count, maximum = con.execute(f"""
            SELECT count(*) FILTER (WHERE n > 1), max(n)
            FROM (SELECT {expression} n FROM raw_{table} GROUP BY {key})
        """).fetchone()
        multiplicity.append((label, count, maximum))
    sections += [markdown_table(("检查项", "超过 1 的分组数", "单组最大记录数"), multiplicity), "## 异常与合理性"]
    anomaly_rows = [
        (label, scalar(con, f"SELECT count(*) FROM raw_{table} WHERE {predicate}"))
        for label, table, predicate in (*[(label, "orders", rule) for label, rule in TIME_RULES], *OTHER_RULES)
    ]
    sections += [
        markdown_table(("检查项", "行数"), anomaly_rows),
        query_table(con, """
            SELECT '下单到签收' AS interval, count(delivery_days) AS n,
                   quantile_cont(delivery_days, 0.99) AS p99, max(delivery_days) AS maximum
            FROM order_fact
            UNION ALL SELECT '下单到承运方', count(purchase_to_carrier_days),
                   quantile_cont(purchase_to_carrier_days, 0.99), max(purchase_to_carrier_days) FROM order_fact
            UNION ALL SELECT '承运方到签收', count(carrier_to_delivery_days),
                   quantile_cont(carrier_to_delivery_days, 0.99), max(carrier_to_delivery_days) FROM order_fact
        """),
        query_table(con, """
            SELECT count(*) FILTER (WHERE item_value IS NOT NULL AND payment_value IS NOT NULL) AS orders_with_both,
                   count(*) FILTER (WHERE item_value + freight_value <> payment_value) AS payment_differs,
                   max(abs(item_value + freight_value - payment_value)) AS max_absolute_diff_brl
            FROM order_fact
        """),
        "## 分析对象行数",
        markdown_table(("对象", "行数"), [
            (name, scalar(con, f"SELECT count(*) FROM {name}"))
            for name in ("order_fact", "order_seller_fact", "order_category", "order_primary_category")
        ]),
        query_table(con, """
            SELECT count(*) FILTER (WHERE item_count = 0) AS no_items,
                   count(*) FILTER (WHERE payment_count = 0) AS no_payments,
                   count(*) FILTER (WHERE review_count = 0) AS no_reviews
            FROM order_fact
        """),
        "## 各列类型、空值与范围",
        *column_sections,
    ]
    write_report(REPORTS / "data_quality_report.md", sections)


if __name__ == "__main__":
    with duckdb.connect(str(DB), read_only=True) as connection:
        generate(connection)
