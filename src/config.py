from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB = PROCESSED / "olist.duckdb"
REPORTS = ROOT / "reports"
SLUG = "olistbr/brazilian-ecommerce"
VERSION = 2
SOURCE = f"https://www.kaggle.com/api/v1/datasets/download/{SLUG}?datasetVersionNumber={VERSION}"
SNAPSHOT = ROOT / "data" / "snapshot.json"
TABLES = {
    name: f"olist_{name}_dataset.csv"
    for name in (
        "orders", "order_items", "customers", "sellers", "products",
        "order_reviews", "order_payments", "geolocation",
    )
}
TABLES["product_category_name_translation"] = "product_category_name_translation.csv"

# Natural keys, or candidate keys to audit in the raw source.
KEYS = {
    "orders": "order_id",
    "order_items": "order_id, order_item_id",
    "customers": "customer_id",
    "sellers": "seller_id",
    "products": "product_id",
    "order_reviews": "review_id, order_id",
    "order_payments": "order_id, payment_sequential",
    "geolocation": "geolocation_zip_code_prefix",
    "product_category_name_translation": "product_category_name",
}
REFERENCES = (
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("products", "product_category_name", "product_category_name_translation", "product_category_name"),
    ("customers", "customer_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
    ("sellers", "seller_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
)
# Text IDs, numeric BRL and timestamps are typed explicitly during ingestion.
TABLE_TYPES = {
    "orders": {
        "order_purchase_timestamp": "TIMESTAMP", "order_approved_at": "TIMESTAMP",
        "order_delivered_carrier_date": "TIMESTAMP", "order_delivered_customer_date": "TIMESTAMP",
        "order_estimated_delivery_date": "TIMESTAMP",
    },
    "order_items": {"order_item_id": "INTEGER", "shipping_limit_date": "TIMESTAMP",
                    "price": "DECIMAL(18,2)", "freight_value": "DECIMAL(18,2)"},
    "order_reviews": {"review_score": "INTEGER", "review_creation_date": "TIMESTAMP",
                      "review_answer_timestamp": "TIMESTAMP"},
    "order_payments": {"payment_sequential": "INTEGER", "payment_installments": "INTEGER",
                       "payment_value": "DECIMAL(18,2)"},
    "products": dict.fromkeys(
        ("product_name_lenght", "product_description_lenght", "product_photos_qty",
         "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"), "INTEGER"
    ),
    "geolocation": {"geolocation_lat": "DOUBLE", "geolocation_lng": "DOUBLE"},
}
