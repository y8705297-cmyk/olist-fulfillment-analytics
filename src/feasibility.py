import duckdb
from scipy.stats import chi2_contingency
from scipy.stats.contingency import odds_ratio

from src.config import DB, REPORTS
from src.reporting import markdown_table, query_table, write_report

WINDOW = "purchase_timestamp >= DATE '2017-01-01' AND purchase_timestamp < DATE '2018-08-01'"


def associations(con):
    rows = []
    for label, restriction, low_cutoff in (
        ("全期", "TRUE", 2),
        ("2017-01 至 2018-07", WINDOW, 2),
        ("全期，改用评分 ≤ 3", "TRUE", 3),
    ):
        timely, late = con.execute(f"""
            SELECT count(*) FILTER (WHERE review_score <= {low_cutoff}),
                   count(*) FILTER (WHERE review_score > {low_cutoff})
            FROM order_fact
            WHERE is_delayed IS NOT NULL AND review_score BETWEEN 1 AND 5 AND ({restriction})
            GROUP BY is_delayed ORDER BY is_delayed
        """).fetchall()
        table = [late, timely]
        chi = chi2_contingency(table, correction=False)
        estimate = odds_ratio(table, kind="sample")
        interval = estimate.confidence_interval()
        p_value = "<1e-300" if chi.pvalue < 1e-300 else float(chi.pvalue)
        rows.append((label, sum(late), sum(timely), f"{late[0] / sum(late):.2%}",
                     f"{timely[0] / sum(timely):.2%}", estimate.statistic,
                     interval.low, interval.high, chi.statistic, p_value,
                     float(chi.expected_freq.min())))
    return markdown_table(
        ("样本", "延误有评", "未延误有评", "延误低评率", "未延误低评率", "OR",
         "95% CI 下限", "95% CI 上限", "χ²", "p", "最小期望频数"), rows
    )


def generate(con):
    sections = [
        "# 业务分析可行性验证",
        "下列结果由真实 Olist 数据运行生成。以订单下单月定义观察窗口。所有比例以 0–1 表示，带 % 的读数除外。",
        "## A. 履约表现",
        "总体与诊断切片可计算。对同一批具备有效全过程时间的订单，分别比较两个阶段的典型耗时。"
        "流程时间可定位需要排查的环节。责任界定还需要更细的物流事件和约定。",
        query_table(con, "SELECT * FROM business_kpis"),
        query_table(con, """
            SELECT count(*) FILTER (WHERE order_status = 'delivered' AND is_delayed IS NULL) AS delivered_excluded,
                   count(*) FILTER (WHERE is_delayed IS NOT NULL AND (carrier_timestamp IS NULL
                       OR carrier_timestamp < purchase_timestamp OR carrier_timestamp > delivered_timestamp)) AS bad_carrier_for_phases,
                   median(delay_days) AS p50_signed_days, quantile_cont(delay_days, 0.90) AS p90_signed_days,
                   min(delay_days) AS min_signed_days, max(delay_days) AS max_signed_days
            FROM order_fact
        """),
        query_table(con, """
            SELECT is_delayed, count(*) AS orders,
                   median(purchase_to_carrier_days) AS pre_carrier_p50_days,
                   quantile_cont(purchase_to_carrier_days, .9) AS pre_carrier_p90_days,
                   median(carrier_to_delivery_days) AS transit_p50_days,
                   quantile_cont(carrier_to_delivery_days, .9) AS transit_p90_days
            FROM order_fact
            WHERE is_delayed IS NOT NULL AND carrier_timestamp BETWEEN purchase_timestamp AND delivered_timestamp
            GROUP BY is_delayed ORDER BY is_delayed
        """),
        "按延误订单数列出前十个目的州和前十个品类。品类是订单触达口径，同一订单可能出现在多个品类。",
        query_table(con, "SELECT * FROM delivery_by_state ORDER BY late_orders DESC, customer_state LIMIT 10"),
        query_table(con, """
            SELECT category, eligible_orders, late_orders, late_rate FROM delivery_by_category
            ORDER BY late_orders DESC, category LIMIT 10
        """),
        "## B. 履约与客户体验",
        "样本支持 2×2 独立性诊断和简单二项回归。下表的样本 OR 等价于仅含延误标识的二项 Logit 系数取指数。"
        "χ² 和区间视订单为独立，正式推断须检验客户和商家聚类及月份、品类和地区混杂。"
        "低评率以有效评价订单为分母。缺评选择偏差和边界月份的截尾需要单独检查。",
        query_table(con, """
            SELECT is_delayed, count(*) AS orders, count(is_low_rating) AS rated,
                   count(is_low_rating)::DOUBLE / count(*) AS rating_coverage,
                   count(*) FILTER (WHERE review_score = 1) AS score_1,
                   count(*) FILTER (WHERE review_score = 2) AS score_2,
                   count(*) FILTER (WHERE review_score = 3) AS score_3,
                   count(*) FILTER (WHERE review_score = 4) AS score_4,
                   count(*) FILTER (WHERE review_score = 5) AS score_5
            FROM order_fact WHERE is_delayed IS NOT NULL GROUP BY 1 ORDER BY 1
        """),
        query_table(con, """
            WITH bands AS (
                SELECT *, CASE WHEN delay_days <= 0 THEN 0 WHEN delay_days <= 3 THEN 1
                               WHEN delay_days <= 7 THEN 2 WHEN delay_days <= 14 THEN 3 ELSE 4 END AS band
                FROM order_fact WHERE is_delayed IS NOT NULL
            )
            SELECT (['≤0', '1–3', '4–7', '8–14', '15+'])[band + 1] AS delay_days_band,
                   count(*) AS orders, count(is_low_rating) AS rated,
                   avg(is_low_rating::INT) AS low_rating_rate
            FROM bands GROUP BY band ORDER BY band
        """),
        associations(con),
        "主样本含完整快照。固定敏感性窗口覆盖 2017-01 至 2018-07 的下单月，避开起始低量和快照末端。"
        "快照没有明确记录各表抽取截止日。下表展示逐月分母和观察覆盖，供正式分析判断截尾影响。",
        query_table(con, """
            SELECT date_trunc('month', purchase_timestamp)::DATE AS month, count(*) AS orders,
                   count(is_delayed) AS delay_eligible,
                   count(is_delayed)::DOUBLE / count(*) AS delay_eligible_share,
                   count(is_low_rating) FILTER (WHERE is_delayed IS NOT NULL)::DOUBLE
                     / nullif(count(is_delayed), 0) AS eligible_rating_coverage,
                   avg(is_delayed::INT) AS late_rate
            FROM order_fact GROUP BY 1 ORDER BY 1
        """),
        "## C. 商家筛选与业务量",
        "候选排序适用于有至少 50 笔单卖家、可判延误订单的商家。"
        "基准为全量单卖家样本延误率，以 50 笔基准订单作为平滑权重。"
        "按平滑后高于基准的延误率差乘以样本量排序，同分按延误量和商家 ID。"
        "该分数衡量排查价值，实际执行前需结合分层覆盖和商家运营信息复核。",
        query_table(con, """
            SELECT (SELECT count(*) FROM raw_sellers) AS raw_sellers, count(*) AS active_sellers,
                   (SELECT count(*) FILTER (WHERE seller_count = 1) FROM order_fact) AS single_seller_orders,
                   (SELECT count(*) FROM order_fact WHERE seller_count > 0) AS seller_linked_orders,
                   (SELECT avg((seller_count = 1)::INT) FROM order_fact WHERE seller_count > 0) AS single_seller_share,
                   min(linked_orders) AS min_linked, median(linked_orders) AS p50_linked,
                   quantile_cont(linked_orders, .9) AS p90_linked, max(linked_orders) AS max_linked,
                   count(*) FILTER (WHERE eligible_orders >= 30) AS n_ge_30,
                   count(*) FILTER (WHERE eligible_orders >= 50) AS n_ge_50,
                   count(*) FILTER (WHERE eligible_orders >= 100) AS n_ge_100
            FROM seller_metrics
        """),
        query_table(con, """
            WITH ranked AS (
                SELECT *, row_number() OVER (ORDER BY late_orders DESC, seller_id) AS pos FROM seller_metrics
            )
            SELECT sum(late_orders) AS all_single_seller_late,
                   sum(late_orders) FILTER (WHERE pos <= 10) AS top10_late,
                   sum(late_orders) FILTER (WHERE pos <= 10)::DOUBLE / sum(late_orders) AS top10_share,
                   sum(late_orders) FILTER (WHERE pos <= 50)::DOUBLE / sum(late_orders) AS top50_share,
                   sum(late_orders) FILTER (WHERE eligible_orders >= 50)::DOUBLE / sum(late_orders) AS candidate_share
            FROM ranked
        """),
        "分层以目的州 × 主品类比较。主品类按订单商品行数最多的品类定义，同数按原葡语键升序。"
        "仅纳入至少有 50 笔其他商家可比订单的层。期望延误数用同层其他商家延误率乘以本商家同层订单数后加总。",
        query_table(con, """
            SELECT r.seller_id, r.seller_state, r.eligible_orders, r.late_orders, r.late_rate,
                   r.smoothed_rate, r.excess_late_orders,
                   m.covered_orders::DOUBLE / r.eligible_orders AS mix_coverage,
                   m.observed_late, m.expected_late, m.observed_late - m.expected_late AS mix_excess
            FROM seller_risk r LEFT JOIN seller_mix_adjusted m USING (seller_id)
            WHERE r.excess_late_orders > 0
            ORDER BY r.excess_late_orders DESC, r.late_orders DESC, r.seller_id LIMIT 10
        """),
        query_table(con, """
            SELECT customer_state, category_key, count(*) AS comparable_sellers,
                   sum(s.eligible_orders) AS eligible_orders, sum(s.late_orders) AS late_orders,
                   sum(s.late_orders)::DOUBLE / sum(s.eligible_orders) AS late_rate
            FROM seller_segments s JOIN seller_risk r USING (seller_id)
            GROUP BY customer_state, category_key HAVING sum(s.eligible_orders) >= 50
            ORDER BY late_orders DESC, customer_state, category_key LIMIT 10
        """),
        "## D. 优化情景",
        "示例组选平滑超额延误分数最高的十家正分商家。10% 与 20% 指相对基线延误率下降。"
        "订单量与组合固定时，减少延误期望数等于样本内基线延误量乘改善比例。"
        "潜在减少的低评记录还乘全平台可判延误订单评价覆盖率及其有评人群低评率差。"
        "该扩展假设迁移订单保持相同评价覆盖率，且所观察到的低评率差可迁移。这是统计关联情景。",
        query_table(con, """
            WITH target AS (
                SELECT * FROM seller_risk WHERE excess_late_orders > 0
                ORDER BY excess_late_orders DESC, late_orders DESC, seller_id LIMIT 10
            ), cohort AS (
                SELECT count(*) AS sellers, sum(eligible_orders) AS baseline_orders,
                       sum(late_orders) AS baseline_late FROM target
            ), association AS (
                SELECT count(is_low_rating)::DOUBLE / count(*) AS review_coverage,
                       avg(is_low_rating::INT) FILTER (WHERE is_delayed)
                       - avg(is_low_rating::INT) FILTER (WHERE NOT is_delayed) AS low_rating_gap
                FROM order_fact WHERE is_delayed IS NOT NULL
            )
            SELECT reduction AS relative_improvement, cohort.*, review_coverage, low_rating_gap,
                   baseline_late::DOUBLE / baseline_orders * (1 - reduction) AS scenario_late_rate,
                   baseline_late * reduction AS fewer_late_orders,
                   baseline_late * reduction * review_coverage * low_rating_gap AS fewer_low_rating_records
            FROM cohort CROSS JOIN association CROSS JOIN (VALUES (.10), (.20)) AS scenarios(reduction)
            ORDER BY reduction
        """),
    ]
    write_report(REPORTS / "feasibility_assessment.md", sections)


if __name__ == "__main__":
    with duckdb.connect(str(DB), read_only=True) as connection:
        generate(connection)
