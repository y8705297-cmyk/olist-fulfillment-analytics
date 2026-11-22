import altair as alt
import pandas as pd
import streamlit as st

from labels import ELIGIBLE, HANDOFF, LATE, LATE_ORDERS, LATE_RATE, LOW_RATE, MONTH, ON_TIME, OR, ORDERS, TRANSIT

TEAL = "#08776F"
RUST = "#B24B32"
GRAY = "#77939A"
INK = "#172E34"
FONT = "PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif"


def show(chart):
    spec = (
        chart.configure_view(stroke=None)
        .configure_axis(labelColor=INK, titleColor=INK, gridColor="#E5ECEB", domainColor="#CAD8D7",
                        labelFont=FONT, titleFont=FONT)
        .configure_legend(labelFont=FONT, titleFont=FONT)
        .configure_header(labelFont=FONT, titleFont=FONT)
        .configure_title(anchor="start", color=INK, font=FONT)
    )
    st.altair_chart(spec, width="stretch")


def trend(monthly):
    frame = monthly.assign(purchase_month=pd.to_datetime(monthly.month))
    frame["plotted_rate"] = frame.late_rate.where(frame.eligible >= 30)
    base = alt.Chart(frame).encode(
        x=alt.X("purchase_month:T", title=MONTH, axis=alt.Axis(format="%y-%m", labelOverlap=True)),
        tooltip=[alt.Tooltip("purchase_month:T", title=MONTH, format="%Y-%m"),
                 alt.Tooltip("eligible:Q", title=ELIGIBLE, format=",d"),
                 alt.Tooltip("late:Q", title=LATE_ORDERS, format=",d"),
                 alt.Tooltip("late_rate:Q", title=LATE_RATE, format=".2%")],
    )
    rate = base.mark_line(point=alt.OverlayMarkDef(size=45, filled=True, color=TEAL), color=TEAL, strokeWidth=2.5).encode(
        y=alt.Y("plotted_rate:Q", title=LATE_RATE, axis=alt.Axis(format="%")),
    ).properties(height=158)
    volume = base.mark_bar(color=RUST, cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=15).encode(
        y=alt.Y("late:Q", title=LATE_ORDERS),
    ).properties(height=108)
    show(alt.vconcat(rate, volume, spacing=12))


def segments(frame, field, title):
    data = frame[frame.eligible > 0].sort_values(["late", field], ascending=[False, True]).head(8).copy()
    data[field] = data.category_label if field == "category" else data[field]
    order = data[field].tolist()
    base = alt.Chart(data).encode(
        y=alt.Y(f"{field}:N", title=None, sort=order, axis=alt.Axis(labelLimit=205)),
        tooltip=[alt.Tooltip(f"{field}:N", title=title), alt.Tooltip("eligible:Q", title=ELIGIBLE, format=",d"),
                 alt.Tooltip("late:Q", title=LATE_ORDERS, format=",d"), alt.Tooltip("late_rate:Q", title=LATE_RATE, format=".2%")],
    ).properties(height=235)
    vol = base.mark_bar(color=TEAL, cornerRadiusEnd=3).encode(x=alt.X("late:Q", title=LATE_ORDERS))
    rate = base.mark_bar(color=RUST, cornerRadiusEnd=3).encode(
        x=alt.X("late_rate:Q", title=LATE_RATE, axis=alt.Axis(format="%")),
        y=alt.Y(f"{field}:N", title=None, sort=order, axis=None),
    )
    show(alt.hconcat(vol, rate, spacing=20).resolve_scale(x="independent", y="independent"))


def stages(stage_orders):
    rows = []
    for field, label in (("purchase_to_carrier_days", HANDOFF),
                         ("carrier_to_delivery_days", TRANSIT)):
        for delayed, group in stage_orders.groupby("delayed", observed=True):
            p10, p25, p50, p75, p90 = group[field].quantile([.10, .25, .50, .75, .90])
            rows.append(dict(stage=label, group=LATE if delayed else ON_TIME, n=len(group),
                             p10=p10, p25=p25, p50=p50, p75=p75, p90=p90))
    frame = pd.DataFrame(rows)
    base = alt.Chart(frame).encode(
        y=alt.Y("group:N", title=None), color=alt.Color("group:N", title=None,
            scale=alt.Scale(domain=[LATE, ON_TIME], range=[RUST, TEAL])),
        tooltip=[alt.Tooltip("stage:N", title="履约阶段"), alt.Tooltip("group:N", title="配送结果"), alt.Tooltip("n:Q", title=ORDERS, format=",d"),
                 *(alt.Tooltip(f"p{n}:Q", title=f"P{n}（天）", format=".2f") for n in [10, 25, 50, 75, 90])],
    )
    chart = (
        base.mark_rule(strokeWidth=2).encode(x=alt.X("p10:Q", title="耗时（天）"), x2="p90:Q")
        + base.mark_bar(size=12).encode(x="p25:Q", x2="p75:Q")
        + base.mark_point(color="white", filled=True, size=42).encode(x="p50:Q", color=alt.value("white"))
    ).properties(height=110)
    show(chart.facet(column=alt.Column("stage:N", title=None, sort=[HANDOFF, TRANSIT],
                                     header=alt.Header(labelOrient="top", labelFontSize=12)), spacing=22))


def duration_trend(stage_orders):
    long = (stage_orders.groupby("month")[["purchase_to_carrier_days", "carrier_to_delivery_days"]]
            .median().rename(columns={"purchase_to_carrier_days": HANDOFF,
                                     "carrier_to_delivery_days": TRANSIT})
            .reset_index().melt("month", var_name="stage", value_name="median_days"))
    long["purchase_month"] = pd.to_datetime(long.month)
    counts = stage_orders.groupby("month").size().rename("n")
    long = long.join(counts, on="month")
    long["plotted_days"] = long.median_days.where(long.n >= 30)
    show(alt.Chart(long).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("purchase_month:T", title=MONTH, axis=alt.Axis(format="%y-%m")),
        y=alt.Y("plotted_days:Q", title="中位耗时（天）"),
        color=alt.Color("stage:N", title=None, scale=alt.Scale(
            domain=[TRANSIT, HANDOFF], range=[RUST, TEAL]),
            legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("purchase_month:T", title=MONTH, format="%Y-%m"), alt.Tooltip("stage:N", title="履约阶段"),
                 alt.Tooltip("median_days:Q", title="中位耗时（天）", format=".2f"), alt.Tooltip("n:Q", title="时间完整订单数", format=",d")],
    ).properties(height=190))


def review_bars(data):
    data = data.assign(band=data.band.replace({"<=0": "≤0", "15+": "≥15"}))
    show(alt.Chart(data).mark_bar(color=TEAL, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("band:N", title="延误天数（日历日）", sort=data.band.tolist(), axis=alt.Axis(labelAngle=0)),
        y=alt.Y("low_rate:Q", title=LOW_RATE, axis=alt.Axis(format="%")),
        tooltip=[alt.Tooltip("band:N", title="延误天数区间"), alt.Tooltip("rated:Q", title="有效评分订单数", format=",d"),
                 alt.Tooltip("low_rate:Q", title=LOW_RATE, format=".2%")],
    ).properties(height=210))


def forest(data):
    base = alt.Chart(data).encode(
        y=alt.Y("label:N", title=None, sort=data.label.tolist(), axis=alt.Axis(labelLimit=260)),
        tooltip=[alt.Tooltip("label:N", title="模型"), alt.Tooltip("n:Q", title=ORDERS, format=",d"), alt.Tooltip("odds_ratio:Q", title=OR, format=".2f"),
                 alt.Tooltip("lower:Q", title="95% 置信区间下限", format=".2f"), alt.Tooltip("upper:Q", title="95% 置信区间上限", format=".2f")],
    )
    bounds = base.mark_rule(color=GRAY, strokeWidth=3).encode(
        x=alt.X("lower:Q", title=f"{OR}及 95% 置信区间", scale=alt.Scale(zero=False)), x2="upper:Q")
    points = base.mark_circle(color=TEAL, size=95).encode(x="odds_ratio:Q")
    show((bounds + points).properties(height=175))


def concentration(scores):
    ranked = scores.sort_values("late", ascending=False).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    ranked["share"] = ranked.late.cumsum() / ranked.late.sum()
    show(alt.Chart(ranked).mark_line(color=TEAL, strokeWidth=2.5).encode(
        x=alt.X("rank:Q", title="按延误订单数排列的商家名次（对数刻度）", scale=alt.Scale(type="log")),
        y=alt.Y("share:Q", title="延误订单累计占比", axis=alt.Axis(format="%")),
        tooltip=[alt.Tooltip("rank:Q", title="商家名次"), alt.Tooltip("share:Q", title="延误订单累计占比", format=".1%")],
    ).properties(height=185))
