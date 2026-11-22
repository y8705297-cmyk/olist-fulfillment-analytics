from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from labels import CATEGORY, MONTH, STATE, category_name

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/olist.duckdb"
OUTPUT = DB.parent / "analysis"
PEAKS = ("2017-11", "2018-02", "2018-03")


@st.cache_data(show_spinner=False)
def load_orders(revision):
    with duckdb.connect(str(DB), read_only=True) as con:
        con.execute((ROOT / "analysis/delivery.sql").read_text())
        orders = con.execute("""
            SELECT strftime(purchase_month, '%Y-%m') AS month, customer_state AS state, category, category_key,
                   order_status = 'delivered' AS delivered, is_delayed AS delayed, is_low_rating AS low,
                   valid_phases, delivery_days, purchase_to_carrier_days, carrier_to_delivery_days
            FROM analysis_orders ORDER BY order_id
        """).df()
    return orders.assign(category_label=orders.category_key.map(category_name))


@st.cache_data(show_spinner=False)
def load_table(name, revision):
    return pd.read_csv(OUTPUT / f"{name}.csv")


def table(name):
    path = OUTPUT / f"{name}.csv"
    if not path.is_file():
        st.error("缺少分析结果表。请在项目根目录运行 `make analysis`。")
        st.stop()
    return load_table(name, path.stat().st_mtime_ns)


def orders_from_db():
    if not DB.is_file():
        st.error("缺少本地 DuckDB 数据库。请在项目根目录运行 `make analysis`。")
        st.stop()
    return load_orders(DB.stat().st_mtime_ns)


def controls():
    orders = orders_from_db()
    months = pd.period_range(orders.month.min(), orders.month.max(), freq="M").astype(str).tolist()
    category_labels = orders.drop_duplicates("category").set_index("category").category_label.to_dict()
    with st.sidebar:
        st.subheader("筛选范围")
        st.select_slider(MONTH, months, value=(months[0], months[-1]), key="scope_month")
        st.multiselect(STATE, sorted(orders.state.dropna().unique()), key="scope_state", placeholder="全部州")
        st.multiselect(CATEGORY, sorted(category_labels), key="scope_category", placeholder="全部品类",
                       format_func=category_labels.__getitem__)


def selection():
    orders = orders_from_db()
    lo, hi = st.session_state.scope_month
    states = st.session_state.scope_state
    categories = st.session_state.scope_category
    selected = orders[orders.month.between(lo, hi)]
    if states:
        selected = selected[selected.state.isin(states)]
    if categories:
        selected = selected[selected.category.isin(categories)]
    state_scope = f"已选 {len(states)} 个州" if states else "全部州"
    category_scope = f"已选 {len(categories)} 个主品类" if categories else "全部主品类"
    st.caption(f"下单月份：{lo} 至 {hi} · {len(selected):,} 笔订单 · {state_scope} · {category_scope}")
    if selected.empty:
        st.info("当前筛选范围内没有订单。请扩大下单月份范围或清除筛选。")
        st.stop()
    return selected


def delivery_rollup(data, group):
    result = data.groupby(group, dropna=False, as_index=False).agg(
        orders=("delayed", "size"), eligible=("delayed", "count"), late=("delayed", "sum")
    )
    result["late"] = result.late.astype(int)
    result["late_rate"] = result.late / result.eligible.replace(0, float("nan"))
    return result


def display_rate(num, den):
    return f"{num / den:.2%}" if den else "—"
