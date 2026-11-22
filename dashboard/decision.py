import streamlit as st

from charts import concentration, forest, review_bars
from data import table
from labels import CATEGORY, ELIGIBLE, EXPERIENCE, LATE, LATE_ORDERS, LATE_RATE, ON_TIME, OR, SCENARIOS, SELLERS, STATE, category_name

MODEL_LABELS = {
    "Full snapshot, crude": "全量数据 · 未调整",
    "Mature window, crude": "成熟观察期 · 未调整",
    "Mature window, adjusted": "成熟观察期 · 已调整",
    "Mature window, customer-clustered": "已调整 · 按客户聚类",
    "Mature single seller, crude": "单商家订单 · 未调整",
    "Mature single seller, adjusted": "已调整 · 按商家聚类",
    "Mature excluding peaks, adjusted": "排除高峰月 · 已调整",
    "Mature score <= 3, adjusted": "低评分阈值 ≤3 分 · 已调整",
    "Full snapshot, adjusted": "全量数据 · 已调整",
}


def experience():
    st.title(EXPERIENCE)
    st.write("量化配送延误与低评分的统计关联。")
    st.caption("固定分析样本 · 描述性指标使用全量数据，主模型使用 2017 年 1 月至 2018 年 7 月的成熟观察期。")
    risks = table("review_risk_difference")
    main = risks.iloc[0]
    for col, (label, value) in zip(st.columns(3), (
        ("延误订单低评分率", f"{main.late_rate:.2%}"),
        ("按期订单低评分率", f"{main.timely_rate:.2%}"),
        ("低评分风险差", f"{main.risk_difference * 100:.2f} 个百分点"),
    )):
        col.metric(label, value, border=True)
    st.caption(f"低评分指评分不高于 2 分。延误组有 {int(main.late_n):,} 笔、按期组有 {int(main.timely_n):,} 笔有效评分订单。"
               f"按 Newcombe 方法估计的风险差 95% 置信区间为 {main.lower * 100:.2f}–{main.upper * 100:.2f} 个百分点。")
    rating, coverage = st.columns([1.5, 1])
    with rating:
        st.subheader("按延误天数区间查看低评分率")
        review_bars(table("review_delay_bands"))
    with coverage:
        st.subheader("评分覆盖率")
        frame = table("review_coverage")
        frame["is_delayed"] = frame.is_delayed.map({False: ON_TIME, True: LATE})
        st.dataframe(frame, hide_index=True, width="stretch", column_config={
            "is_delayed": "配送结果",
            "eligible": st.column_config.NumberColumn(ELIGIBLE, format="%,d"),
            "rated": st.column_config.NumberColumn("有效评分订单数", format="%,d"),
            "rating_coverage": st.column_config.NumberColumn("评分覆盖率", format="percent"),
        })
        low, high = risks.iloc[-2:].risk_difference * 100
        st.caption(f"对两组的缺失评分分别作相反的极端假设，风险差介于 {low:.2f}–{high:.2f} 个百分点。")
    st.subheader(f"低评分的{OR}")
    models = table("review_logit").set_index("model")
    forest_models = [
        "Mature window, crude", "Mature window, adjusted",
        "Mature window, customer-clustered", "Mature single seller, adjusted",
    ]
    fits = models.loc[forest_models].assign(label=[MODEL_LABELS[key] for key in forest_models])
    forest(fits)
    adjusted = models.loc["Mature window, adjusted"]
    st.caption(f"调整后 OR 为 {adjusted.odds_ratio:.2f}，95% 置信区间为 {adjusted.lower:.2f}–{adjusted.upper:.2f}，"
               f"基于 {int(adjusted.n):,} 笔有有效评分的订单。")
    st.caption("模型控制下单月份、收货州和订单主品类。优势比衡量历史样本中的统计关联。")
    with st.expander("模型估计与敏感性分析"):
        detail = models.reset_index()[["model", "n", "clusters", "odds_ratio", "lower", "upper"]].copy()
        detail["model"] = detail.model.map(MODEL_LABELS)
        st.dataframe(detail, hide_index=True, width="stretch", column_config={
            "model": "模型",
            "n": st.column_config.NumberColumn("有效评分订单数", format="%,d"),
            "clusters": st.column_config.NumberColumn("聚类数", format="%,d"),
            **{key: st.column_config.NumberColumn(label, format="%.2f") for key, label in
               [("odds_ratio", OR), ("lower", "95% 置信区间下限"), ("upper", "95% 置信区间上限")]},
        })


def sellers():
    st.title(SELLERS)
    st.write("根据历史筛选结果，安排高峰期商家与线路排查。")
    st.caption("固定排序样本 · 仅使用可判定延误的单商家订单 · 默认样本门槛为 50 笔可判定延误订单。")
    scores = table("period_seller_scores").query("period == 'all'")
    coverage = table("threshold_coverage").query("period == 'all' and threshold == 50").iloc[0]
    queue = table("final_seller_queue")
    for col, (label, value) in zip(st.columns(3), (
        ("达标候选商家数", f"{int(coverage.sellers):,}"),
        ("候选覆盖的单商家延误占比", f"{coverage.late_share:.2%}"),
        ("高峰期排查商家", f"{len(queue):,} 家"),
    )):
        col.metric(label, value, border=True)
    st.subheader("商家排查名单")
    st.caption("两期均至少有 50 笔可判定延误订单，且平滑超额延误为正。验证期同行对照覆盖率至少为 70%，"
               "且在覆盖范围内，实际延误订单数高于同行预期。按该差额从高到低排序。")
    picked = st.selectbox("查看商家详情", options=queue.seller_id.tolist(), format_func=lambda key:
                          f"{int(queue.loc[queue.seller_id == key, 'queue_order'].iloc[0]):02d} · {key}")
    row = queue.set_index("seller_id").loc[picked]
    stage = table("final_seller_stages").query("seller_id == @picked").set_index("delayed")
    late_stage, timely_stage = stage.loc[True], stage.loc[False]
    st.info(f"2018 年 1–7 月，{int(row.late_late)}/{int(row.late_n)} 笔订单延误（{row.holdout_rate:.2%}）。"
            f"在同行对照覆盖范围内，实际延误 {int(row.observed)} 笔，按收货州 × 订单主品类的同行基准预计 {row.expected:.1f} 笔。"
            f"延误订单运输中位耗时为 {late_stage.transit_p50_days:.2f} 天，按期订单为 {timely_stage.transit_p50_days:.2f} 天。")
    st.dataframe(queue[["queue_order", "seller_id", "early_rank", "late_rank", "late_n", "late_late",
                        "peer_coverage", "observed", "expected", "peer_excess"]], hide_index=True, width="stretch",
                 column_config={"queue_order": "排查顺序", "seller_id": st.column_config.TextColumn("商家编号", width=240),
                                "early_rank": "2017 排名", "late_rank": "2018 排名",
                                "late_n": "验证期样本", "late_late": "验证期延误",
                                "peer_coverage": st.column_config.NumberColumn("同行覆盖率", format="percent"),
                                "observed": st.column_config.NumberColumn("实际延误", help="同行对照覆盖范围内的实际延误订单数。"),
                                "expected": st.column_config.NumberColumn(
                                    "预期延误", format="%.1f", help="同行对照覆盖范围内按同行基准估算的延误订单数。"),
                                "peer_excess": st.column_config.NumberColumn("同行超额延误", format="%.1f")})
    left, right = st.columns([1.12, 1])
    with left:
        st.subheader("商家延误集中度")
        concentration(scores)
        volume_top = table("audit_top10").query("selection == 'late volume'").late.sum()
        previous = table("audit_top10").query("selection == 'smoothed excess'").late.sum()
        st.caption(f"按延误量排名的前 10 家共有 {volume_top:,} 笔延误（占 {volume_top/scores.late.sum():.1%}）。"
                   f"按平滑超额延误排名的前 10 家共有 {previous:,} 笔延误。")
    with right:
        stability = table("seller_temporal_stability").query("threshold == 50").iloc[0]
        st.subheader("跨期排名稳定性")
        st.metric("两期前十重合商家", f"{int(stability.top10_overlap)} / 10 家", border=True)
        st.write(f"比较 2017 年和 2018 年 1–7 月，共有 **{int(stability.paired_sellers)}** 家商家两期均达到样本门槛。"
                 f"斯皮尔曼秩相关系数（ρ）为 **{stability.spearman_score:.3f}**。")
        st.caption("两期均进入前十的商家位列排查名单前两位。名单为历史回顾性筛选结果。")
    with st.expander("全量样本的平滑延误率与超额延误"):
        rates = table("threshold_ranks").query("period == 'all' and threshold == 50")
        st.caption("平滑时加入按平台基准延误率分布的 50 笔参考订单。"
                   "平滑超额延误等于可判定延误订单数乘以平滑延误率高于平台基准的差额。")
        st.dataframe(rates[["rank", "seller_id", "eligible", "late", "smoothed_rate", "score"]],
                     hide_index=True, width="stretch", column_config={
                         "rank": "排名", "seller_id": "商家编号", "eligible": ELIGIBLE, "late": LATE_ORDERS,
                         "smoothed_rate": st.column_config.NumberColumn("平滑延误率", format="percent"),
                         "score": st.column_config.NumberColumn("平滑超额延误（笔）", format="%.1f"),
                     })
    with st.expander("高峰期收货州 × 订单主品类同行对比"):
        segments = table("audit_cohort_peak_segments").head(12).copy()
        segments["category_key"] = segments.category_key.map(category_name)
        st.dataframe(segments, hide_index=True, width="stretch", column_config={
            "customer_state": STATE, "category_key": CATEGORY,
            "cohort_n": "排查组可判定数", "cohort_late": "排查组延误数",
            "cohort_rate": st.column_config.NumberColumn("排查组延误率", format="percent"),
            "peer_n": "同行可判定数", "peer_late": "同行延误数",
            "peer_rate": st.column_config.NumberColumn("同行延误率", format="percent"),
        })
    st.caption("同行差异与履约耗时用于安排订单和承运线路复盘。最终签收记录的粒度为订单。")


def scenarios():
    st.title(SCENARIOS)
    st.write("估算配送延误率按设定幅度相对下降时，预计可减少的延误订单数。")
    frame = table("final_scenario").query("scope == 'Feb-Mar peak'")
    baseline = frame.iloc[0]
    eligible, late = int(baseline.baseline_orders), int(baseline.baseline_late)
    st.caption(f"固定样本 · 2018 年 2–3 月 · {int(baseline.sellers)} 家排查商家 · "
               f"{eligible:,} 笔可判定延误订单 · 基线配送延误率 {baseline.baseline_late_rate:.2%}")
    change = st.slider("配送延误率相对降幅", min_value=0, max_value=30, value=10, step=1, format="%d%%")
    fewer = late * change / 100
    for col, (label, value) in zip(st.columns(3), (
        ("基线延误订单数", f"{late:,}"), ("预计减少的延误订单数", f"{fewer:,.1f}"),
        ("预计剩余延误订单数", f"{late - fewer:,.1f}"),
    )):
        col.metric(label, value, border=True)
    st.info(f"情景配送延误率为 {(late - fewer) / eligible:.2%}。"
            "假设可判定延误订单数、样本构成及承诺送达日期口径固定。"
            "以上为给定相对降幅下的预期订单数。")
    st.subheader("参考情景")
    st.dataframe(frame[["relative_improvement", "fewer_late_orders", "scenario_late_rate"]],
                 hide_index=True, width="stretch", column_config={
                     "relative_improvement": st.column_config.NumberColumn("相对降幅", format="percent"),
                     "fewer_late_orders": st.column_config.NumberColumn("预计减少的延误订单数", format="%.1f"),
                     "scenario_late_rate": st.column_config.NumberColumn(f"情景{LATE_RATE}", format="percent"),
                 })
