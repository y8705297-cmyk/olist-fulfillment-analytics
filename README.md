# Marketplace Delivery Performance & Operational Prioritization

Olist fulfillment analytics project that turns Brazilian marketplace orders into a prioritized operational review of peak months, delivery lanes, and a historical seller cohort.

本项目以巴西 Olist 电商订单为样本，分析配送延误与低评分的关联，识别高峰期应优先排查的线路与商家。Dashboard 使用简体中文，业务报告为中文 PDF。

[Business report (PDF, Chinese)](reports/business_report.pdf) · [Report source](reports/business_report.md) · [Seller review queue](reports/seller_prioritization.md)

## Business problem

Where should an operations team investigate first when it can review only a limited number of delivery exceptions? This project combines delay volume, stage duration, customer ratings, and the persistence of seller signals to decide which orders and routes to review.

## Data and method

The source is the [official Kaggle Olist Brazilian E-Commerce Public Dataset, v2](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/versions/2), archive version ID 2669146. The full snapshot covers **99,441 orders placed from 2016-09-04 to 2018-10-17**. The primary time-series and adjusted model use orders placed **January 2017–July 2018**. The [snapshot manifest](data/snapshot.json) fixes the nine CSV fingerprints.

DuckDB builds order and order–seller facts after reducing one-to-many item, payment, and review records to the appropriate grain. A late order is a delivered order whose valid actual delivery day exceeds the promised day. The analysis uses mutually exclusive primary categories, a logistic regression on low ratings (score ≤2), and seller scores based on single-seller orders. [Metric definitions](reports/data_dictionary.md) · [Data quality audit](reports/data_quality_report.md)

## Key findings and recommendations

| Evidence | Decision |
| --- | --- |
| **6,534 / 96,470 eligible orders were late (6.77%)**. Nov 2017, Feb 2018, and Mar 2018 reached **12.40%, 14.13%, and 18.96%** and accounted for 51.45% of late orders in the mature window. | Review capacity and handoff around late November and the transit tail in February–March. |
| SP had **1,820** late orders. RJ had **1,495** and a **12.11%** late rate. Median transit was **26.20 days** for late orders and **6.95** for on-time orders. | Start with high-volume RJ lanes and track SP separately for workload. Reconcile carrier events before assigning responsibility. |
| Low ratings were **62.42%** among rated late orders and **9.27%** among rated on-time orders. Adjusted OR **15.44** (95% CI 14.52–16.41), controlling for purchase month, destination state, and primary category. | Test early exception tracking and customer communication. Measure effects in the pilot. |
| Seller scores across 2017 and Jan–Jul 2018 had Spearman **ρ = 0.371** among 96 sellers with at least 50 eligible orders in each window. The top tens shared **2** sellers. | Review the **21** sellers with positive smoothed excess in both windows, ≥70% holdout peer coverage, and positive observed-minus-expected delays within destination state × primary-category strata. |
| The cohort had **366 / 1,522** late orders in Feb–Mar 2018. Relative reductions of **10% and 20%** imply **36.6 and 73.2** fewer late orders at fixed volume and mix. | Use the estimates for scenario planning and validate realized improvements in a comparable future peak. |

![Monthly delivery trends in the mature window](figures/monthly_delivery.png)

## Dashboard preview

The dashboard uses Simplified Chinese. Executive Overview and Delivery Diagnostics apply the same purchase-month, destination-state, and primary-category filters to their metrics and charts. Customer Experience, Seller Prioritization, and Improvement Scenarios label their fixed analysis samples. The scenario slider varies the relative reduction from 0% to 30%.

[![经营与履约概览](figures/dashboard_overview.png)](figures/dashboard_overview.png)

[履约异常诊断](figures/dashboard_delivery.png) · [客户体验分析](figures/dashboard_experience.png) · [商家排查优先级](figures/dashboard_sellers.png) · [改善情景测算](figures/dashboard_scenarios.png)

## Repository structure

| Path | Purpose |
| --- | --- |
| `sql/`, `src/` | DuckDB fact models, data checks, statistics, and analysis exports |
| `analysis/` | Raw audit, delivery diagnostics, and seller prioritization SQL |
| `dashboard/` | Five-page local Streamlit app |
| `tests/`, `scripts/` | Model tests, live browser checks, and PDF generation |
| `data/` | Source manifest and local data directories |
| `figures/`, `reports/` | Figures, portfolio report, seller queue, and acceptance record |

## Reproduction

Tested on Apple Silicon macOS with Python 3.14. Run from the repository root.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make analysis
.venv/bin/streamlit run dashboard/app.py
```

`make analysis` verifies the source fingerprints, builds DuckDB, runs the model tests, and writes report tables to `data/processed/analysis/`. If the official ZIP is already available, import it once with `.venv/bin/python -m src.fetch_data --archive ~/Downloads/brazilian-ecommerce.zip` before running the build. See [data setup](data/README.md). The dashboard reads local outputs on startup and caches them.

To reproduce browser checks or print the Markdown report, install the optional delivery dependencies. Both checks require Google Chrome. PDF export also requires Pandoc and an installed Chinese font such as PingFang SC or Noto Sans CJK SC. Run the browser check while Streamlit is running on its default local port.

```bash
.venv/bin/python -m pip install -r requirements-delivery.txt
.venv/bin/python scripts/check_dashboard.py
.venv/bin/python scripts/render_report.py
```

## Limitations

Carrier event details and an explicit extraction cutoff are absent. Phase times guide investigation, and late snapshot months have limited coverage. Review coverage differs by delivery outcome. The seller cohort uses historical holdout information and needs a new peak-period validation. Adjusted odds ratios are associational, and scenario counts depend on stated assumptions. [Analysis evidence](reports/analysis_findings.md) · [Delivery acceptance](reports/release_validation.md)
