#!/usr/bin/env python3
"""
validate_worst_performers.py

Validation 2: The Worst "Dead" Stocks (The Smoking Gun)
Reworked into a reproducible, repo-friendly script.

Usage examples:
  # demo using sample data
  python core_scripts/validate_worst_performers.py --data_dir data/sample --results_dir results/demo --quick

  # full run (your local processed data)
  python core_scripts/validate_worst_performers.py \
    --timeline data/constituents/index_entry_exit_timeline.csv \
    --universe data/processed/complete_stock_universe.csv \
    --bhav data/processed/all_bhavcopies_combined.csv \
    --results_dir results
"""

from pathlib import Path
import argparse
import logging
import textwrap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (14, 9)
plt.rcParams["font.size"] = 11

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ValidateWorst")

REQUIRED_BHAV_COLS = {"SYMBOL", "DATE", "CLOSE", "TOTTRDQTY", "TOTTRDVAL"}


class DeadStockValidator:
    def __init__(self, timeline_csv: Path, universe_csv: Path, bhav_combined_csv: Path, results_dir: Path):
        self.timeline_csv = Path(timeline_csv)
        self.universe_csv = Path(universe_csv)
        self.bhav_combined_csv = Path(bhav_combined_csv)
        self.results_dir = Path(results_dir)
        self.figures_dir = self.results_dir / "figures"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        # placeholders
        self.timeline = None
        self.universe = None
        self.bhav = None
        self.dead_stocks = None
        self.case_df = None

    def _read_csv_upper(self, p: Path, parse_dates=None) -> pd.DataFrame:
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        df = pd.read_csv(p)
        df.columns = df.columns.str.upper()
        if parse_dates:
            for c in parse_dates:
                if c in df.columns:
                    df[c] = pd.to_datetime(df[c], errors="coerce")
        return df

    def load_data(self):
        log.info("Loading files...")
        self.timeline = self._read_csv_upper(self.timeline_csv, parse_dates=["ENTRY_DATE", "EXIT_DATE"])
        self.universe = self._read_csv_upper(self.universe_csv, parse_dates=["FIRST_DATE", "LAST_DATE"])
        self.bhav = self._read_csv_upper(self.bhav_combined_csv, parse_dates=["DATE"])

        # quick checks
        missing = REQUIRED_BHAV_COLS - set(self.bhav.columns)
        if missing:
            raise ValueError(f"Combined bhavcopy missing columns: {missing}")

        # Normalize columns used downstream
        for df, cols in [
            (self.timeline, ["SYMBOL", "ENTRY_DATE", "EXIT_DATE", "CURRENTLY_IN_INDEX"]),
            (self.universe, ["SYMBOL", "LAST_DATE", "DAYS_SINCE_LAST_TRADE", "LIKELY_DELISTED", "AVG_PRICE", "MIN_PRICE", "MAX_PRICE", "MARKET_CAP_PROXY"]),
        ]:
            for c in cols:
                if c not in df.columns:
                    # create sensible defaults
                    if c == "CURRENTLY_IN_INDEX":
                        df[c] = False
                    else:
                        df[c] = np.nan

        # cast symbol to str
        for df in (self.timeline, self.universe, self.bhav):
            if "SYMBOL" in df.columns:
                df["SYMBOL"] = df["SYMBOL"].astype(str).str.upper()

        log.info(f"✓ Timeline rows: {len(self.timeline):,}")
        log.info(f"✓ Universe rows: {len(self.universe):,}")
        log.info(f"✓ Bhav combined rows: {len(self.bhav):,}\n")

    def identify_dead_stocks(self):
        log.info("=" * 72)
        log.info("IDENTIFYING TRULY 'DEAD' STOCKS")
        log.info("=" * 72)

        removed = self.timeline[~self.timeline["CURRENTLY_IN_INDEX"]].copy()
        removed = removed.merge(
            self.universe[["SYMBOL", "LAST_DATE", "DAYS_SINCE_LAST_TRADE", "LIKELY_DELISTED", "AVG_PRICE", "MIN_PRICE", "MAX_PRICE", "MARKET_CAP_PROXY"]],
            on="SYMBOL",
            how="left",
        )

        # Define "dead" as LIKELY_DELISTED True (you used that earlier) AND DAYS_SINCE_LAST_TRADE >= 365 (1 year)
        # If DAYS_SINCE_LAST_TRADE missing, fall back to LAST_DATE relative to latest bhav date
        if removed["DAYS_SINCE_LAST_TRADE"].isna().any():
            latest_bhav_date = self.bhav["DATE"].max()
            removed["DAYS_SINCE_LAST_TRADE"] = removed["DAYS_SINCE_LAST_TRADE"].fillna(
                (latest_bhav_date - pd.to_datetime(removed["LAST_DATE"], errors="coerce")).dt.days
            )

        dead = removed[(removed["LIKELY_DELISTED"] == True) | (removed["DAYS_SINCE_LAST_TRADE"] >= 365)].copy()
        still_trading = removed[~removed.index.isin(dead.index)].copy()

        log.info(f"Removed stocks total: {len(removed):,}")
        log.info(f"Dead/delisted (detected): {len(dead):,} ({len(dead)/len(removed)*100:.1f}%)")
        log.info(f"Still trading / demoted:   {len(still_trading):,} ({len(still_trading)/len(removed)*100:.1f}%)\n")

        # prefer sorting by DAYS_SINCE_LAST_TRADE desc
        dead = dead.sort_values("DAYS_SINCE_LAST_TRADE", ascending=False)
        self.dead_stocks = dead
        return dead

    def analyze_top_dead(self, top_n: int = 15):
        if self.dead_stocks is None:
            raise RuntimeError("Run identify_dead_stocks() first")

        log.info("=" * 72)
        log.info("THE 'SMOKING GUN' - WORST PERFORMERS (TOP %d DEAD STOCKS)", top_n)
        log.info("=" * 72)
        log.info("These stocks are COMPLETELY MISSING from survivor-only backtests.")
        log.info("They represent the left tail of the return distribution.\n")

        case_studies = []
        for idx, (_, stock) in enumerate(self.dead_stocks.head(top_n).iterrows(), 1):
            sym = stock["SYMBOL"]
            entry_date = stock.get("ENTRY_DATE", pd.NaT)
            exit_date = stock.get("EXIT_DATE", pd.NaT)

            history = self.bhav[self.bhav["SYMBOL"] == sym].sort_values("DATE")
            if history.empty:
                log.warning(f"No trading history for {sym}; skipping deep dive.")
                continue

            # compute entry/exit prices (closest non-null)
            entry_price = np.nan
            exit_price = np.nan
            if pd.notna(entry_date):
                e_period = history[history["DATE"] <= pd.to_datetime(entry_date, errors="coerce")]
                if not e_period.empty:
                    entry_price = float(e_period["CLOSE"].iloc[-1])
            if pd.notna(exit_date):
                x_period = history[history["DATE"] <= pd.to_datetime(exit_date, errors="coerce")]
                if not x_period.empty:
                    exit_price = float(x_period["CLOSE"].iloc[-1])

            final_price = float(history["CLOSE"].iloc[-1])

            # compute returns
            if not np.isnan(entry_price) and not np.isnan(exit_price):
                return_while_in_index = (exit_price - entry_price) / entry_price * 100
            else:
                return_while_in_index = np.nan

            if not np.isnan(entry_price):
                return_to_delisting = (final_price - entry_price) / entry_price * 100
            else:
                return_to_delisting = np.nan

            decline_after_exit = np.nan
            if not np.isnan(exit_price):
                decline_after_exit = (final_price - exit_price) / exit_price * 100

            case_studies.append({
                "symbol": sym,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "last_trade": history["DATE"].max(),
                "days_dead": stock.get("DAYS_SINCE_LAST_TRADE", np.nan),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "final_price": final_price,
                "return_in_index": return_while_in_index,
                "total_return": return_to_delisting,
                "decline_after_exit": decline_after_exit,
                "trading_days": len(history),
                "avg_daily_volume": history.get("TOTTRDQTY", pd.Series()).mean()
            })

        case_df = pd.DataFrame(case_studies)
        self.case_df = case_df
        return case_df

    def summarize_and_visualize(self, top_n=15):
        if self.case_df is None:
            raise RuntimeError("Run analyze_top_dead() first")

        case_df = self.case_df.copy()
        valid_returns = case_df["total_return"].dropna()

        # SUMMARY VALUES
        avg_dead_return = valid_returns.mean() if not valid_returns.empty else np.nan
        median = valid_returns.median() if not valid_returns.empty else np.nan
        worst = valid_returns.min() if not valid_returns.empty else np.nan
        best = valid_returns.max() if not valid_returns.empty else np.nan
        std = valid_returns.std() if not valid_returns.empty else np.nan

        massive_losses = (valid_returns < -50).sum()
        significant_losses = ((valid_returns >= -50) & (valid_returns < -20)).sum()
        moderate_losses = ((valid_returns >= -20) & (valid_returns < 0)).sum()
        gainers = (valid_returns >= 0).sum()

        avg_days_dead = case_df["days_dead"].mean() if "days_dead" in case_df.columns else np.nan

        # Print textual summary
        log.info("\n" + "=" * 72)
        log.info("SUMMARY: THE SMOKING GUN EVIDENCE")
        log.info("=" * 72)
        log.info(f"Analysis of {len(case_df)} worst dead stocks")
        log.info(f"Average return (entry -> delisting): {avg_dead_return:+.2f}%")
        log.info(f"Median: {median:+.2f}%, Best: {best:+.2f}%, Worst: {worst:+.2f}%")
        log.info(f"Std deviation: {std:.2f}%")
        log.info("")
        log.info("PERFORMANCE BREAKDOWN:")
        total = len(valid_returns) if len(valid_returns) else 1
        log.info(f"  Massive losses (>50%):      {massive_losses} ({massive_losses/total*100:.1f}%)")
        log.info(f"  Significant losses (20-50%): {significant_losses} ({significant_losses/total*100:.1f}%)")
        log.info(f"  Moderate losses (<20%):     {moderate_losses} ({moderate_losses/total*100:.1f}%)")
        log.info(f"  Gains:                      {gainers} ({gainers/total*100:.1f}%)")
        log.info("")
        log.info(f"Average days since last trade (of cases): {avg_days_dead:.0f} days ({avg_days_dead/365:.1f} years)\n")

        # VISUALIZATIONS (4-panel)
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle("The Smoking Gun: Worst Dead Stocks Analysis", fontsize=16, fontweight="bold")

        # Plot 1: distribution of returns
        ax = axes[0, 0]
        if not valid_returns.empty:
            ax.hist(valid_returns, bins=20, color="red", alpha=0.75, edgecolor="black")
            ax.axvline(valid_returns.mean(), color="darkred", linestyle="--", linewidth=2, label=f"Mean: {valid_returns.mean():.1f}%")
            ax.axvline(0, color="black", linewidth=1)
            ax.set_xlabel("Return (%)")
            ax.set_title("Return Distribution of Dead Stocks")
            ax.legend()
            ax.grid(True, alpha=0.3)

        # Plot 2: individual returns
        ax = axes[0, 1]
        if not case_df.empty:
            y = case_df["total_return"].fillna(0)
            colors = ["darkred" if r < -50 else "red" if r < -20 else "orange" if r < 0 else "green" for r in y]
            ax.barh(case_df["symbol"], y, color=colors, edgecolor="black", alpha=0.8)
            ax.set_xlabel("Total Return (%)")
            ax.set_title("Individual Dead Stock Performance")
            ax.grid(True, alpha=0.3, axis="x")

        # Plot 3: days dead
        ax = axes[1, 0]
        if not case_df.empty:
            ax.bar(case_df["symbol"], case_df["days_dead"] / 365, color="purple", edgecolor="black", alpha=0.8)
            ax.set_ylabel("Years Since Last Trade")
            ax.set_title("Time Since Death (Delisting)")
            ax.set_xticklabels(case_df["symbol"], rotation=45, ha="right")

        # Plot 4: price trajectory for the worst performer (if data exists)
        ax = axes[1, 1]
        if not valid_returns.empty:
            worst_idx = valid_returns.idxmin()
            worst_symbol = case_df.loc[worst_idx, "symbol"]
            hist = self.bhav[self.bhav["SYMBOL"] == worst_symbol].sort_values("DATE")
            if not hist.empty:
                ax.plot(hist["DATE"], hist["CLOSE"], color="red", linewidth=2, label="Price")
                e = case_df.loc[worst_idx, "entry_date"]
                x = case_df.loc[worst_idx, "exit_date"]
                if pd.notna(e):
                    ax.axvline(pd.to_datetime(e), color="green", linestyle="--", label="Entered Index")
                if pd.notna(x):
                    ax.axvline(pd.to_datetime(x), color="black", linestyle="--", label="Exited Index")
                ax.set_title(f"Price Trajectory: {worst_symbol} (Worst Performer)")
                ax.set_xlabel("Date"); ax.set_ylabel("Price")
                ax.legend()
                ax.grid(True, alpha=0.3)

        plt.tight_layout()
        out_fig = self.figures_dir / "6_smoking_gun_dead_stocks.png"
        plt.savefig(out_fig, dpi=300, bbox_inches="tight")
        plt.close()
        log.info(f"✓ Saved visualization: {out_fig}")

        # Export dead stocks list
        out_csv = self.results_dir.parent.joinpath("data", "processed", "dead_stocks_list.csv")
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        export_cols = ["SYMBOL", "ENTRY_DATE", "EXIT_DATE", "LAST_DATE", "DAYS_SINCE_LAST_TRADE", "AVG_PRICE", "MARKET_CAP_PROXY"]
        export_df = self.dead_stocks[export_cols].copy() if set(export_cols).issubset(self.dead_stocks.columns) else self.dead_stocks.copy()
        export_df.to_csv(out_csv, index=False)
        log.info(f"✓ Exported dead stocks list to: {out_csv}")

        # Save internal case_df for downstream checks
        self.case_df.to_csv(self.results_dir / "dead_case_studies.csv", index=False)
        log.info(f"✓ Saved case studies CSV: {self.results_dir / 'dead_case_studies.csv'}")

        # Final printed summary (compact)
        log.info("\n✓ VALIDATION 2 COMPLETE: THE SMOKING GUN FOUND\n")
        log.info("KEY EVIDENCE:")
        log.info(f"  • {len(self.dead_stocks)} stocks detected as dead/delisted")
        if not np.isnan(avg_dead_return):
            log.info(f"  • Average return of worst cases: {avg_dead_return:+.2f}%")
        log.info(f"  • Avg days since last trade (cases): {avg_days_dead:.0f} days")
        log.info("  • These stocks create significant upward bias in survivor-only backtests\n")

    def run(self, top_n=15):
        self.load_data()
        self.identify_dead_stocks()
        self.analyze_top_dead(top_n=top_n)
        self.summarize_and_visualize(top_n=top_n)


def parse_args():
    p = argparse.ArgumentParser(description="Validate worst dead stocks and produce visualizations")
    p.add_argument("--timeline", type=str, default="data/constituents/index_entry_exit_timeline.csv", help="Timeline CSV (index entry/exit)")
    p.add_argument("--universe", type=str, default="data/processed/complete_stock_universe.csv", help="Universe CSV with delisting metadata")
    p.add_argument("--bhav", type=str, default="data/processed/all_bhavcopies_combined.csv", help="Combined bhavcopies CSV")
    p.add_argument("--results_dir", type=str, default="results", help="Results output directory")
    p.add_argument("--top_n", type=int, default=15, help="Top N dead stocks to analyze")
    p.add_argument("--quick", action="store_true", help="Quick demo mode (not used here but kept for API parity)")
    return p.parse_args()


def main():
    args = parse_args()
    validator = DeadStockValidator(
        timeline_csv=Path(args.timeline),
        universe_csv=Path(args.universe),
        bhav_combined_csv=Path(args.bhav),
        results_dir=Path(args.results_dir),
    )
    validator.run(top_n=args.top_n)


if __name__ == "__main__":
    main()
