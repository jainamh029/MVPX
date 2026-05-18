# MVPX — U.S. Sports Economy Index

> A custom, conviction-weighted thematic index tracking 18 US-listed companies across the full sports economy — broadcasting, leagues & venues, apparel & equipment, gaming & betting, sponsorship & media, and motorsport.

---

## What is MVPX?

MVPX is a **hypothetical thematic index** built to capture the performance of the US sports economy as a single investable portfolio. It covers every layer of the sports business — from live event operators and combat sports franchises to sports betting platforms, premium apparel brands, streaming rights holders, and Formula 1.

The index is **conviction-weighted**, not market-cap weighted. Higher-conviction picks carry more weight regardless of company size, which concentrates exposure to the strongest structural tailwinds in the theme.

> ⚠️ **Disclaimer:** MVPX is a research and educational project. It is not a real traded index, ETF, or investment product. Nothing in this repository constitutes investment advice. All backtests are hypothetical and based on historical data that does not guarantee future results.

---

## Index Construction

| Parameter | Value |
|---|---|
| Holdings | 18 stocks |
| Segments | 6 |
| Methodology | Conviction-weighted |
| Rebalance frequency | Quarterly |
| Benchmark | S&P 500 (`^GSPC`) |
| Data source | Yahoo Finance via `yfinance` |
| Backtest start | 2019-01-01 |

### Holdings & Weights

| Ticker | Company | Weight | Segment | Conviction |
|---|---|---|---|---|
| FLUT | Flutter Entertainment (FanDuel) | 8.35% | Gaming & Betting | ★ High |
| TKO | TKO Group (WWE / UFC) | 8.33% | Leagues & Venues | ★ High |
| LYV | Live Nation Entertainment | 8.33% | Sponsorship & Media | ★ High |
| FWONA | Liberty Media (Formula 1) | 8.33% | Motorsport | ★ High |
| ONON | On Holding AG | 8.33% | Apparel & Equipment | ★ High |
| NFLX | Netflix | 8.33% | Broadcasting | ★ High |
| DIS | Walt Disney / ESPN | 5.00% | Broadcasting | ● Medium |
| ADDYY | Adidas ADR | 5.00% | Apparel & Equipment | ● Medium |
| EA | Electronic Arts | 5.00% | Gaming & Betting | ● Medium |
| FOX | Fox Corporation | 5.00% | Broadcasting | ● Medium |
| DKNG | DraftKings | 5.00% | Gaming & Betting | ● Medium |
| WBD | Warner Bros. Discovery | 5.00% | Broadcasting | ● Medium |
| EDR | Endeavor Group | 5.00% | Leagues & Venues | ● Medium |
| CHDN | Churchill Downs | 5.00% | Leagues & Venues | ● Medium |
| TTWO | Take-Two Interactive | 2.50% | Gaming & Betting | ◆ Tactical |
| MSGS | Madison Square Garden Sports | 2.50% | Leagues & Venues | ◆ Tactical |
| GOLF | Acushnet Holdings (Titleist) | 2.50% | Apparel & Equipment | ◆ Tactical |
| LSEA | Lucky Strike Entertainment | 2.50% | Leagues & Venues | ◆ Tactical |

### Segment Breakdown

| Segment | Weight |
|---|---|
| Broadcasting | ~28% |
| Gaming & Betting | ~18% |
| Leagues & Venues | ~18% |
| Apparel & Equipment | ~18% |
| Sponsorship & Media | ~8% |
| Motorsport | ~8% |

---

## What the Script Does

`mvpx_analysis.py` runs a complete quantitative analysis in one command:

1. **Downloads real price data** from Yahoo Finance for all 18 holdings and the S&P 500
2. **Builds the MVPX index** with quarterly rebalancing back to conviction weights
3. **Backtests** MVPX vs S&P 500 from 2019 to today
4. **Stress tests** against three historical crisis scenarios using the actual market data from those periods:
   - 2008 Global Financial Crisis (Oct 2007 → Jun 2009)
   - 2020 COVID Crash & Recovery (Jan 2020 → Mar 2021)
   - 2022 Fed Rate Hike Cycle (Jan 2022 → Jan 2023)
5. **Generates 9 charts** and a full numerical report

---

## Requirements

- Python 3.8 or higher
- Internet connection (for Yahoo Finance data download)

### Dependencies

```bash
pip install yfinance pandas numpy matplotlib seaborn scipy
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/mvpx-index.git
cd mvpx-index
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install yfinance pandas numpy matplotlib seaborn scipy
```

---

## Usage

```bash
python mvpx_analysis.py
```

The script will print progress to the console as it downloads data and generates each chart. A typical run takes 30–90 seconds depending on your internet connection.

---

## Output Files

All outputs are saved to `./mvpx_output/` automatically.

| File | Description |
|---|---|
| `01_mvpx_vs_sp500_cumulative.png` | Growth of $10,000 — MVPX vs S&P 500 full backtest |
| `02_annual_returns_comparison.png` | Side-by-side annual return bars, year by year |
| `03_drawdown_comparison.png` | Rolling drawdown from peak for both indexes |
| `04_stress_2008.png` | 2008 GFC window — line chart + total return comparison |
| `05_stress_2020.png` | 2020 COVID crash and V-shaped recovery |
| `06_stress_2022.png` | 2022 Fed rate hike cycle Jan 2022 – Jan 2023 |
| `07_stock_heatmap.png` | Annual return heatmap for every holding |
| `08_rolling_correlation.png` | 12-month rolling correlation to S&P 500 |
| `09_segment_weights_pie.png` | Segment breakdown + individual position weights |
| `mvpx_full_report.txt` | Complete numerical report — all metrics, all scenarios |

---

## Stress Test Scenarios

### Scenario 1 — 2008 Global Financial Crisis
- **Period:** October 2007 → June 2009
- **S&P 500 peak-to-trough:** −56.8%
- **Why it hurts MVPX:** Consumer discretionary collapse. Sports betting, live events, premium apparel, and racing venues are among the first spending categories consumers cut in a credit-driven recession. High-conviction live-events positions (LYV, TKO, CHDN) share correlated drawdown risk.
- **Built-in shelter:** NFLX (subscription model), EA (gaming is counter-cyclical), FOX (broadcast rights locked in)

### Scenario 2 — 2020 COVID Crash & Recovery
- **Period:** January 2020 → March 2021
- **S&P 500 crash:** −33.9% (Feb → Mar 2020)
- **S&P 500 recovery:** +65.4% (Mar → Dec 2020)
- **Why MVPX is interesting here:** The crash phase is nearly market-neutral (NFLX and EA cushion the fall). The recovery dramatically outperforms as sports return, betting legalisation accelerates, and pent-up live event demand explodes.
- **Biggest crash drag:** LYV (live events shutdown, 2.4× crash beta)
- **Biggest recovery driver:** FLUT, TKO, DKNG (sports betting legalisation wave)

### Scenario 3 — 2022 Fed Rate Hike Cycle
- **Period:** January 2022 → January 2023
- **S&P 500 drawdown:** −25.4%
- **Why it hurts MVPX:** High-P/E and unprofitable growth names (FLUT, DKNG, NFLX) get re-rated aggressively when the discount rate rises. MVPX carries more duration risk than the broad market.
- **Rate-hike survivors inside MVPX:** FWONA, TKO, CHDN (profitable, lower-multiple, earnings-based)

---

## Hedge Recommendations

| Scenario | Instrument | Rationale |
|---|---|---|
| 2008 GFC | XLP | Consumer Staples ETF — counter-cyclical, zero correlation to sports spending |
| 2008 GFC | GLD | Gold — safe haven, inverse to consumer discretionary |
| 2008 GFC | TLT | Long Treasuries — rallied 25%+ in 2008 crisis |
| 2020 Crash | Overweight NFLX | Subscription revenue is lockdown-proof; acts as natural crash cushion |
| 2020 Crash | Overweight EA | Video gaming is counter-cyclical; in-index position to size up |
| 2020 Crash | LYV put collar | Highest crash beta (2.4×); cheapest to hedge at the position level |
| 2022 Hikes | SHV / BIL | Short-duration T-bills — yield rises with rates, direct offset |
| 2022 Hikes | XLE | Energy ETF — best sector 2022, completely uncorrelated to sports |
| 2022 Hikes | Internal rotation | Tilt toward CHDN, FWONA, TKO; reduce FLUT, DKNG weight |
| Universal | 5% cash sleeve | Always maintain dry powder — cuts drawdown ~3pp in any scenario |
| Universal | Quarterly rebalance | Mechanical discipline forces buy-low/sell-high — cheapest structural hedge |

---

## Methodology Notes

- **Price data:** Yahoo Finance adjusted close prices (splits and dividends included)
- **Index construction:** Daily return simulation with quarterly rebalancing to target weights
- **Weight normalisation:** Holdings with insufficient history are automatically dropped and remaining weights renormalised
- **Stress tests:** Crisis windows use actual market data from those periods with weights frozen (no rebalance during crisis — realistic simulation)
- **Sharpe ratio:** Calculated using 4% risk-free rate assumption
- **Benchmark:** S&P 500 total return index (`^GSPC`)

---

## Project Structure

```
mvpx-index/
│
├── mvpx_analysis.py          # Main script — all analysis in one file
├── README.md                 # This file
│
└── mvpx_output/              # Auto-created when script runs
    ├── 01_mvpx_vs_sp500_cumulative.png
    ├── 02_annual_returns_comparison.png
    ├── 03_drawdown_comparison.png
    ├── 04_stress_2008.png
    ├── 05_stress_2020.png
    ├── 06_stress_2022.png
    ├── 07_stock_heatmap.png
    ├── 08_rolling_correlation.png
    ├── 09_segment_weights_pie.png
    └── mvpx_full_report.txt
```

---

## Customisation

All index parameters are defined at the top of `mvpx_analysis.py` in the `MVPX` dictionary. To modify the index:

```python
MVPX = {
    # ticker : (weight_pct, segment, conviction)
    "FLUT":  (8.35, "Gaming & Betting", "High"),
    # add or remove holdings here
}
```

To change the backtest window:

```python
BACKTEST_START = "2019-01-01"   # change start date
BACKTEST_END   = "2026-01-01"   # or set a fixed end date
```

To change the rebalance frequency, find the `build_index()` call and change `rebalance="QE"` to `"ME"` (monthly), `"YE"` (annual), or `"10YE"` (buy-and-hold).

---

## Contributing

Pull requests are welcome. If you want to add a new holding, improve the stress test methodology, or add additional output formats (CSV exports, PDF reports), feel free to open an issue or submit a PR.

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Author

Built as a portfolio strategy research project. Index concept, construction methodology, and stress test framework designed from scratch. Data sourced entirely from Yahoo Finance — no proprietary or estimated data.
