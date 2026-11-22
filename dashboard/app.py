import streamlit as st

from data import controls
from decision import experience, scenarios, sellers
from delivery import diagnostics, overview
from labels import DIAGNOSTICS, EXPERIENCE, OVERVIEW, SCENARIOS, SELLERS


st.set_page_config(page_title="Olist 履约分析", layout="wide")
st.markdown("""
<style>
    .block-container { max-width: 1380px; padding-top: 3.25rem; padding-bottom: 3rem; }
    [data-testid="stMetric"] { background: #F5F8F7; border-color: #D9E6E3; border-radius: 10px; }
    [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    [data-testid="stApp"], #vg-tooltip-element {
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    }
    [data-testid="stMetricLabel"] p { white-space: normal; overflow-wrap: anywhere; }
    [data-testid="stSidebarNav"] { padding-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### Olist 履约分析")
    st.caption("巴西电商平台 · Kaggle 第 2 版")

page = st.navigation([
    st.Page(overview, title=OVERVIEW, default=True),
    st.Page(diagnostics, title=DIAGNOSTICS, url_path="delivery"),
    st.Page(experience, title=EXPERIENCE, url_path="experience"),
    st.Page(sellers, title=SELLERS, url_path="sellers"),
    st.Page(scenarios, title=SCENARIOS, url_path="scenarios"),
])
if page.url_path in ("", "delivery"):
    controls()
page.run()
