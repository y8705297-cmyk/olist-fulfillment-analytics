import streamlit as st

from charts import duration_trend, segments, stages, trend
from data import PEAKS, delivery_rollup, display_rate, selection
from labels import CATEGORY, DIAGNOSTICS, ELIGIBLE, LATE_ORDERS, LATE_RATE, LOW_RATE, MONTH, ORDERS, OVERVIEW, STATE


def peaks(monthly):
    available = monthly[monthly.month.isin(PEAKS) & monthly.eligible.gt(0)]
    if available.empty:
        st.caption("当前筛选范围内，三个高峰月均无可判定延误订单。")
        return
    st.dataframe(available[["month", "eligible", "late", "late_rate"]], hide_index=True, width="stretch",
                 column_config={
                     "month": MONTH,
                     "eligible": st.column_config.NumberColumn(ELIGIBLE, format="%,d"),
                     "late": st.column_config.NumberColumn(LATE_ORDERS, format="%,d"),
                     "late_rate": st.column_config.NumberColumn(LATE_RATE, format="percent"),
                 })
    st.caption("高峰月基于平台全量数据识别。表中数据随当前筛选条件更新。")


def overview():
    st.title(OVERVIEW)
    st.write("了解配送延误的规模和严重程度，确定优先排查范围。")
    orders = selection()
    eligible = int(orders.delayed.count())
    late = int(orders.delayed.sum())
    rated = int(orders.low.count())
    for col, (label, value) in zip(st.columns(3), (
        (ORDERS, f"{len(orders):,}"), ("已交付订单占比", display_rate(orders.delivered.sum(), len(orders))),
        (ELIGIBLE, f"{eligible:,}"),
    )):
        col.metric(label, value, border=True)
    for col, (label, value) in zip(st.columns(3), (
        (LATE_RATE, display_rate(late, eligible)), (LATE_ORDERS, f"{late:,}"),
        (LOW_RATE, display_rate(orders.low.sum(), rated)),
    )):
        col.metric(label, value, border=True)
    st.caption(f"已交付订单占比按订单状态计算。配送延误率以 {eligible:,} 笔可判定延误订单为分母。"
               f"低评分指评分不高于 2 分，分母为所有订单状态中有有效评分的 {rated:,} 笔订单。")
    if not eligible:
        st.info("当前筛选范围内没有可判定延误订单，无法计算延误率或按维度拆解。")
        return
    monthly = delivery_rollup(orders, "month")
    chart, context = st.columns([1.65, 1])
    with chart:
        st.subheader("月度配送延误趋势")
        trend(monthly)
        st.caption("当月可判定延误订单达到 30 笔时显示延误率。延误订单数覆盖筛选范围内的所有有订单月份。")
    with context:
        st.subheader("延误高峰月")
        peaks(monthly)
        st.caption("结合延误订单数和配送延误率安排排查资源。")
    st.subheader("延误订单数最多的收货州")
    segments(delivery_rollup(orders, "state"), "state", STATE)


def diagnostics():
    st.title(DIAGNOSTICS)
    st.write("比较交接前和运输阶段的耗时，定位延误订单较多的收货州与主品类。")
    orders = selection()
    monthly = delivery_rollup(orders, "month")
    complete = orders[orders.valid_phases.fillna(False)]
    st.subheader("按下单月份查看履约耗时")
    if complete.empty:
        st.info("当前筛选范围内没有可判定延误且各阶段时间完整、顺序有效的订单。")
    else:
        st.caption(f"共有 {len(complete):,} 笔订单具备有效的下单、交接承运方和签收时间。")
        duration_trend(complete)
        st.caption("每月至少有 30 笔时间完整的订单才显示中位数。下方分布包含筛选范围内所有时间完整的订单。")
        st.subheader("按期与延误订单的分阶段耗时")
        st.caption("细线表示第 10 至第 90 百分位（P10–P90），粗条表示第 25 至第 75 百分位（P25–P75），"
                   "圆点表示中位数（P50）。悬停可查看样本量和分位数。")
        stages(complete)
    if not monthly.eligible.sum():
        return
    st.subheader("收货州与订单主品类")
    states, categories = st.tabs([STATE, CATEGORY])
    with states:
        segments(delivery_rollup(orders, "state"), "state", STATE)
    with categories:
        segments(delivery_rollup(orders, ["category", "category_label"]), "category", CATEGORY)
    st.caption("图中按延误订单数展示前八个有可判定延误订单的分组。各组以本组可判定延误订单数为分母。")
    st.subheader("延误高峰月回顾")
    timely = (complete.groupby("month", as_index=False).agg(
        complete_orders=("valid_phases", "size"),
        handoff_p50=("purchase_to_carrier_days", "median"),
        transit_p90=("carrier_to_delivery_days", lambda values: values.quantile(.90)),
    ))
    detail = monthly.merge(timely, on="month", how="left")
    detail = detail[detail.month.isin(PEAKS) & detail.eligible.gt(0)]
    if detail.empty:
        st.caption("当前筛选范围内，三个高峰月均无可判定延误订单。")
    else:
        st.dataframe(detail.drop(columns="orders"), hide_index=True, width="stretch", column_config={
            "month": MONTH,
            "eligible": st.column_config.NumberColumn(ELIGIBLE, format="%,d"),
            "late": st.column_config.NumberColumn(LATE_ORDERS, format="%,d"),
            "late_rate": st.column_config.NumberColumn(LATE_RATE, format="percent"),
            "complete_orders": st.column_config.NumberColumn("时间完整订单数", format="%,d"),
            "handoff_p50": st.column_config.NumberColumn("交接前 P50（天）", format="%.2f"),
            "transit_p90": st.column_config.NumberColumn("运输 P90（天）", format="%.2f"),
        })
    st.caption("平台历史数据中，2017 年 11 月下旬订单量上升的同时，交接前耗时延长。2018 年 2、3 月运输长尾更明显。"
               "可据此安排分阶段排查。")
