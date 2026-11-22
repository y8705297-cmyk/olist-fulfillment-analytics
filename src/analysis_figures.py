import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

INK = "#162a3a"
TEAL = "#0c7a79"
RUST = "#bc502d"
GRAY = "#667482"


def save(fig, path):
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)


def percent(ax, axis="y"):
    getattr(ax, f"{axis}axis").set_major_formatter(PercentFormatter(xmax=1, decimals=0))


def monthly(tables, path):
    data = tables["monthly_delivery"]
    data = data[data.purchase_month.between("2017-01-01", "2018-07-01")]
    peaks = data[data.purchase_month.astype(str).str[:7].isin(["2017-11", "2018-02", "2018-03"])]
    fig, (rate_ax, volume_ax) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True, layout="constrained")
    rate_ax.set_title(f"Late delivery by purchase month | {data.eligible.sum():,} eligible orders", loc="left")
    rate_ax.plot(data.purchase_month, data.late_rate, color=TEAL, marker="o", linewidth=2)
    rate_ax.scatter(peaks.purchase_month, peaks.late_rate, color=RUST, zorder=3)
    for row in peaks.itertuples():
        rate_ax.annotate(f"{row.late_rate:.1%}", (row.purchase_month, row.late_rate),
                         xytext=(0, 6), textcoords="offset points", ha="center", color=RUST)
    rate_ax.set_ylim(0, .23)
    rate_ax.set_ylabel("Late orders (%)")
    percent(rate_ax)
    volume_ax.bar(data.purchase_month, data.eligible, width=21, color="#c5d4db", label="Eligible")
    volume_ax.bar(data.purchase_month, data.late, width=21, color=RUST, label="Late")
    volume_ax.set_ylabel("Orders")
    volume_ax.set_xlabel("Purchase month")
    volume_ax.legend(frameon=False, loc="upper left", ncols=2)
    volume_ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    volume_ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    save(fig, path)


def segments(tables, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.3), layout="constrained")
    for ax, table, field, title in (
        (axes[0], "state_delivery", "customer_state", "Destination state"),
        (axes[1], "primary_category_delivery", "category", "Primary product category"),
    ):
        data = tables[table].head(8).iloc[::-1]
        labels = [f"{name.replace('_', ' ')}  (n={n:,})" for name, n in zip(data[field], data.eligible)]
        bars = ax.barh(labels, data.late, color=TEAL)
        ax.bar_label(bars, labels=[f"{n:,}  |  {rate:.1%}" for n, rate in zip(data.late, data.late_rate)],
                     padding=5, color=INK, fontsize=9)
        ax.set_xlim(0, data.late.max() * 1.38)
        ax.set_xlabel("Late orders (count); labels also show late rate")
        ax.set_title(title, loc="left")
    fig.suptitle("Highest delay volumes by segment | Full snapshot, 96,470 eligible orders", x=.02, ha="left")
    save(fig, path)


def stages(tables, path):
    data = tables["stage_delivery"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharex=True, layout="constrained")
    for ax, (stage, group) in zip(axes, data.groupby("stage", sort=False)):
        for y, row in enumerate(group.itertuples()):
            p10, p25, p50, p75, p90 = row.quantiles
            color = RUST if row.delayed else TEAL
            ax.hlines(y, p10, p90, color=color, linewidth=2)
            ax.hlines(y, p25, p75, color=color, linewidth=9)
            ax.scatter(p50, y, color="white", edgecolor=color, zorder=3)
        ax.set_yticks(range(len(group)), [f"{'Late' if row.delayed else 'On time'} (n={row.orders:,})"
                                         for row in group.itertuples()])
        ax.set_ylim(-.5, 1.5)
        ax.set_title(stage, loc="left")
        ax.set_xlabel("Elapsed days")
    fig.suptitle("Fulfillment stage duration | P10–P90, IQR and median", x=.02, ha="left")
    save(fig, path)


def reviews(tables, path):
    data = tables["review_delay_bands"]
    pos = np.arange(len(data))
    fig, (rate_ax, gap_ax) = plt.subplots(1, 2, figsize=(10, 4.2), layout="constrained")
    labels = [f"{r.band}\n(n={r.rated:,})" for r in data.itertuples()]
    rate_ax.bar(pos, data.low_rate, color=[TEAL, RUST, RUST, RUST, RUST])
    rate_ax.set_xticks(pos, labels)
    rate_ax.set_ylabel("Orders with score ≤ 2 (%)")
    rate_ax.set_xlabel("Calendar days late (rated orders)")
    rate_ax.set_title("Low-rating rate", loc="left")
    percent(rate_ax)
    gaps = data.iloc[1:]
    gap_ax.errorbar(pos[1:], gaps.risk_difference * 100,
                    yerr=np.array([gaps.risk_difference - gaps.lower, gaps.upper - gaps.risk_difference]) * 100,
                    fmt="o", color=RUST, capsize=4)
    gap_ax.set_xticks(pos[1:], labels[1:])
    gap_ax.set_ylim(0, 80)
    gap_ax.set_ylabel("Risk difference (percentage points)")
    gap_ax.set_xlabel("Calendar days late (rated orders)")
    gap_ax.set_title("Difference vs. on time, 95% CI", loc="left")
    fig.suptitle(f"Delivery delay and low ratings | {data.rated.sum():,} rated eligible orders", x=.02, ha="left")
    save(fig, path)


def sellers(tables, path):
    data = tables["seller_followup"]
    selected = data.seller_id.isin(tables["final_seller_queue"].seller_id)
    fig, (ax, concentration) = plt.subplots(1, 2, figsize=(10, 4.6), layout="constrained")
    ax.scatter(data.early_score[~selected], data.late_score[~selected], s=28, color=GRAY, alpha=.55, label="Other paired sellers")
    ax.scatter(data.early_score[selected], data.late_score[selected], s=32, color=RUST, label="Audit cohort")
    ax.set_title(f"Score stability | {len(data)} sellers with ≥50 orders per window", loc="left", fontsize=10)
    ax.set_xlabel("2017 smoothed excess (orders)")
    ax.set_ylabel("Jan–Jul 2018 smoothed excess (orders)")
    ax.legend(frameon=False, fontsize=8)
    counts = tables["period_seller_scores"].query("period == 'all'").late.sort_values(ascending=False)
    ranks = np.arange(1, len(counts) + 1)
    concentration.plot(ranks, counts.cumsum() / counts.sum(), color=TEAL)
    concentration.scatter([10, 50], [counts.iloc[:10].sum() / counts.sum(), counts.iloc[:50].sum() / counts.sum()],
                          color=RUST, zorder=3)
    concentration.set_xscale("log")
    concentration.set_xlabel("Sellers ranked by late volume (log scale)")
    concentration.set_ylabel("Cumulative share of late orders (%)")
    concentration.set_title(f"Delay concentration | {counts.sum():,} late single-seller orders", loc="left", fontsize=10)
    percent(concentration)
    save(fig, path)


def render(tables, directory):
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                         "axes.labelcolor": INK, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.axisbelow": True, "grid.alpha": .2, "axes.grid": True})
    for name, chart in (("monthly_delivery", monthly), ("delivery_segments", segments),
                        ("fulfillment_stages", stages), ("delay_and_ratings", reviews), ("seller_stability", sellers)):
        chart(tables, directory / f"{name}.png")
        print(f"Figure: {name}.png", flush=True)
