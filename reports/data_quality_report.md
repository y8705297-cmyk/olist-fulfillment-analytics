# Olist 原始数据质量检查

以下计数基于已加载的原始表，保留源数据异常。邮编前缀是地理观测的分组键。评价候选键为评价 ID 与订单 ID 的组合。

Kaggle v2，版本 ID 2669146。官方归档 SHA-256 为 `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`。[固定版本下载](https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce?datasetVersionNumber=2)

## 文件指纹

| CSV | SHA-256 |
| --- | --- |
| olist_orders_dataset.csv | 8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf |
| olist_order_items_dataset.csv | 0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279 |
| olist_customers_dataset.csv | 983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2 |
| olist_sellers_dataset.csv | 1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e |
| olist_products_dataset.csv | 3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc |
| olist_order_reviews_dataset.csv | 012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7 |
| olist_order_payments_dataset.csv | 4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0 |
| olist_geolocation_dataset.csv | b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6 |
| product_category_name_translation.csv | a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278 |

## 原始表与键

| 表 | 行数 | 键 | 空键行 | 重复键组 | 重复键额外行 | 完全重复额外行 |
| --- | --- | --- | --- | --- | --- | --- |
| orders | 99441 | order_id | 0 | 0 | 0 | 0 |
| order_items | 112650 | order_id, order_item_id | 0 | 0 | 0 | 0 |
| customers | 99441 | customer_id | 0 | 0 | 0 | 0 |
| sellers | 3095 | seller_id | 0 | 0 | 0 | 0 |
| products | 32951 | product_id | 0 | 0 | 0 | 0 |
| order_reviews | 99224 | review_id, order_id | 0 | 0 | 0 | 0 |
| order_payments | 103886 | order_id, payment_sequential | 0 | 0 | 0 | 0 |
| geolocation | 1000163 | geolocation_zip_code_prefix | 0 | 17972 | 981148 | 261831 |
| product_category_name_translation | 71 | product_category_name | 0 | 0 | 0 | 0 |

## 外键覆盖

| 关联 | 非空引用 | 空引用 | 非空未匹配 | 非空匹配率 |
| --- | --- | --- | --- | --- |
| orders.customer_id → customers.customer_id | 99441 | 0 | 0 | 100.00% |
| order_items.order_id → orders.order_id | 112650 | 0 | 0 | 100.00% |
| order_items.seller_id → sellers.seller_id | 112650 | 0 | 0 | 100.00% |
| order_items.product_id → products.product_id | 112650 | 0 | 0 | 100.00% |
| order_reviews.order_id → orders.order_id | 99224 | 0 | 0 | 100.00% |
| order_payments.order_id → orders.order_id | 103886 | 0 | 0 | 100.00% |
| products.product_category_name → product_category_name_translation.product_category_name | 32341 | 610 | 13 | 99.96% |
| customers.customer_zip_code_prefix → geolocation.geolocation_zip_code_prefix | 99441 | 0 | 278 | 99.72% |
| sellers.seller_zip_code_prefix → geolocation.geolocation_zip_code_prefix | 3095 | 0 | 7 | 99.77% |

## 状态与一对多

| order_status | orders |
| --- | --- |
| delivered | 96478 |
| shipped | 1107 |
| canceled | 625 |
| unavailable | 609 |
| invoiced | 314 |
| processing | 301 |
| created | 5 |
| approved | 2 |

| 检查项 | 超过 1 的分组数 | 单组最大记录数 |
| --- | --- | --- |
| 多卖家订单 | 1278 | 5 |
| 多商品行订单 | 9803 | 21 |
| 多评价订单 | 547 | 3 |
| 重复评价 ID | 789 | 3 |
| 多支付订单 | 2961 | 29 |

## 异常与合理性

| 检查项 | 行数 |
| --- | --- |
| 审批早于下单 | 0 |
| 交承运方早于下单 | 166 |
| 交承运方早于审批 | 1359 |
| 签收早于下单 | 0 |
| 签收早于交承运方 | 23 |
| 预计送达早于下单 | 0 |
| delivered 缺实际签收 | 8 |
| 非 delivered 有签收时间 | 6 |
| 商品负价 | 0 |
| 零商品价 | 0 |
| 负运费 | 0 |
| 零运费 | 383 |
| 负支付额 | 0 |
| 零支付额 | 9 |
| 零支付期数 | 2 |
| 评分越界或缺失 | 0 |
| 评价答复早于创建 | 0 |
| 商品重量为零 | 4 |
| 负商品重量或尺寸 | 0 |
| 经纬度超出全球范围 | 0 |
| 经纬度超出巴西粗略范围 | 31 |

| interval | n | p99 | maximum |
| --- | --- | --- | --- |
| 下单到签收 | 96470 | 46.05 | 209.63 |
| 下单到承运方 | 97492 | 17.822 | 125.78 |
| 承运方到签收 | 96281 | 40.989 | 205.19 |

| orders_with_both | payment_differs | max_absolute_diff_brl |
| --- | --- | --- |
| 98665 | 576 | 182.81 |

## 分析对象行数

| 对象 | 行数 |
| --- | --- |
| order_fact | 99441 |
| order_seller_fact | 100010 |
| order_category | 99470 |
| order_primary_category | 98666 |

| no_items | no_payments | no_reviews |
| --- | --- | --- |
| 775 | 1 | 768 |

## 各列类型、空值与范围

### orders

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| order_id | VARCHAR | 0 | — | — |
| customer_id | VARCHAR | 0 | — | — |
| order_status | VARCHAR | 0 | — | — |
| order_purchase_timestamp | TIMESTAMP | 0 | 2016-09-04 21:15:19 | 2018-10-17 17:30:18 |
| order_approved_at | TIMESTAMP | 160 | 2016-09-15 12:16:38 | 2018-09-03 17:40:06 |
| order_delivered_carrier_date | TIMESTAMP | 1783 | 2016-10-08 10:34:01 | 2018-09-11 19:48:28 |
| order_delivered_customer_date | TIMESTAMP | 2965 | 2016-10-11 13:46:32 | 2018-10-17 13:22:46 |
| order_estimated_delivery_date | TIMESTAMP | 0 | 2016-09-30 00:00:00 | 2018-11-12 00:00:00 |

### order_items

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| order_id | VARCHAR | 0 | — | — |
| order_item_id | INTEGER | 0 | 1 | 21 |
| product_id | VARCHAR | 0 | — | — |
| seller_id | VARCHAR | 0 | — | — |
| shipping_limit_date | TIMESTAMP | 0 | 2016-09-19 00:15:34 | 2020-04-09 22:35:08 |
| price | DECIMAL(18,2) | 0 | 0.85 | 6,735.00 |
| freight_value | DECIMAL(18,2) | 0 | 0.00 | 409.68 |

### customers

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| customer_id | VARCHAR | 0 | — | — |
| customer_unique_id | VARCHAR | 0 | — | — |
| customer_zip_code_prefix | VARCHAR | 0 | — | — |
| customer_city | VARCHAR | 0 | — | — |
| customer_state | VARCHAR | 0 | — | — |

### sellers

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| seller_id | VARCHAR | 0 | — | — |
| seller_zip_code_prefix | VARCHAR | 0 | — | — |
| seller_city | VARCHAR | 0 | — | — |
| seller_state | VARCHAR | 0 | — | — |

### products

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| product_id | VARCHAR | 0 | — | — |
| product_category_name | VARCHAR | 610 | — | — |
| product_name_lenght | INTEGER | 610 | 5 | 76 |
| product_description_lenght | INTEGER | 610 | 4 | 3992 |
| product_photos_qty | INTEGER | 610 | 1 | 20 |
| product_weight_g | INTEGER | 2 | 0 | 40425 |
| product_length_cm | INTEGER | 2 | 7 | 105 |
| product_height_cm | INTEGER | 2 | 2 | 105 |
| product_width_cm | INTEGER | 2 | 6 | 118 |

### order_reviews

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| review_id | VARCHAR | 0 | — | — |
| order_id | VARCHAR | 0 | — | — |
| review_score | INTEGER | 0 | 1 | 5 |
| review_comment_title | VARCHAR | 87656 | — | — |
| review_comment_message | VARCHAR | 58247 | — | — |
| review_creation_date | TIMESTAMP | 0 | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 |
| review_answer_timestamp | TIMESTAMP | 0 | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 |

### order_payments

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| order_id | VARCHAR | 0 | — | — |
| payment_sequential | INTEGER | 0 | 1 | 29 |
| payment_type | VARCHAR | 0 | — | — |
| payment_installments | INTEGER | 0 | 0 | 24 |
| payment_value | DECIMAL(18,2) | 0 | 0.00 | 13,664.08 |

### geolocation

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| geolocation_zip_code_prefix | VARCHAR | 0 | — | — |
| geolocation_lat | DOUBLE | 0 | -36.605 | 45.066 |
| geolocation_lng | DOUBLE | 0 | -101.47 | 121.11 |
| geolocation_city | VARCHAR | 0 | — | — |
| geolocation_state | VARCHAR | 0 | — | — |

### product_category_name_translation

| 列名 | 载入类型 | 缺失 | 最小 | 最大 |
| --- | --- | --- | --- | --- |
| product_category_name | VARCHAR | 0 | — | — |
| product_category_name_english | VARCHAR | 0 | — | — |
