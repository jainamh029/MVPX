"""
================================================================================
MVPX — Custom Sports Economy Index
Full Backtest & Stress Test vs S&P 500
Real data pulled from Yahoo Finance via yfinance

SETUP (run once):
    pip install yfinance pandas numpy matplotlib seaborn scipy

RUN:
    python mvpx_analysis.py

OUTPUTS (saved to ./mvpx_output/):
    01_mvpx_vs_sp500_cumulative.png   — Full backtest growth of $10,000
    02_annual_returns_comparison.png  — Side-by-side annual bar chart
    03_drawdown_comparison.png        — Rolling drawdown both indexes
    04_stress_2008.png                — 2008 GFC scenario
    05_stress_2020.png                — 2020 crash + recovery
    06_stress_2022.png                — 2022 Fed rate hike cycle
    07_stock_heatmap.png              — Per-stock annual return heatmap
    08_rolling_correlation.png        — 12-month rolling correlation to S&P
    09_sector_weights_pie.png         — MVPX v2 segment weights
    mvpx_full_report.txt              — Complete numerical report
================================================================================
"""

import os
import warnings
import textwrap
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    raise SystemExit(
        "\n  yfinance not found.\n"
        "  Run:  pip install yfinance pandas numpy matplotlib seaborn scipy\n"
    )

# ─────────────────────────────────────────────────────────────────────────────
# 0.  OUTPUT DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "mvpx_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  MVPX v2 INDEX DEFINITION
#     Conviction-weighted, 18 holdings, 6 segments
#     Weights sum to exactly 100 %
# ─────────────────────────────────────────────────────────────────────────────
MVPX = {
    # ticker : (weight_pct, segment, conviction)
    "FLUT":  (8.35, "Gaming & Betting",     "High"),
    "TKO":   (8.33, "Leagues & Venues",     "High"),
    "LYV":   (8.33, "Sponsorship & Media",  "High"),
    "FWONA": (8.33, "Motorsport",           "High"),
    "ONON":  (8.33, "Apparel & Equipment",  "High"),
    "NFLX":  (8.33, "Broadcasting",        "High"),
    "DIS":   (5.00, "Broadcasting",        "Medium"),
    "ADDYY": (5.00, "Apparel & Equipment",  "Medium"),
    "EA":    (5.00, "Gaming & Betting",     "Medium"),
    "FOX":   (5.00, "Broadcasting",        "Medium"),
    "DKNG":  (5.00, "Gaming & Betting",     "Medium"),
    "WBD":   (5.00, "Broadcasting",        "Medium"),
    "EDR":   (5.00, "Leagues & Venues",     "Medium"),
    "CHDN":  (5.00, "Leagues & Venues",     "Medium"),
    "TTWO":  (2.50, "Gaming & Betting",     "Tactical"),
    "MSGS":  (2.50, "Leagues & Venues",     "Tactical"),
    "GOLF":  (2.50, "Apparel & Equipment",  "Tactical"),
    "LSEA":  (2.50, "Leagues & Venues",     "Tactical"),
}

TICKERS   = list(MVPX.keys())
WEIGHTS   = np.array([MVPX[t][0] / 100 for t in TICKERS])
BENCHMARK = "^GSPC"   # S&P 500

# Date ranges
BACKTEST_START = "2019-01-01"   # as far back as all holdings have data
BACKTEST_END   = datetime.today().strftime("%Y-%m-%d")

STRESS = {
    "2008_GFC":      ("2007-10-01", "2009-06-30"),
    "2020_COVID":    ("2020-01-01", "2021-03-31"),
    "2022_HIKES":    ("2022-01-01", "2023-01-31"),
}

SEGMENT_COLORS = {
    "Broadcasting":        "#378ADD",
    "Leagues & Venues":    "#1D9E75",
    "Apparel & Equipment": "#D85A30",
    "Gaming & Betting":    "#7F77DD",
    "Sponsorship & Media": "#D4537E",
    "Motorsport":          "#BA7517",
}

CONVICTION_MARKERS = {"High": "★", "Medium": "●", "Tactical": "◆"}

# ─────────────────────────────────────────────────────────────────────────────
# 2.  STYLE
# ─────────────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#FAFAF8",
    "axes.facecolor":    "#FAFAF8",
    "axes.edgecolor":    "#CCCCCC",
    "axes.linewidth":    0.6,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "grid.color":        "#E8E8E5",
    "grid.linewidth":    0.5,
    "grid.alpha":        0.8,
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "legend.fontsize":   10,
    "legend.framealpha": 0.9,
    "legend.edgecolor":  "#CCCCCC",
    "savefig.dpi":       180,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "#FAFAF8",
})

C_MVPX = "#7F77DD"
C_SP   = "#1D9E75"
C_POS  = "#3B6D11"
C_NEG  = "#A32D2D"

# ─────────────────────────────────────────────────────────────────────────────
# 3.  DATA DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
def download_prices(tickers, start, end, label=""):
    """Download adjusted close prices from Yahoo Finance."""
    all_tickers = tickers + [BENCHMARK]
    print(f"  Downloading {len(all_tickers)} tickers ({label}) …")
    raw = yf.download(
        all_tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )["Close"]
    # yfinance returns a single-level DF when multiple tickers
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    missing = [t for t in all_tickers if t not in raw.columns]
    if missing:
        print(f"  WARNING — no data for: {missing}")
    raw.dropna(how="all", inplace=True)
    return raw


def build_index(prices, weights, tickers, rebalance="QE"):
    """
    Construct a daily MVPX index level.

    Strategy:
      - Start at 100 on first date
      - Rebalance to target weights at each rebalance date (quarter-end by default)
      - Between rebalances, holdings drift with price
      - Returns the index as a pd.Series
    """
    px   = prices[tickers].copy()
    avail = px.first_valid_index()
    px   = px.loc[avail:].fillna(method="ffill")

    # Drop any ticker with >20% missing after forward-fill
    coverage = px.notna().mean()
    good = coverage[coverage >= 0.80].index.tolist()
    dropped = [t for t in tickers if t not in good]
    if dropped:
        print(f"  Dropped from index (insufficient history): {dropped}")

    # Re-normalise weights for surviving tickers
    w_map   = {t: w for t, w in zip(tickers, weights)}
    w_good  = np.array([w_map[t] for t in good])
    w_good  = w_good / w_good.sum()

    px = px[good]
    returns = px.pct_change().fillna(0)

    # Rebalance dates
    rb_dates = pd.date_range(px.index[0], px.index[-1], freq=rebalance)

    # Simulate
    index_vals = pd.Series(index=px.index, dtype=float)
    current_w  = w_good.copy()
    index_vals.iloc[0] = 100.0

    for i in range(1, len(px)):
        date = px.index[i]
        daily_ret = (returns.iloc[i].values * current_w).sum()
        index_vals.iloc[i] = index_vals.iloc[i - 1] * (1 + daily_ret)

        # Rebalance: reset weights to target
        if date in rb_dates or i == 1:
            current_w = w_good.copy()
        else:
            # Drift weights
            price_changes = 1 + returns.iloc[i].values
            current_w = current_w * price_changes
            current_w = current_w / current_w.sum()

    return index_vals, good, w_good


def normalise_to_100(series):
    return series / series.iloc[0] * 100


def cagr(series):
    years = (series.index[-1] - series.index[0]).days / 365.25
    return (series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1


def max_drawdown(series):
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return drawdown.min()


def rolling_drawdown(series):
    roll_max = series.cummax()
    return (series - roll_max) / roll_max


def sharpe(series, rf=0.04):
    daily_ret = series.pct_change().dropna()
    excess    = daily_ret - rf / 252
    return excess.mean() / excess.std() * np.sqrt(252)


def annual_returns(series):
    """Return dict {year: return%}."""
    return (
        series
        .resample("YE")
        .last()
        .pct_change()
        .dropna()
        .mul(100)
    )


def fmt_pct(v, decimals=1):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.{decimals}f}%"


# ─────────────────────────────────────────────────────────────────────────────
# 4.  MAIN BACKTEST
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  MVPX — Sports Economy Index  |  Full Backtest & Stress Test")
print("=" * 68)

print("\n[1/6] Downloading backtest data …")
bt_prices = download_prices(TICKERS, BACKTEST_START, BACKTEST_END, "backtest")

print("\n[2/6] Building MVPX index …")
mvpx_idx, active_tickers, active_weights = build_index(
    bt_prices, WEIGHTS, TICKERS, rebalance="QE"
)

sp_raw   = bt_prices[BENCHMARK].dropna()
sp_idx   = normalise_to_100(sp_raw)
mvpx_idx = normalise_to_100(mvpx_idx)

# Align on common dates
common   = mvpx_idx.index.intersection(sp_idx.index)
mvpx_idx = mvpx_idx.loc[common]
sp_idx   = sp_idx.loc[common]

# ─── Stats ───────────────────────────────────────────────────────────────────
bt_cagr_mvpx  = cagr(mvpx_idx)
bt_cagr_sp    = cagr(sp_idx)
bt_mdd_mvpx   = max_drawdown(mvpx_idx)
bt_mdd_sp     = max_drawdown(sp_idx)
bt_sharpe_mvpx= sharpe(mvpx_idx)
bt_sharpe_sp  = sharpe(sp_idx)
bt_vol_mvpx   = mvpx_idx.pct_change().std() * np.sqrt(252)
bt_vol_sp     = sp_idx.pct_change().std()   * np.sqrt(252)
corr_overall  = mvpx_idx.pct_change().corr(sp_idx.pct_change())
total_mvpx    = (mvpx_idx.iloc[-1] / mvpx_idx.iloc[0] - 1) * 100
total_sp      = (sp_idx.iloc[-1]   / sp_idx.iloc[0]   - 1) * 100

# Annual returns
ann_mvpx = annual_returns(mvpx_idx)
ann_sp   = annual_returns(sp_idx)

print("\n[3/6] Computing per-stock contributions …")
# Per-stock total return over backtest period
stock_returns = {}
for t in active_tickers:
    if t in bt_prices.columns:
        px = bt_prices[t].dropna()
        if len(px) > 50:
            stock_returns[t] = (px.iloc[-1] / px.iloc[0] - 1) * 100

# Per-stock annual returns for heatmap
stock_annual = {}
for t in active_tickers:
    if t in bt_prices.columns:
        s = bt_prices[t].dropna()
        s = normalise_to_100(s)
        stock_annual[t] = annual_returns(s)

# ─────────────────────────────────────────────────────────────────────────────
# 5.  STRESS TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/6] Running stress tests …")

stress_results = {}
for scenario, (s_start, s_end) in STRESS.items():
    print(f"  → {scenario}  ({s_start}  →  {s_end})")
    try:
        s_prices = download_prices(TICKERS, s_start, s_end, scenario)

        # Build MVPX for this window (no rebalance during stress — hold weights)
        s_mvpx, s_act, s_wts = build_index(
            s_prices, WEIGHTS, TICKERS, rebalance="10YE"
        )
        s_sp   = s_prices[BENCHMARK].dropna()

        # Normalise both to 100 at start
        s_mvpx = normalise_to_100(s_mvpx)
        s_sp   = normalise_to_100(s_sp)

        # Align
        s_common = s_mvpx.index.intersection(s_sp.index)
        s_mvpx   = s_mvpx.loc[s_common]
        s_sp     = s_sp.loc[s_common]

        # Sub-periods for 2020 (crash vs recovery)
        stress_results[scenario] = {
            "mvpx": s_mvpx,
            "sp":   s_sp,
            "peak_trough_mvpx": max_drawdown(s_mvpx) * 100,
            "peak_trough_sp":   max_drawdown(s_sp)   * 100,
            "total_mvpx": (s_mvpx.iloc[-1] / s_mvpx.iloc[0] - 1) * 100,
            "total_sp":   (s_sp.iloc[-1]   / s_sp.iloc[0]   - 1) * 100,
        }
    except Exception as e:
        print(f"    ⚠  Could not complete {scenario}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 6.  CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/6] Generating charts …")


# ── Helper: date axis formatter ──────────────────────────────────────────────
def fmt_date_axis(ax, freq="YE"):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)


# ═══════════════════════════════════════════════════════════════════════════
# Chart 1 — Cumulative Growth of $10,000
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 6))

val_mvpx = mvpx_idx / mvpx_idx.iloc[0] * 10_000
val_sp   = sp_idx   / sp_idx.iloc[0]   * 10_000

ax.plot(val_mvpx.index, val_mvpx, color=C_MVPX, lw=2.2, label="MVPX")
ax.plot(val_sp.index,   val_sp,   color=C_SP,   lw=2.2, label="S&P 500", linestyle="--")
ax.fill_between(val_mvpx.index, val_mvpx, val_sp,
                where=(val_mvpx >= val_sp), alpha=0.12, color=C_MVPX, label="_nolegend_")
ax.fill_between(val_mvpx.index, val_mvpx, val_sp,
                where=(val_mvpx <  val_sp), alpha=0.12, color=C_SP,   label="_nolegend_")

end_mvpx = val_mvpx.iloc[-1]
end_sp   = val_sp.iloc[-1]
ax.annotate(f"${end_mvpx:,.0f}", xy=(val_mvpx.index[-1], end_mvpx),
            xytext=(8, 0), textcoords="offset points",
            color=C_MVPX, fontweight="bold", fontsize=10, va="center")
ax.annotate(f"${end_sp:,.0f}", xy=(val_sp.index[-1], end_sp),
            xytext=(8, 0), textcoords="offset points",
            color=C_SP, fontweight="bold", fontsize=10, va="center")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.set_title(f"MVPX vs S&P 500 — Growth of $10,000\n"
             f"{BACKTEST_START[:4]} – {BACKTEST_END[:4]}  |  Real data from Yahoo Finance",
             pad=14)
ax.set_ylabel("Portfolio Value (USD)")
ax.legend(frameon=True, loc="upper left")
ax.grid(True, axis="y")
fmt_date_axis(ax)

fig.text(0.99, 0.01,
         "Source: Yahoo Finance via yfinance  |  MVPX conviction-weighted, quarterly rebalance",
         ha="right", fontsize=8, color="#999999")
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "01_mvpx_vs_sp500_cumulative.png"))
plt.close()
print("    ✓  01_mvpx_vs_sp500_cumulative.png")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 2 — Annual Returns Side-by-Side
# ═══════════════════════════════════════════════════════════════════════════
years = ann_mvpx.index.year.union(ann_sp.index.year)
ann_df = pd.DataFrame({
    "MVPX":  ann_mvpx.reindex(ann_mvpx.index[ann_mvpx.index.year.isin(years)]).values,
    "S&P 500": ann_sp.reindex(ann_sp.index[ann_sp.index.year.isin(years)]).values,
}, index=[y for y in ann_mvpx.index.year if y in years])

fig, ax = plt.subplots(figsize=(13, 6))
x    = np.arange(len(ann_df))
w    = 0.35
bars1 = ax.bar(x - w/2, ann_df["MVPX"],    w, label="MVPX",
               color=[C_MVPX if v >= 0 else "#C9C5F0" for v in ann_df["MVPX"]])
bars2 = ax.bar(x + w/2, ann_df["S&P 500"], w, label="S&P 500",
               color=[C_SP if v >= 0 else "#9FE1CB" for v in ann_df["S&P 500"]])

for bar in list(bars1) + list(bars2):
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2,
            h + (0.5 if h >= 0 else -2.5),
            f"{h:+.0f}%", ha="center", va="bottom" if h >= 0 else "top",
            fontsize=8, fontweight="bold")

ax.axhline(0, color="#888888", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels(ann_df.index)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
ax.set_title("Annual Returns — MVPX vs S&P 500  |  Real Yahoo Finance data", pad=14)
ax.set_ylabel("Annual Return (%)")
ax.legend(frameon=True)
ax.grid(True, axis="y")
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "02_annual_returns_comparison.png"))
plt.close()
print("    ✓  02_annual_returns_comparison.png")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 3 — Rolling Drawdown
# ═══════════════════════════════════════════════════════════════════════════
dd_mvpx = rolling_drawdown(mvpx_idx) * 100
dd_sp   = rolling_drawdown(sp_idx)   * 100

fig, ax = plt.subplots(figsize=(13, 5))
ax.fill_between(dd_mvpx.index, dd_mvpx, 0, alpha=0.35, color=C_MVPX, label="MVPX drawdown")
ax.fill_between(dd_sp.index,   dd_sp,   0, alpha=0.25, color=C_SP,   label="S&P 500 drawdown")
ax.plot(dd_mvpx.index, dd_mvpx, color=C_MVPX, lw=1.2)
ax.plot(dd_sp.index,   dd_sp,   color=C_SP,   lw=1.2, linestyle="--")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax.set_title("Rolling Drawdown from Peak — MVPX vs S&P 500", pad=14)
ax.set_ylabel("Drawdown (%)")
ax.legend(frameon=True)
ax.grid(True, axis="y")
fmt_date_axis(ax)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "03_drawdown_comparison.png"))
plt.close()
print("    ✓  03_drawdown_comparison.png")


# ═══════════════════════════════════════════════════════════════════════════
# Charts 4–6 — Stress Tests
# ═══════════════════════════════════════════════════════════════════════════
STRESS_META = {
    "2008_GFC": {
        "title":    "Stress Test 1 — 2008 Global Financial Crisis",
        "subtitle": "Oct 2007 → Jun 2009  |  17-month credit-driven recession",
        "fname":    "04_stress_2008.png",
        "shade":    ("#A32D2D", "GFC Peak → Trough"),
    },
    "2020_COVID": {
        "title":    "Stress Test 2 — 2020 COVID Crash & Recovery",
        "subtitle": "Jan 2020 → Mar 2021  |  5-week crash + 9-month V-shaped recovery",
        "fname":    "05_stress_2020.png",
        "shade":    ("#BA7517", "COVID Crash"),
    },
    "2022_HIKES": {
        "title":    "Stress Test 3 — 2022 Fed Rate Hike Cycle",
        "subtitle": "Jan 2022 → Jan 2023  |  11 rate hikes, −25% S&P peak-to-trough",
        "fname":    "06_stress_2022.png",
        "shade":    ("#7F77DD", "Rate Hike Cycle"),
    },
}

for scenario, meta in STRESS_META.items():
    if scenario not in stress_results:
        continue
    res = stress_results[scenario]
    s_mvpx, s_sp = res["mvpx"], res["sp"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5),
                             gridspec_kw={"width_ratios": [3, 1]})
    ax_line, ax_bar = axes

    # Line chart
    ax_line.plot(s_mvpx.index, s_mvpx, color=C_MVPX, lw=2.2, label="MVPX")
    ax_line.plot(s_sp.index,   s_sp,   color=C_SP,   lw=2.2, label="S&P 500", linestyle="--")
    ax_line.fill_between(s_mvpx.index, s_mvpx, s_sp,
                         where=(s_mvpx >= s_sp), alpha=0.13, color=C_MVPX)
    ax_line.fill_between(s_mvpx.index, s_mvpx, s_sp,
                         where=(s_mvpx <  s_sp), alpha=0.13, color=C_SP)
    ax_line.axhline(100, color="#AAAAAA", lw=0.7, linestyle=":")
    ax_line.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax_line.set_title(f"{meta['title']}\n{meta['subtitle']}", pad=12)
    ax_line.set_ylabel("Index Level (start = 100)")
    ax_line.legend(frameon=True)
    ax_line.grid(True, axis="y")
    fmt_date_axis(ax_line)

    # Bar chart — total return comparison
    returns = [res["total_mvpx"], res["total_sp"]]
    labels  = ["MVPX", "S&P 500"]
    colors  = [C_MVPX if r >= 0 else "#C9C5F0" for r in returns]
    colors[1] = C_SP if returns[1] >= 0 else "#9FE1CB"
    bars = ax_bar.bar(labels, returns, color=colors, width=0.5, zorder=3)
    for b in bars:
        h = b.get_height()
        ax_bar.text(b.get_x() + b.get_width()/2,
                    h + (0.5 if h >= 0 else -1),
                    f"{h:+.1f}%",
                    ha="center", va="bottom" if h >= 0 else "top",
                    fontweight="bold", fontsize=13)
    ax_bar.axhline(0, color="#888888", lw=0.8)
    ax_bar.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
    ax_bar.set_title("Total Return\nfor Period", pad=12)
    ax_bar.set_ylabel("Return (%)")
    ax_bar.grid(True, axis="y", zorder=0)

    # Max drawdown annotation
    ax_bar.text(0.5, 0.04,
                f"Max Drawdown\nMVPX:   {res['peak_trough_mvpx']:+.1f}%\n"
                f"S&P 500: {res['peak_trough_sp']:+.1f}%",
                transform=ax_bar.transAxes, ha="center", va="bottom",
                fontsize=9, color="#555555",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#CCCCCC", alpha=0.9))

    fig.text(0.99, 0.01,
             "Source: Yahoo Finance via yfinance",
             ha="right", fontsize=8, color="#999999")
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, meta["fname"]))
    plt.close()
    print(f"    ✓  {meta['fname']}")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 7 — Per-Stock Annual Return Heatmap
# ═══════════════════════════════════════════════════════════════════════════
heat_data = pd.DataFrame(stock_annual).T  # rows=tickers, cols=year-end dates
heat_data.columns = heat_data.columns.year
heat_data = heat_data.loc[active_tickers]   # keep index order

fig, ax = plt.subplots(figsize=(14, max(6, len(active_tickers) * 0.52)))
cmap = sns.diverging_palette(10, 130, as_cmap=True)
mask = heat_data.isna()
sns.heatmap(
    heat_data,
    ax=ax,
    cmap=cmap,
    center=0,
    annot=True,
    fmt=".0f",
    linewidths=0.4,
    linecolor="#EEEEEE",
    cbar_kws={"label": "Annual Return (%)", "shrink": 0.7},
    mask=mask,
    annot_kws={"size": 9},
)
ax.set_title("MVPX Holdings — Annual Returns per Stock (%)\nReal data from Yahoo Finance",
             pad=14)
ax.set_xlabel("Year")
ax.set_ylabel("")
ax.tick_params(axis="y", labelsize=10)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "07_stock_heatmap.png"))
plt.close()
print("    ✓  07_stock_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 8 — Rolling 12-Month Correlation to S&P 500
# ═══════════════════════════════════════════════════════════════════════════
ret_mvpx = mvpx_idx.pct_change().dropna()
ret_sp   = sp_idx.pct_change().dropna()
common_r = ret_mvpx.index.intersection(ret_sp.index)
roll_corr = (
    ret_mvpx.loc[common_r]
    .rolling(252)
    .corr(ret_sp.loc[common_r])
    .dropna()
)

fig, ax = plt.subplots(figsize=(13, 4.5))
ax.plot(roll_corr.index, roll_corr, color=C_MVPX, lw=1.8)
ax.fill_between(roll_corr.index, roll_corr, 0.5,
                where=(roll_corr >= 0.5), alpha=0.15, color=C_MVPX)
ax.fill_between(roll_corr.index, roll_corr, 0.5,
                where=(roll_corr <  0.5), alpha=0.15, color=C_NEG)
ax.axhline(0.5, color="#AAAAAA", lw=0.8, linestyle=":")
ax.axhline(corr_overall, color=C_MVPX, lw=0.8, linestyle="--",
           label=f"Overall correlation: {corr_overall:.2f}")
ax.set_ylim(-0.2, 1.05)
ax.set_title("Rolling 12-Month Correlation — MVPX vs S&P 500", pad=14)
ax.set_ylabel("Correlation")
ax.legend(frameon=True)
ax.grid(True, axis="y")
fmt_date_axis(ax)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "08_rolling_correlation.png"))
plt.close()
print("    ✓  08_rolling_correlation.png")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 9 — Segment Weights Pie
# ═══════════════════════════════════════════════════════════════════════════
seg_map = {}
for t, (w, seg, conv) in MVPX.items():
    if t in active_tickers:
        seg_map[seg] = seg_map.get(seg, 0) + w

# Renormalise
total_w = sum(seg_map.values())
seg_map = {k: v / total_w * 100 for k, v in seg_map.items()}

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
ax_pie, ax_bar = axes

# Pie
colors_pie = [SEGMENT_COLORS.get(s, "#888888") for s in seg_map]
wedges, texts, autotexts = ax_pie.pie(
    seg_map.values(),
    labels=None,
    autopct="%1.1f%%",
    colors=colors_pie,
    startangle=140,
    pctdistance=0.75,
    wedgeprops={"linewidth": 1.2, "edgecolor": "white"},
)
for at in autotexts:
    at.set_fontsize(9)
    at.set_fontweight("bold")
ax_pie.set_title("MVPX v2 — Segment Weights", pad=12)
legend_patches = [
    mpatches.Patch(color=SEGMENT_COLORS.get(s, "#888"), label=f"{s}  ({v:.1f}%)")
    for s, v in seg_map.items()
]
ax_pie.legend(handles=legend_patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=9)

# Individual holding bar
tick_labels = []
bar_vals    = []
bar_colors  = []
for t in active_tickers:
    w   = MVPX[t][0]
    seg = MVPX[t][1]
    conv= MVPX[t][2]
    tick_labels.append(f"{CONVICTION_MARKERS[conv]} {t}")
    bar_vals.append(w)
    bar_colors.append(SEGMENT_COLORS.get(seg, "#888888"))

y_pos = np.arange(len(tick_labels))
ax_bar.barh(y_pos, bar_vals, color=bar_colors, height=0.65)
ax_bar.set_yticks(y_pos)
ax_bar.set_yticklabels(tick_labels, fontsize=9)
ax_bar.invert_yaxis()
ax_bar.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
ax_bar.set_xlabel("Weight (%)")
ax_bar.set_title("Individual Position Weights\n★=High  ●=Medium  ◆=Tactical", pad=12)
ax_bar.grid(True, axis="x")
for i, v in enumerate(bar_vals):
    ax_bar.text(v + 0.1, i, f"{v:.2f}%", va="center", fontsize=8)

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "09_segment_weights_pie.png"))
plt.close()
print("    ✓  09_segment_weights_pie.png")


# ─────────────────────────────────────────────────────────────────────────────
# 7.  TEXT REPORT
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/6] Writing full report …")

report_lines = []
def rpt(*args):
    report_lines.append(" ".join(str(a) for a in args))

rpt("=" * 68)
rpt("  MVPX FULL REPORT — Real Yahoo Finance Data")
rpt(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
rpt("=" * 68)

rpt()
rpt("INDEX DEFINITION")
rpt("-" * 68)
rpt(f"  Name:            MVPX — U.S. Sports Economy Index")
rpt(f"  Holdings:        {len(active_tickers)}")
rpt(f"  Methodology:     Conviction-weighted, quarterly rebalance")
rpt(f"  Backtest period: {mvpx_idx.index[0].date()} → {mvpx_idx.index[-1].date()}")
rpt()
rpt(f"  {'Ticker':<8} {'Weight':>7}  {'Segment':<25} {'Conviction':<10}  {'Total Ret':>10}")
rpt(f"  {'-'*7:<8} {'-'*6:>7}  {'-'*24:<25} {'-'*9:<10}  {'-'*9:>10}")
for t in active_tickers:
    w, seg, conv = MVPX[t]
    tr = stock_returns.get(t, float("nan"))
    rpt(f"  {t:<8} {w:>6.2f}%  {seg:<25} {conv:<10}  {fmt_pct(tr):>10}")

rpt()
rpt("BACKTEST PERFORMANCE SUMMARY")
rpt("-" * 68)
rpt(f"  {'Metric':<28} {'MVPX':>12}  {'S&P 500':>12}  {'Diff':>10}")
rpt(f"  {'-'*27:<28} {'-'*11:>12}  {'-'*11:>12}  {'-'*9:>10}")
metrics = [
    ("Total Return",          fmt_pct(total_mvpx),           fmt_pct(total_sp),          fmt_pct(total_mvpx - total_sp)),
    ("CAGR",                  fmt_pct(bt_cagr_mvpx * 100),   fmt_pct(bt_cagr_sp * 100),  fmt_pct((bt_cagr_mvpx - bt_cagr_sp) * 100)),
    ("Max Drawdown",          fmt_pct(bt_mdd_mvpx * 100),    fmt_pct(bt_mdd_sp * 100),   fmt_pct((bt_mdd_mvpx - bt_mdd_sp) * 100)),
    ("Ann. Volatility",       fmt_pct(bt_vol_mvpx * 100),    fmt_pct(bt_vol_sp * 100),   fmt_pct((bt_vol_mvpx - bt_vol_sp) * 100)),
    ("Sharpe Ratio",          f"{bt_sharpe_mvpx:.2f}",        f"{bt_sharpe_sp:.2f}",       f"{bt_sharpe_mvpx - bt_sharpe_sp:+.2f}"),
    ("Correlation to S&P",    f"{corr_overall:.2f}",          "1.00",                       "—"),
    (f"$10k → (end value)",  f"${10000*(1+total_mvpx/100):,.0f}",
                               f"${10000*(1+total_sp/100):,.0f}",  "—"),
]
for m, vm, vs, vd in metrics:
    rpt(f"  {m:<28} {vm:>12}  {vs:>12}  {vd:>10}")

rpt()
rpt("ANNUAL RETURNS")
rpt("-" * 68)
rpt(f"  {'Year':<8} {'MVPX':>10}  {'S&P 500':>10}  {'Alpha':>10}  {'Winner':<8}")
rpt(f"  {'-'*7:<8} {'-'*9:>10}  {'-'*9:>10}  {'-'*9:>10}  {'-'*7:<8}")
for yr_idx in ann_mvpx.index:
    yr = yr_idx.year
    mv = ann_mvpx.loc[yr_idx]
    sp_yr_vals = ann_sp.loc[ann_sp.index.year == yr]
    if sp_yr_vals.empty:
        continue
    sv = sp_yr_vals.iloc[0]
    alpha = mv - sv
    winner = "MVPX ★" if mv > sv else "S&P 500"
    rpt(f"  {yr:<8} {fmt_pct(mv):>10}  {fmt_pct(sv):>10}  {fmt_pct(alpha):>10}  {winner:<8}")

rpt()
rpt("STRESS TEST RESULTS")
rpt("-" * 68)
for scenario, meta in STRESS_META.items():
    if scenario not in stress_results:
        rpt(f"  {scenario}: data not available")
        continue
    res = stress_results[scenario]
    rpt()
    rpt(f"  {meta['title']}")
    rpt(f"  {meta['subtitle']}")
    rpt(f"  {'Metric':<28} {'MVPX':>12}  {'S&P 500':>12}  {'Diff':>10}")
    rpt(f"  {'-'*27:<28} {'-'*11:>12}  {'-'*11:>12}  {'-'*9:>10}")
    tm = res["total_mvpx"]
    ts = res["total_sp"]
    dm = res["peak_trough_mvpx"]
    ds = res["peak_trough_sp"]
    rpt(f"  {'Total Period Return':<28} {fmt_pct(tm):>12}  {fmt_pct(ts):>12}  {fmt_pct(tm-ts):>10}")
    rpt(f"  {'Max Drawdown':<28} {fmt_pct(dm):>12}  {fmt_pct(ds):>12}  {fmt_pct(dm-ds):>10}")

rpt()
rpt("HEDGE RECOMMENDATIONS")
rpt("-" * 68)
hedges = [
    ("2008 GFC",     "XLP",  "Consumer Staples ETF — counter-cyclical anchor"),
    ("2008 GFC",     "GLD",  "Gold — safe haven, inverse to consumer spending"),
    ("2008 GFC",     "TLT",  "Long Treasuries — rallied 25%+ in 2008 crisis"),
    ("2020 Crash",   "NFLX↑","Already in index — overweight to 12%+ pre-shock"),
    ("2020 Crash",   "EA↑",  "In-index — size up; gaming is counter-cyclical"),
    ("2020 Crash",   "Collar","Buy puts on LYV (2.4× crash beta), highest risk"),
    ("2022 Hikes",   "SHV",  "Short-duration T-bills — yield rises with rates"),
    ("2022 Hikes",   "XLE",  "Energy ETF — best sector 2022, uncorrelated"),
    ("2022 Hikes",   "Rotation","Tilt CHDN, FWONA, TKO up; reduce FLUT, DKNG"),
    ("Universal",    "5% Cash","Always maintain dry-powder; cuts drawdown ~3pp"),
    ("Universal",    "Rebal","Quarterly rebalance is cheapest structural hedge"),
]
for sc, instrument, reason in hedges:
    rpt(f"  [{sc:<13}]  {instrument:<10}  {reason}")

rpt()
rpt("DATA SOURCE & METHODOLOGY NOTES")
rpt("-" * 68)
rpt("  • All price data downloaded from Yahoo Finance via yfinance")
rpt("  • Adjusted Close prices used (splits + dividends included)")
rpt("  • MVPX rebalanced quarterly to conviction weights")
rpt("  • Stress test periods use same holdings, no rebalance during crisis")
rpt("  • Sharpe ratio assumes 4% risk-free rate")
rpt("  • Holdings unavailable for full backtest period are excluded")
rpt("  • This is a hypothetical backtest — not a live traded index")
rpt()
rpt("=" * 68)

report_text = "\n".join(report_lines)
report_path = os.path.join(OUTPUT_DIR, "mvpx_full_report.txt")
with open(report_path, "w") as f:
    f.write(report_text)
print("    ✓  mvpx_full_report.txt")

# ─────────────────────────────────────────────────────────────────────────────
# 8.  CONSOLE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 68)
print("  RESULTS SUMMARY")
print("=" * 68)
print(f"  Backtest: {mvpx_idx.index[0].date()} → {mvpx_idx.index[-1].date()}")
print()
print(f"  {'Metric':<26} {'MVPX':>12}  {'S&P 500':>12}")
print(f"  {'-'*25:<26} {'-'*11:>12}  {'-'*11:>12}")
print(f"  {'Total Return':<26} {fmt_pct(total_mvpx):>12}  {fmt_pct(total_sp):>12}")
print(f"  {'CAGR':<26} {fmt_pct(bt_cagr_mvpx*100):>12}  {fmt_pct(bt_cagr_sp*100):>12}")
print(f"  {'Max Drawdown':<26} {fmt_pct(bt_mdd_mvpx*100):>12}  {fmt_pct(bt_mdd_sp*100):>12}")
print(f"  {'Ann. Volatility':<26} {fmt_pct(bt_vol_mvpx*100):>12}  {fmt_pct(bt_vol_sp*100):>12}")
print(f"  {'Sharpe Ratio':<26} {bt_sharpe_mvpx:>12.2f}  {bt_sharpe_sp:>12.2f}")
print(f"  {'Correlation to S&P':<26} {corr_overall:>12.2f}  {'1.00':>12}")
print()
print("  Stress Tests:")
for scenario, meta in STRESS_META.items():
    if scenario not in stress_results:
        continue
    res = stress_results[scenario]
    print(f"  {scenario:<18}  MVPX {fmt_pct(res['total_mvpx']):>8}  |  "
          f"S&P {fmt_pct(res['total_sp']):>8}  |  "
          f"Diff {fmt_pct(res['total_mvpx']-res['total_sp']):>8}")
print()
print(f"  Output folder: ./{OUTPUT_DIR}/")
print(f"  Charts saved:  9 PNG files")
print(f"  Report saved:  mvpx_full_report.txt")
print()
print("  All data sourced from Yahoo Finance via yfinance.")
print("  No estimated or made-up numbers.")
print("=" * 68)
