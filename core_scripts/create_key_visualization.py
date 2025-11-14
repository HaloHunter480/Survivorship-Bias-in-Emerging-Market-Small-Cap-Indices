#!/usr/bin/env python3
"""
create_key_visualization.py

Create a single comprehensive PNG with 3 subplots:
  1) Cumulative returns: Survivor vs Complete
  2) Rolling Sharpe comparison
  3) Survivorship churn timeline

Usage (demo):
  python core_scripts/create_key_visualization.py \
    --data_dir data/processed --constituents_dir data/constituents --results_dir results --quick
"""

from pathlib import Path
import argparse
import logging
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("Viz")

sns.set_style("whitegrid")
plt.rcParams["font.size"] = 11


def safe_read_csv(p: Path, parse_dates=None):
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {p}")
    df = pd.read_csv(p)
    df.columns = df.columns.str.upper()
    if parse_dates:
        for c in parse_dates:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def create_comprehensive_visualization(price_file: Path,
                                       timeline_file: Path,
                                       results_dir: Path,
                                       window: int = 60):
    log.info("=" * 80)
    log.info("CREATING COMPREHENSIVE SURVIVORSHIP BIAS VISUALIZATION")
    log.info("=" * 80)

    results_dir = Path(results_dir)
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    log.info("Loading data...")
    price = safe_read_csv(price_file, parse_dates=["DATE", "TIMESTAMP"])
    timeline = safe_read_csv(timeline_file, parse_dates=["ENTRY_DATE", "EXIT_DATE"])

    # normalize common column names
    price.rename(columns={c: c.upper() for c in price.columns}, inplace=True)
    timeline.rename(columns={c: c.upper() for c in timeline.columns}, inplace=True)

    # unify date column in price data
    if "DATE" not in price.columns:
        # try TIMESTAMP fallback
        if "TIMESTAMP" in price.columns:
            price["DATE"] = pd.to_datetime(price["TIMESTAMP"], errors="coerce")
        else:
            raise ValueError("price file must contain DATE or TIMESTAMP column")

    # Ensure SYMBOL and return or compute return
    if "SYMBOL" not in price.columns:
        raise ValueError("price file must contain SYMBOL column")

    price["SYMBOL"] = price["SYMBOL"].astype(str)
    price["DATE"] = pd.to_datetime(price["DATE"], errors="coerce")

    # find price column to compute returns if needed
    if "RETURN" not in price.columns:
        price_col = None
        for c in ("CLOSE", "ADJCLOSE", "ADJ_CLOSE", "PRICE"):
            if c in price.columns:
                price_col = c
                break
        if price_col is None:
            raise ValueError("price data must contain RETURN or a price column (CLOSE/ADJCLOSE/PRICE)")
        log.info(f"Computing RETURN from {price_col}")
        price = price.sort_values(["SYMBOL", "DATE"])
        price["RETURN"] = price.groupby("SYMBOL")[price_col].pct_change().fillna(0)

    # is_survivor flag
    if "IS_SURVIVOR" not in price.columns:
        if "CURRENTLY_IN_INDEX" in timeline.columns:
            survivors = set(timeline[timeline["CURRENTLY_IN_INDEX"] == True]["SYMBOL"].astype(str).tolist())
        else:
            survivors = set(timeline[timeline["EXIT_DATE"].isna()]["SYMBOL"].astype(str).tolist())
        price["IS_SURVIVOR"] = price["SYMBOL"].isin(survivors)

    # compute daily mean returns across universe and survivors
    daily_complete = price.groupby("DATE")["RETURN"].mean().dropna()
    daily_survivor = price[price["IS_SURVIVOR"] == True].groupby("DATE")["RETURN"].mean().dropna()

    if daily_complete.empty or daily_survivor.empty:
        raise RuntimeError("Not enough data to compute daily series. Check sample data or file paths.")

    # cumulative returns
    cum_complete = (1 + daily_complete).cumprod()
    cum_survivor = (1 + daily_survivor).cumprod()

    # rolling sharpe
    surv_roll = (daily_survivor.rolling(window).mean() /
                 daily_survivor.rolling(window).std() * np.sqrt(252))
    comp_roll = (daily_complete.rolling(window).mean() /
                 daily_complete.rolling(window).std() * np.sqrt(252))

    # Create figure
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.2, 1, 1], hspace=0.3)
    fig.suptitle('Survivorship Bias in NIFTY Smallcap 250: Comprehensive Analysis',
                 fontsize=18, fontweight='bold', y=0.995)

    # SUBPLOT 1: Cumulative returns
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(cum_survivor.index, (cum_survivor - 1) * 100, linewidth=3, label='Survivor-Only', alpha=0.9)
    ax1.plot(cum_complete.index, (cum_complete - 1) * 100, linewidth=3, label='Complete Dataset', alpha=0.9)
    ax1.fill_between(cum_survivor.index,
                     (cum_survivor - 1) * 100,
                     (cum_complete - 1) * 100,
                     alpha=0.2, color='orange', label='Survivorship Bias')
    ax1.axhline(0, color='k', linestyle='--', linewidth=1, alpha=0.5)

    # final numbers (safe)
    final_survivor = ((cum_survivor.iloc[-1] - 1) * 100) if len(cum_survivor) else 0.0
    final_complete = ((cum_complete.iloc[-1] - 1) * 100) if len(cum_complete) else 0.0
    bias_amount = final_survivor - final_complete if final_complete is not None else 0.0

    ax1.set_title('1. Portfolio Performance: Survivor-Only vs Complete Dataset', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date'); ax1.set_ylabel('Cumulative Return (%)')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # SUBPLOT 2: Rolling Sharpe
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(surv_roll.index, surv_roll, linewidth=2.5, label='Survivor-Only', alpha=0.9)
    ax2.plot(comp_roll.index, comp_roll, linewidth=2.5, label='Complete Dataset', alpha=0.9)
    ax2.axhline(0, color='k', linestyle='--', linewidth=1, alpha=0.5)
    avg_surv_sharpe = surv_roll.mean()
    avg_comp_sharpe = comp_roll.mean()
    sharpe_bias = (avg_surv_sharpe - avg_comp_sharpe) if (avg_comp_sharpe is not None) else np.nan
    sharpe_bias_pct = (sharpe_bias / avg_comp_sharpe * 100) if avg_comp_sharpe not in (0, None, np.nan) else np.nan

    ax2.set_title(f'2. Rolling Sharpe Ratio ({window}-day) Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date'); ax2.set_ylabel('Rolling Sharpe')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    # annotate bias
    ax2.text(0.98, 0.95, f'Bias: {sharpe_bias:+.4f}\n({sharpe_bias_pct:+.1f}%)',
             transform=ax2.transAxes, ha='right', va='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange', alpha=0.9))

    # SUBPLOT 3: Churn timeline
    ax3 = fig.add_subplot(gs[2])
    # create monthly date_range covering price data
    date_start = price["DATE"].min()
    date_end = price["DATE"].max()
    date_range = pd.date_range(start=date_start, end=date_end, freq='M')

    cumulative_entries = []
    cumulative_exits = []
    active_stocks = []
    # normalize timeline columns
    if "ENTRY_DATE" not in timeline.columns or "EXIT_DATE" not in timeline.columns:
        raise ValueError("timeline file must contain ENTRY_DATE and EXIT_DATE columns (or similar).")

    timeline_local = timeline.copy()
    timeline_local["ENTRY_DATE"] = pd.to_datetime(timeline_local["ENTRY_DATE"], errors="coerce")
    timeline_local["EXIT_DATE"] = pd.to_datetime(timeline_local["EXIT_DATE"], errors="coerce")

    for d in date_range:
        entries = int((timeline_local["ENTRY_DATE"] <= d).sum())
        exits = int(((timeline_local["EXIT_DATE"] <= d) & (~timeline_local.get("CURRENTLY_IN_INDEX", False))).sum())
        active = entries - exits
        cumulative_entries.append(entries)
        cumulative_exits.append(exits)
        active_stocks.append(active)

    ax3.fill_between(date_range, 0, cumulative_entries, alpha=0.4, label='Cumulative Entries')
    ax3.plot(date_range, cumulative_entries, linewidth=2)
    ax3.fill_between(date_range, 0, cumulative_exits, alpha=0.4, label='Cumulative Exits', color='red')
    ax3.plot(date_range, cumulative_exits, linewidth=2, color='red')
    ax3.plot(date_range, active_stocks, linewidth=3, label='Active in Index', color='green')

    final_entries = cumulative_entries[-1] if cumulative_entries else 0
    final_exits = cumulative_exits[-1] if cumulative_exits else 0
    final_active = active_stocks[-1] if active_stocks else 0
    churn_rate = (final_exits / final_entries * 100) if final_entries else 0.0

    ax3.set_title('3. Index Churn: Stock Entry, Exit, and Active Timeline', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date'); ax3.set_ylabel('Number of Stocks')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.text(0.02, 0.97, f'Churn Rate: {churn_rate:.1f}%\nRemoved: {final_exits}\nTotal ever: {final_entries}',
             transform=ax3.transAxes, ha='left', va='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='red', alpha=0.9))

    # Save
    out_file = figures_dir / "COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()
    log.info(f"✓ Saved comprehensive visualization: {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data/processed", help="Processed data dir")
    parser.add_argument("--constituents_dir", type=str, default="data/constituents", help="Timeline/constituents dir")
    parser.add_argument("--results_dir", type=str, default="results", help="Output results dir")
    parser.add_argument("--price_file", type=str, default=None, help="Override price CSV path")
    parser.add_argument("--timeline_file", type=str, default=None, help="Override timeline CSV path")
    parser.add_argument("--window", type=int, default=60, help="Rolling window (days) for Sharpe calc")
    parser.add_argument("--quick", action="store_true", help="Quick demo mode; not used here but kept for consistency")
    args = parser.parse_args()

    price_file = Path(args.price_file) if args.price_file else Path(args.data_dir) / "price_data_for_backtest.csv"
    timeline_file = Path(args.timeline_file) if args.timeline_file else Path(args.constituents_dir) / "index_entry_exit_timeline.csv"
    out = create_comprehensive_visualization(price_file=price_file, timeline_file=timeline_file, results_dir=Path(args.results_dir), window=args.window)
    log.info("Visualization complete. Check: %s", out)


if __name__ == "__main__":
    main()
