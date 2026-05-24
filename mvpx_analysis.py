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
    01_mvpx_vs_sp500_cumulative.png
    02_annual_returns_comparison.png
    03_drawdown_comparison.png
    04_stress_2008.png
    05_stress_2020.png
    06_stress_2022.png
    07_stock_heatmap.png
    08_rolling_correlation.png
    09_segment_weights_pie.png
    10_risk_return_scatter.png   (NEW)
    11_rolling_sharpe.png        (NEW)
    12_monthly_return_heatmap.png(NEW)
    mvpx_full_report.txt
================================================================================
"""

import os
import time
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import seaborn as sns

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("Run: pip install yfinance pandas numpy matplotlib seaborn scipy")

# ─────────────────────────────────────────────────────────────────────────────
# 0.  OUTPUT DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "mvpx_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  INDEX DEFINITION
# ─────────────────────────────────────────────────────────────────────────────
MVPX = {
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

TICKERS        = list(MVPX.keys())
WEIGHTS        = np.array([MVPX[t][0] / 100 for t in TICKERS])
BENCHMARK      = "^GSPC"
BACKTEST_START = "2019-01-01"
BACKTEST_END   = datetime.today().strftime("%Y-%m-%d")

STRESS = {
    "2008_GFC":   ("2007-10-01", "2009-06-30"),
    "2020_COVID": ("2020-01-01", "2021-03-31"),
    "2022_HIKES": ("2022-01-01", "2023-01-31"),
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
# 3.  RATE-LIMIT-SAFE DOWNLOAD
#     Downloads in batches of 4 with a 3-second pause between batches,
#     and retries each batch up to 3 times on a rate-limit error.
# ─────────────────────────────────────────────────────────────────────────────
BATCH_SIZE  = 4      # tickers per request
BATCH_PAUSE = 3.0    # seconds between batches
RETRY_WAIT  = 15.0   # seconds to wait after a rate-limit hit
MAX_RETRIES = 3

def download_prices(tickers, start, end, label=""):
    all_tickers = list(dict.fromkeys(tickers + [BENCHMARK]))
    print(f"  Downloading {len(all_tickers)} tickers ({label}) in batches of {BATCH_SIZE} …")

    frames = []
    batches = [all_tickers[i:i+BATCH_SIZE] for i in range(0, len(all_tickers), BATCH_SIZE)]

    for b_idx, batch in enumerate(batches):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw = yf.download(
                    batch,
                    start=start,
                    end=end,
                    auto_adjust=True,
                    progress=False,
                    threads=False,   # serial within batch avoids secondary limit
                )["Close"]
                if isinstance(raw, pd.Series):
                    raw = raw.to_frame(name=batch[0])
                frames.append(raw)
                print(f"    batch {b_idx+1}/{len(batches)} ✓  ({', '.join(batch)})")
                break
            except Exception as e:
                msg = str(e)
                if "Rate" in msg or "429" in msg or "Too Many" in msg:
                    wait = RETRY_WAIT * attempt
                    print(f"    batch {b_idx+1} rate-limited — waiting {wait:.0f}s (attempt {attempt}/{MAX_RETRIES}) …")
                    time.sleep(wait)
                else:
                    print(f"    batch {b_idx+1} error: {e}")
                    break
        else:
            print(f"    batch {b_idx+1} skipped after {MAX_RETRIES} retries.")

        if b_idx < len(batches) - 1:
            time.sleep(BATCH_PAUSE)

    if not frames:
        raise RuntimeError("No data downloaded. Check your internet connection and try again in a minute.")

    prices = pd.concat(frames, axis=1)
    prices = prices.loc[:, ~prices.columns.duplicated()]
    prices.dropna(how="all", inplace=True)

    missing = [t for t in all_tickers if t not in prices.columns]
    if missing:
        print(f"  WARNING — still missing after retries: {missing}")

    return prices


# ─────────────────────────────────────────────────────────────────────────────
# 4.  INDEX & STAT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def build_index(prices, weights, tickers, rebalance="QE"):
    available = [t for t in tickers if t in prices.columns]
    px = prices[available].copy()
    if px.empty:
        raise RuntimeError("build_index: no valid tickers in price data.")

    px = px.ffill()

    coverage = px.notna().mean()
    good     = coverage[coverage >= 0.80].index.tolist()
    dropped  = [t for t in available if t not in good]
    if dropped:
        print(f"  Dropped (< 80% coverage): {dropped}")
    if not good:
        raise RuntimeError("build_index: no tickers with sufficient history.")

    w_map  = {t: w for t, w in zip(tickers, weights)}
    w_good = np.array([w_map[t] for t in good if t in w_map])
    w_good = w_good / w_good.sum()

    px      = px[good]
    returns = px.pct_change().fillna(0)

    rb_dates   = pd.date_range(px.index[0], px.index[-1], freq=rebalance)
    index_vals = pd.Series(index=px.index, dtype=float)
    current_w  = w_good.copy()
    index_vals.iloc[0] = 100.0

    for i in range(1, len(px)):
        date      = px.index[i]
        daily_ret = (returns.iloc[i].values * current_w).sum()
        index_vals.iloc[i] = index_vals.iloc[i-1] * (1 + daily_ret)
        if date in rb_dates or i == 1:
            current_w = w_good.copy()
        else:
            pc        = 1 + returns.iloc[i].values
            current_w = current_w * pc
            current_w = current_w / current_w.sum()

    return index_vals, good, w_good


def normalise(s):
    return s / s.iloc[0] * 100

def cagr(s):
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1

def max_dd(s):
    return ((s - s.cummax()) / s.cummax()).min()

def roll_dd(s):
    return (s - s.cummax()) / s.cummax()

def sharpe(s, rf=0.04):
    dr = s.pct_change().dropna()
    ex = dr - rf / 252
    return ex.mean() / ex.std() * np.sqrt(252)

def rolling_sharpe(s, window=252, rf=0.04):
    dr = s.pct_change()
    ex = dr - rf / 252
    return (ex.rolling(window).mean() / ex.rolling(window).std()) * np.sqrt(252)

def ann_returns(s):
    return s.resample("YE").last().pct_change().dropna().mul(100)

def fmt(v, d=1):
    return f"{'+'if v>=0 else ''}{v:.{d}f}%"

def fmt_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  MAIN BACKTEST
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*68)
print("  MVPX — Sports Economy Index  |  Full Backtest & Stress Test")
print("="*68)

print("\n[1] Downloading data …")
bt_prices = download_prices(TICKERS, BACKTEST_START, BACKTEST_END, "backtest")

print("\n[2] Building index …")
mi, active, aw = build_index(bt_prices, WEIGHTS, TICKERS)

sp_raw = bt_prices[BENCHMARK].dropna()
sp_idx = normalise(sp_raw)
mi     = normalise(mi)

common = mi.index.intersection(sp_idx.index)
mi     = mi.loc[common]
sp_idx = sp_idx.loc[common]

# Stats
cagr_mi  = cagr(mi);        cagr_sp  = cagr(sp_idx)
mdd_mi   = max_dd(mi);      mdd_sp   = max_dd(sp_idx)
shr_mi   = sharpe(mi);      shr_sp   = sharpe(sp_idx)
vol_mi   = mi.pct_change().std() * np.sqrt(252)
vol_sp   = sp_idx.pct_change().std() * np.sqrt(252)
corr_all = mi.pct_change().corr(sp_idx.pct_change())
tot_mi   = (mi.iloc[-1]   / mi.iloc[0]   - 1) * 100
tot_sp   = (sp_idx.iloc[-1] / sp_idx.iloc[0] - 1) * 100
ann_mi   = ann_returns(mi)
ann_sp   = ann_returns(sp_idx)

print("\n[3] Per-stock stats …")
stock_ret = {}
stock_ann = {}
for t in active:
    if t in bt_prices.columns:
        px = bt_prices[t].dropna()
        if len(px) > 50:
            stock_ret[t] = (px.iloc[-1] / px.iloc[0] - 1) * 100
            stock_ann[t] = ann_returns(normalise(px))

# ─────────────────────────────────────────────────────────────────────────────
# 6.  STRESS TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Stress tests …")
stress_res = {}
STRESS_META = {
    "2008_GFC":   {"title":"Stress Test 1 — 2008 GFC",             "subtitle":"Oct 2007→Jun 2009",   "fname":"04_stress_2008.png"},
    "2020_COVID": {"title":"Stress Test 2 — 2020 COVID",           "subtitle":"Jan 2020→Mar 2021",   "fname":"05_stress_2020.png"},
    "2022_HIKES": {"title":"Stress Test 3 — 2022 Rate Hikes",      "subtitle":"Jan 2022→Jan 2023",   "fname":"06_stress_2022.png"},
}
for sc, (s0, s1) in STRESS.items():
    print(f"  → {sc}")
    try:
        sp = download_prices(TICKERS, s0, s1, sc)
        sm, _, _ = build_index(sp, WEIGHTS, TICKERS, rebalance="10YE")
        ss = sp[BENCHMARK].dropna()
        sm = normalise(sm);  ss = normalise(ss)
        c  = sm.index.intersection(ss.index)
        sm = sm.loc[c];      ss = ss.loc[c]
        stress_res[sc] = {
            "mvpx": sm, "sp": ss,
            "pt_mi": max_dd(sm)*100, "pt_sp": max_dd(ss)*100,
            "tot_mi": (sm.iloc[-1]/sm.iloc[0]-1)*100,
            "tot_sp": (ss.iloc[-1]/ss.iloc[0]-1)*100,
        }
    except Exception as e:
        print(f"    ⚠  {sc}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 7.  CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Charts …")

# ── Chart 1: Cumulative growth ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13,6))
vm = mi   / mi.iloc[0]   * 10_000
vs = sp_idx / sp_idx.iloc[0] * 10_000
ax.plot(vm.index, vm, color=C_MVPX, lw=2.2, label="MVPX")
ax.plot(vs.index, vs, color=C_SP,   lw=2.2, label="S&P 500", linestyle="--")
ax.fill_between(vm.index, vm, vs, where=(vm>=vs), alpha=.12, color=C_MVPX)
ax.fill_between(vm.index, vm, vs, where=(vm<vs),  alpha=.12, color=C_SP)
ax.annotate(f"${vm.iloc[-1]:,.0f}", xy=(vm.index[-1], vm.iloc[-1]), xytext=(8,0),
            textcoords="offset points", color=C_MVPX, fontweight="bold", fontsize=10, va="center")
ax.annotate(f"${vs.iloc[-1]:,.0f}", xy=(vs.index[-1], vs.iloc[-1]), xytext=(8,0),
            textcoords="offset points", color=C_SP,   fontweight="bold", fontsize=10, va="center")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x:,.0f}"))
ax.set_title(f"MVPX vs S&P 500 — Growth of $10,000\n{BACKTEST_START[:4]}–{BACKTEST_END[:4]}  |  Yahoo Finance", pad=14)
ax.set_ylabel("Portfolio Value (USD)")
ax.legend(frameon=True, loc="upper left")
ax.grid(True, axis="y")
fmt_date_axis(ax)
fig.text(0.99,0.01,"Source: Yahoo Finance via yfinance | MVPX conviction-weighted, quarterly rebalance",
         ha="right", fontsize=8, color="#999")
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"01_mvpx_vs_sp500_cumulative.png")); plt.close()
print("    ✓  01")

# ── Chart 2: Annual returns ─────────────────────────────────────────────────
yr_set = ann_mi.index.year.union(ann_sp.index.year)
adf = pd.DataFrame({
    "MVPX":    ann_mi.reindex(ann_mi.index[ann_mi.index.year.isin(yr_set)]).values,
    "S&P 500": ann_sp.reindex(ann_sp.index[ann_sp.index.year.isin(yr_set)]).values,
}, index=[y for y in ann_mi.index.year if y in yr_set])

fig, ax = plt.subplots(figsize=(13,6))
x, w = np.arange(len(adf)), 0.35
b1 = ax.bar(x-w/2, adf["MVPX"],    w, label="MVPX",
            color=[C_MVPX if v>=0 else "#C9C5F0" for v in adf["MVPX"]])
b2 = ax.bar(x+w/2, adf["S&P 500"], w, label="S&P 500",
            color=[C_SP if v>=0 else "#9FE1CB" for v in adf["S&P 500"]])
for bar in list(b1)+list(b2):
    h = bar.get_height()
    ax.text(bar.get_x()+bar.get_width()/2, h+(0.5 if h>=0 else -2.5),
            f"{h:+.0f}%", ha="center", va="bottom" if h>=0 else "top", fontsize=8, fontweight="bold")
ax.axhline(0, color="#888", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(adf.index)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:+.0f}%"))
ax.set_title("Annual Returns — MVPX vs S&P 500", pad=14)
ax.set_ylabel("Annual Return (%)")
ax.legend(frameon=True); ax.grid(True, axis="y")
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"02_annual_returns_comparison.png")); plt.close()
print("    ✓  02")

# ── Chart 3: Rolling drawdown ───────────────────────────────────────────────
dd_mi = roll_dd(mi)*100
dd_sp = roll_dd(sp_idx)*100
fig, ax = plt.subplots(figsize=(13,5))
ax.fill_between(dd_mi.index, dd_mi, 0, alpha=.35, color=C_MVPX, label="MVPX")
ax.fill_between(dd_sp.index, dd_sp, 0, alpha=.25, color=C_SP,   label="S&P 500")
ax.plot(dd_mi.index, dd_mi, color=C_MVPX, lw=1.2)
ax.plot(dd_sp.index, dd_sp, color=C_SP,   lw=1.2, linestyle="--")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
ax.set_title("Rolling Drawdown from Peak — MVPX vs S&P 500", pad=14)
ax.set_ylabel("Drawdown (%)"); ax.legend(frameon=True); ax.grid(True, axis="y")
fmt_date_axis(ax); plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"03_drawdown_comparison.png")); plt.close()
print("    ✓  03")

# ── Charts 4-6: Stress tests ────────────────────────────────────────────────
for sc, meta in STRESS_META.items():
    if sc not in stress_res: continue
    r = stress_res[sc]
    sm, ss = r["mvpx"], r["sp"]
    fig, (al, ab) = plt.subplots(1,2,figsize=(14,5.5),gridspec_kw={"width_ratios":[3,1]})
    al.plot(sm.index, sm, color=C_MVPX, lw=2.2, label="MVPX")
    al.plot(ss.index, ss, color=C_SP,   lw=2.2, label="S&P 500", linestyle="--")
    al.fill_between(sm.index, sm, ss, where=(sm>=ss), alpha=.13, color=C_MVPX)
    al.fill_between(sm.index, sm, ss, where=(sm<ss),  alpha=.13, color=C_SP)
    al.axhline(100, color="#AAA", lw=.7, linestyle=":")
    al.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}"))
    al.set_title(f"{meta['title']}\n{meta['subtitle']}", pad=12)
    al.set_ylabel("Index (start=100)"); al.legend(frameon=True); al.grid(True,axis="y")
    fmt_date_axis(al)
    rets   = [r["tot_mi"], r["tot_sp"]]
    cols   = [C_MVPX if rets[0]>=0 else "#C9C5F0", C_SP if rets[1]>=0 else "#9FE1CB"]
    bars   = ab.bar(["MVPX","S&P 500"], rets, color=cols, width=.5, zorder=3)
    for b in bars:
        h = b.get_height()
        ab.text(b.get_x()+b.get_width()/2, h+(0.5 if h>=0 else -1), f"{h:+.1f}%",
                ha="center", va="bottom" if h>=0 else "top", fontweight="bold", fontsize=13)
    ab.axhline(0, color="#888", lw=.8)
    ab.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:+.0f}%"))
    ab.set_title("Total Return", pad=12); ab.set_ylabel("Return (%)"); ab.grid(True,axis="y",zorder=0)
    ab.text(.5,.04,f"Max DD\nMVPX: {r['pt_mi']:+.1f}%\nS&P: {r['pt_sp']:+.1f}%",
            transform=ab.transAxes, ha="center", va="bottom", fontsize=9, color="#555",
            bbox=dict(boxstyle="round,pad=.4",facecolor="white",edgecolor="#CCC",alpha=.9))
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, meta["fname"])); plt.close()
    print(f"    ✓  {meta['fname']}")

# ── Chart 7: Per-stock heatmap ──────────────────────────────────────────────
heat = pd.DataFrame(stock_ann).T
heat.columns = heat.columns.year
heat = heat.reindex([t for t in active if t in heat.index])
fig, ax = plt.subplots(figsize=(14, max(6, len(heat)*0.52)))
sns.heatmap(heat, ax=ax, cmap=sns.diverging_palette(10,130,as_cmap=True),
            center=0, annot=True, fmt=".0f", linewidths=.4, linecolor="#EEE",
            cbar_kws={"label":"Annual Return (%)","shrink":.7},
            mask=heat.isna(), annot_kws={"size":9})
ax.set_title("MVPX Holdings — Annual Returns per Stock (%)", pad=14)
ax.set_xlabel("Year"); ax.tick_params(axis="y", labelsize=10)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"07_stock_heatmap.png")); plt.close()
print("    ✓  07")

# ── Chart 8: Rolling correlation ────────────────────────────────────────────
r_mi = mi.pct_change().dropna()
r_sp = sp_idx.pct_change().dropna()
rc   = r_mi.loc[r_mi.index.intersection(r_sp.index)].rolling(252).corr(
       r_sp.loc[r_mi.index.intersection(r_sp.index)]).dropna()
fig, ax = plt.subplots(figsize=(13,4.5))
ax.plot(rc.index, rc, color=C_MVPX, lw=1.8)
ax.fill_between(rc.index, rc, .5, where=(rc>=.5), alpha=.15, color=C_MVPX)
ax.fill_between(rc.index, rc, .5, where=(rc<.5),  alpha=.15, color=C_NEG)
ax.axhline(.5, color="#AAA", lw=.8, linestyle=":")
ax.axhline(corr_all, color=C_MVPX, lw=.8, linestyle="--",
           label=f"Overall: {corr_all:.2f}")
ax.set_ylim(-.2, 1.05)
ax.set_title("Rolling 12-Month Correlation — MVPX vs S&P 500", pad=14)
ax.set_ylabel("Correlation"); ax.legend(frameon=True); ax.grid(True,axis="y")
fmt_date_axis(ax); plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"08_rolling_correlation.png")); plt.close()
print("    ✓  08")

# ── Chart 9: Segment weights ────────────────────────────────────────────────
seg_map = {}
for t,(w,seg,_) in MVPX.items():
    if t in active: seg_map[seg] = seg_map.get(seg,0)+w
total_w  = sum(seg_map.values())
seg_map  = {k: v/total_w*100 for k,v in seg_map.items()}

fig, (ap, ab2) = plt.subplots(1,2,figsize=(14,5.5))
cpie = [SEGMENT_COLORS.get(s,"#888") for s in seg_map]
_, _, autotexts = ap.pie(seg_map.values(), labels=None, autopct="%1.1f%%",
                         colors=cpie, startangle=140, pctdistance=.75,
                         wedgeprops={"linewidth":1.2,"edgecolor":"white"})
for at in autotexts: at.set_fontsize(9); at.set_fontweight("bold")
ap.set_title("MVPX — Segment Weights", pad=12)
ap.legend(handles=[mpatches.Patch(color=SEGMENT_COLORS.get(s,"#888"),label=f"{s} ({v:.1f}%)")
                   for s,v in seg_map.items()],
          loc="lower center", bbox_to_anchor=(.5,-.18), ncol=2, fontsize=9)

tlabels, bvals, bcols = [], [], []
for t in active:
    tlabels.append(f"{CONVICTION_MARKERS[MVPX[t][2]]} {t}")
    bvals.append(MVPX[t][0])
    bcols.append(SEGMENT_COLORS.get(MVPX[t][1],"#888"))
yp = np.arange(len(tlabels))
ab2.barh(yp, bvals, color=bcols, height=.65)
ab2.set_yticks(yp); ab2.set_yticklabels(tlabels, fontsize=9); ab2.invert_yaxis()
ab2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.1f}%"))
ab2.set_xlabel("Weight (%)"); ab2.grid(True, axis="x")
ab2.set_title("Position Weights\n★=High  ●=Medium  ◆=Tactical", pad=12)
for i,v in enumerate(bvals): ab2.text(v+.1, i, f"{v:.2f}%", va="center", fontsize=8)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"09_segment_weights_pie.png")); plt.close()
print("    ✓  09")

# ── Chart 10 (NEW): Risk / Return scatter ───────────────────────────────────
print("    Building 10 — risk/return scatter …")
scatter = []
for t in active:
    if t not in bt_prices.columns: continue
    px = bt_prices[t].dropna()
    if len(px) < 100: continue
    dr     = px.pct_change().dropna()
    ar     = (px.iloc[-1]/px.iloc[0])**(252/len(px)) - 1
    av     = dr.std() * np.sqrt(252)
    scatter.append({"t":t, "ret":ar*100, "vol":av*100,
                    "seg":MVPX[t][1], "wt":MVPX[t][0]})

sp_ar = (sp_raw.iloc[-1]/sp_raw.iloc[0])**(252/len(sp_raw)) - 1
sp_av = sp_raw.pct_change().dropna().std() * np.sqrt(252)

fig, ax = plt.subplots(figsize=(13,7))
ax.axvline(sp_av*100, color="#AAA", lw=.8, linestyle=":", label="S&P 500 vol")
ax.axhline(sp_ar*100, color="#AAA", lw=.8, linestyle=":", label="S&P 500 return")

for row in scatter:
    c = SEGMENT_COLORS.get(row["seg"],"#888")
    s = 80 + row["wt"]*25
    ax.scatter(row["vol"], row["ret"], s=s, color=c, alpha=.82,
               edgecolors="white", linewidths=.8, zorder=3)
    ax.annotate(row["t"], xy=(row["vol"],row["ret"]),
                xytext=(4,4), textcoords="offset points", fontsize=8, color="#333", zorder=4)

ax.scatter(sp_av*100, sp_ar*100, s=220, marker="D", color=C_SP,
           edgecolors="white", linewidths=1.2, zorder=5, label="S&P 500")
ax.annotate("S&P 500", xy=(sp_av*100,sp_ar*100),
            xytext=(6,-12), textcoords="offset points",
            fontsize=9, color=C_SP, fontweight="bold")

ax.legend(handles=[mpatches.Patch(color=SEGMENT_COLORS[s],label=s) for s in SEGMENT_COLORS]
                  +[mpatches.Patch(color=C_SP,label="S&P 500")],
          fontsize=9, frameon=True, loc="lower right", title="Segment", title_fontsize=9)
ax.set_xlabel("Annualised Volatility (%)")
ax.set_ylabel("Annualised Return (%)")
ax.set_title("Risk / Return — MVPX Holdings vs S&P 500\n"
             "Bubble size = index weight  |  Real Yahoo Finance data", pad=14)
ax.grid(True, alpha=.4)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"10_risk_return_scatter.png")); plt.close()
print("    ✓  10")

# ── Chart 11 (NEW): Rolling 12-month Sharpe ─────────────────────────────────
print("    Building 11 — rolling Sharpe …")
rs_mi = rolling_sharpe(mi).dropna()
rs_sp = rolling_sharpe(sp_idx).dropna()
csh   = rs_mi.index.intersection(rs_sp.index)
rs_mi = rs_mi.loc[csh]; rs_sp = rs_sp.loc[csh]

fig, ax = plt.subplots(figsize=(13,5))
ax.plot(rs_mi.index, rs_mi, color=C_MVPX, lw=2.0, label="MVPX Sharpe")
ax.plot(rs_sp.index, rs_sp, color=C_SP,   lw=2.0, label="S&P 500 Sharpe", linestyle="--")
ax.fill_between(rs_mi.index, rs_mi, rs_sp, where=(rs_mi>=rs_sp), alpha=.18, color=C_MVPX,
                label="MVPX leads (risk-adj.)")
ax.fill_between(rs_mi.index, rs_mi, rs_sp, where=(rs_mi<rs_sp),  alpha=.12, color=C_SP,
                label="S&P 500 leads (risk-adj.)")
ax.axhline(0, color="#AAA", lw=.8, linestyle=":")
ax.axhline(1, color="#CCC", lw=.6, linestyle=":", label="Sharpe = 1")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.1f}"))
ax.set_title("Rolling 12-Month Sharpe Ratio — MVPX vs S&P 500\nRF = 4%", pad=14)
ax.set_ylabel("Sharpe Ratio")
ax.legend(frameon=True, fontsize=9, ncol=2); ax.grid(True, axis="y")
fmt_date_axis(ax)
fig.text(0.99,0.01,"Source: Yahoo Finance via yfinance",ha="right",fontsize=8,color="#999")
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"11_rolling_sharpe.png")); plt.close()
print("    ✓  11")

# ── Chart 12 (NEW): Monthly return calendar heatmap ─────────────────────────
print("    Building 12 — monthly return heatmap …")
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def to_cal(s):
    m = s.resample("ME").last().pct_change().dropna()*100
    df = pd.DataFrame({"yr":m.index.year,"mo":m.index.month,"v":m.values})
    return df.pivot(index="mo", columns="yr", values="v")

cal_mi = to_cal(mi)
cal_sp = to_cal(sp_idx)

fig, axes = plt.subplots(1,2,figsize=(16,6))
for ax, cal, title in zip(axes, [cal_mi,cal_sp],
                           ["MVPX — Monthly Returns (%)","S&P 500 — Monthly Returns (%)"]):
    sns.heatmap(cal, ax=ax, cmap=sns.diverging_palette(10,130,as_cmap=True),
                center=0, annot=True, fmt=".1f", linewidths=.4, linecolor="#EEE",
                cbar_kws={"label":"Monthly Return (%)","shrink":.8},
                mask=cal.isna(), annot_kws={"size":8}, vmin=-15, vmax=15)
    ax.set_yticklabels([MONTHS[i-1] for i in cal.index], rotation=0, fontsize=9)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, fontsize=9)
    ax.set_xlabel("Year"); ax.set_ylabel(""); ax.set_title(title, pad=12)
fig.suptitle("Monthly Return Calendar — MVPX vs S&P 500\nRed=negative  Green=positive",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR,"12_monthly_return_heatmap.png")); plt.close()
print("    ✓  12")

# ─────────────────────────────────────────────────────────────────────────────
# 8.  TEXT REPORT
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Writing report …")
lines = []
def rpt(*a): lines.append(" ".join(str(x) for x in a))

rpt("="*68)
rpt("  MVPX FULL REPORT — Real Yahoo Finance Data")
rpt(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
rpt("="*68)
rpt(); rpt("INDEX DEFINITION"); rpt("-"*68)
rpt(f"  Name:      MVPX — U.S. Sports Economy Index")
rpt(f"  Holdings:  {len(active)}")
rpt(f"  Period:    {mi.index[0].date()} → {mi.index[-1].date()}")
rpt()
rpt(f"  {'Ticker':<8} {'Weight':>7}  {'Segment':<25} {'Conv':<10}  {'Total Ret':>10}")
rpt(f"  {'-'*68}")
for t in active:
    w,seg,cv = MVPX[t]
    tr = stock_ret.get(t, float("nan"))
    rpt(f"  {t:<8} {w:>6.2f}%  {seg:<25} {cv:<10}  {fmt(tr):>10}")

rpt(); rpt("PERFORMANCE SUMMARY"); rpt("-"*68)
rpt(f"  {'Metric':<28} {'MVPX':>12}  {'S&P 500':>12}  {'Diff':>10}")
for label, vm, vs, vd in [
    ("Total Return",     fmt(tot_mi),           fmt(tot_sp),           fmt(tot_mi-tot_sp)),
    ("CAGR",            fmt(cagr_mi*100),       fmt(cagr_sp*100),      fmt((cagr_mi-cagr_sp)*100)),
    ("Max Drawdown",    fmt(mdd_mi*100),        fmt(mdd_sp*100),       fmt((mdd_mi-mdd_sp)*100)),
    ("Ann. Volatility", fmt(vol_mi*100),        fmt(vol_sp*100),       fmt((vol_mi-vol_sp)*100)),
    ("Sharpe",          f"{shr_mi:.2f}",         f"{shr_sp:.2f}",       f"{shr_mi-shr_sp:+.2f}"),
    ("Correlation",     f"{corr_all:.2f}",       "1.00",                "—"),
]:
    rpt(f"  {label:<28} {vm:>12}  {vs:>12}  {vd:>10}")

rpt(); rpt("ANNUAL RETURNS"); rpt("-"*68)
for yi in ann_mi.index:
    mv = ann_mi.loc[yi]
    sp_row = ann_sp.loc[ann_sp.index.year == yi.year]
    if sp_row.empty: continue
    sv = sp_row.iloc[0]
    rpt(f"  {yi.year}  MVPX {fmt(mv):>8}  S&P {fmt(sv):>8}  Alpha {fmt(mv-sv):>8}  {'★ MVPX' if mv>sv else 'S&P 500'}")

rpt(); rpt("STRESS TESTS"); rpt("-"*68)
for sc, meta in STRESS_META.items():
    if sc not in stress_res: continue
    r = stress_res[sc]
    rpt(f"\n  {meta['title']}")
    rpt(f"  Total return — MVPX {fmt(r['tot_mi']):>8}  S&P {fmt(r['tot_sp']):>8}  Diff {fmt(r['tot_mi']-r['tot_sp']):>8}")
    rpt(f"  Max drawdown — MVPX {fmt(r['pt_mi']):>8}  S&P {fmt(r['pt_sp']):>8}")

rpt(); rpt("="*68)
with open(os.path.join(OUTPUT_DIR,"mvpx_full_report.txt"),"w") as f:
    f.write("\n".join(lines))
print("    ✓  mvpx_full_report.txt")

# ─────────────────────────────────────────────────────────────────────────────
# 9.  SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7] Done.")
print("="*68)
print(f"  Backtest: {mi.index[0].date()} → {mi.index[-1].date()}")
print(f"  {'Total Return':<24} MVPX {fmt(tot_mi):>10}   S&P {fmt(tot_sp):>10}")
print(f"  {'CAGR':<24} MVPX {fmt(cagr_mi*100):>10}   S&P {fmt(cagr_sp*100):>10}")
print(f"  {'Sharpe':<24} MVPX {shr_mi:>10.2f}   S&P {shr_sp:>10.2f}")
print(f"  {'Max Drawdown':<24} MVPX {fmt(mdd_mi*100):>10}   S&P {fmt(mdd_sp*100):>10}")
print()
print("  Charts saved: 12 PNGs + mvpx_full_report.txt")
print(f"  Output: ./{OUTPUT_DIR}/")
print("="*68)