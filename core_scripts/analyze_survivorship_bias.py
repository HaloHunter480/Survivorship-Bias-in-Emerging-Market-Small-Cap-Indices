#!/usr/bin/env python3
"""
analyze_survivorship_bias.py

Reproducible, repo-ready survivorship bias analysis and visualization.
Usage (demo):
  python core_scripts/analyze_survivorship_bias.py --data_dir data --constituents_dir data/constituents --quick

See --help for options.
"""

from pathlib import Path
from datetime import datetime
import argparse
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# plotting defaults
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["font.size"] = 11

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("Analyzer")


class SurvivorshipBiasAnalyzer:
    def __init__(self, data_dir: Path, constituents_dir: Path, results_dir: Path):
        self.data_dir = Path(data_dir)
        self.constituents_dir = Path(constituents_dir)
        self.results_dir = Path(results_dir)
        self.figures_dir = self.results_dir / "figures"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def _read_csv_safe(self, p: Path, parse_dates=None):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")
        df = pd.read_csv(p)
        df.columns = df.columns.str.upper()
        if parse_dates:
            for c in parse_dates:
                if c in df.columns:
                    df[c] = pd.to_datetime(df[c], errors="coerce")
        return df

    def load_data(self,
                  price_file: Path,
                  timeline_file: Path,
                  universe_file: Path):
        log.info("Loading data...")
        # Price data
        self.price_data = self._read_csv_safe(price_file, parse_dates=["DATE", "DATE_TIME", "TIMESTAMP"])
        # try common date column names -> unify to 'DATE'
        date_cols = [c for c in ("DATE", "TIMESTAMP", "DATE_TIME") if c in self.price_data.columns]
        if date_cols:
            self.price_data["DATE"] = pd.to_datetime(self.price_data[date_cols[0]], errors="coerce")
        else:
            # fallback: assume 'DATE' exists; else error
            if "DATE" not in self.price_data.columns:
                raise ValueError("Price data must include a date column (DATE or TIMESTAMP).")

        # Normalize symbol column
        if "SYMBOL" not in self.price_data.columns:
            raise ValueError("Price data must include SYMBOL column.")
        self.price_data["SYMBOL"] = self.price_data["SYMBOL"].astype(str)

        # Timeline (constituents with entry/exit)
        self.timeline = self._read_csv_safe(timeline_file)
        # support both ENTRY_DATE/EXIT_DATE or entry_date/exit_date
        if "ENTRY_DATE" not in self.timeline.columns:
            if "ENTRY_DATE".lower() in map(str.lower, self.timeline.columns):
                self.timeline.columns = [c.upper() for c in self.timeline.columns]
        # try to parse dates
        for c in ("ENTRY_DATE", "EXIT_DATE"):
            if c in self.timeline.columns:
                self.timeline[c] = pd.to_datetime(self.timeline[c], errors="coerce")

        # Universe (for delisting analysis etc)
        self.universe = self._read_csv_safe(universe_file)
        # unify columns used later
        for col in ("STATUS", "LIKELY_DELISTED", "DAYS_SINCE_LAST_TRADE"):
            if col not in self.universe.columns:
                # create sensible default columns
                if col == "LIKELY_DELISTED":
                    self.universe["LIKELY_DELISTED"] = False
                else:
                    self.universe[col] = np.nan

        log.info(f"✓ Loaded price records: {len(self.price_data):,}")
        log.info(f"✓ Timeline records: {len(self.timeline):,}")
        log.info(f"✓ Universe records: {len(self.universe):,}")
        log.info("")

    def ensure_returns_and_flags(self):
        # Derive 'RETURN' if not present using grouped pct_change on CLOSE or ADJ CLOSE
        if "RETURN" not in self.price_data.columns:
            # detect price column
            price_col = None
            for c in ("CLOSE", "ADJCLOSE", "ADJ_CLOSE", "PRICE"):
                if c in self.price_data.columns:
                    price_col = c
                    break
            if price_col is None:
                raise ValueError("No price column found (CLOSE / ADJCLOSE / PRICE).")
            log.info(f"Computing returns from price column: {price_col}")
            self.price_data = self.price_data.sort_values(["SYMBOL", "DATE"])
            self.price_data["RETURN"] = self.price_data.groupby("SYMBOL")[price_col].pct_change().fillna(0)
        else:
            log.info("Using existing RETURN column.")

        # Ensure date is datetime and set index for returns series grouping
        self.price_data["DATE"] = pd.to_datetime(self.price_data["DATE"], errors="coerce")

        # Create is_survivor flag if not present using timeline latest known set
        if "IS_SURVIVOR" not in self.price_data.columns:
            log.info("Creating IS_SURVIVOR flag from timeline.")
            # timeline CURRENTLY_IN_INDEX might be present
            if "CURRENTLY_IN_INDEX" in self.timeline.columns:
                survivors = set(self.timeline[self.timeline["CURRENTLY_IN_INDEX"] == True]["SYMBOL"].astype(str).tolist())
            else:
                # fallback: take symbols whose EXIT_DATE is NaT (still present) OR last method == known_current
                survivors = set(self.timeline[self.timeline["EXIT_DATE"].isna()]["SYMBOL"].astype(str).tolist())

            self.price_data["IS_SURVIVOR"] = self.price_data["SYMBOL"].isin(survivors)
        else:
            log.info("Using existing IS_SURVIVOR flag.")

    def calculate_basic_stats(self):
        log.info("=" * 60)
        log.info("BASIC STATISTICS")
        log.info("=" * 60)
        # daily mean return across symbols for survivor and complete
        # group by date and average returns across universe
        daily = self.price_data.copy()
        # ensure numeric
        daily["RETURN"] = pd.to_numeric(daily["RETURN"], errors="coerce").fillna(0)

        surv_daily = daily[daily["IS_SURVIVOR"] == True].groupby("DATE")["RETURN"].mean().dropna()
        comp_daily = daily.groupby("DATE")["RETURN"].mean().dropna()

        # Annualize
        surv_mean = surv_daily.mean() * 252
        comp_mean = comp_daily.mean() * 252
        surv_vol = surv_daily.std() * np.sqrt(252)
        comp_vol = comp_daily.std() * np.sqrt(252)

        surv_sharpe = surv_mean / surv_vol if surv_vol > 0 else 0.0
        comp_sharpe = comp_mean / comp_vol if comp_vol > 0 else 0.0

        sharpe_bias = surv_sharpe - comp_sharpe
        sharpe_bias_pct = (sharpe_bias / comp_sharpe * 100) if comp_sharpe != 0 else np.nan

        return_bias = surv_mean - comp_mean
        return_bias_pct = (return_bias / (abs(comp_mean) + 1e-12) * 100) if comp_mean != 0 else np.nan

        log.info(f"SURVIVOR-ONLY: Annual Return {surv_mean:.2%}, Vol {surv_vol:.2%}, Sharpe {surv_sharpe:.4f}")
        log.info(f"COMPLETE:     Annual Return {comp_mean:.2%}, Vol {comp_vol:.2%}, Sharpe {comp_sharpe:.4f}")
        log.info("")
        log.info("SURVIVORSHIP BIAS:")
        log.info(f"  Sharpe Bias: {sharpe_bias:+.4f} ({sharpe_bias_pct:+.1f}%)")
        log.info(f"  Return Bias: {return_bias:+.2%} per year ({return_bias_pct:+.1f}%)")
        log.info("")

        self.stats = {
            "surv_daily": surv_daily,
            "comp_daily": comp_daily,
            "surv_mean": surv_mean,
            "comp_mean": comp_mean,
            "surv_sharpe": surv_sharpe,
            "comp_sharpe": comp_sharpe,
            "sharpe_bias": sharpe_bias,
            "sharpe_bias_pct": sharpe_bias_pct,
            "return_bias": return_bias,
            "return_bias_pct": return_bias_pct,
        }
        return self.stats

    def create_visualizations(self):
        # guard
        if not hasattr(self, "stats"):
            raise RuntimeError("Run calculate_basic_stats() first")

        fig1_path = self.figures_dir / "1_stock_timeline.png"
        try:
            # basic timeline plot
            t = self.timeline.copy()
            if "ENTRY_DATE" in t.columns:
                t_sorted = t.sort_values("ENTRY_DATE").reset_index(drop=True)
                t_sorted["cumulative"] = range(1, len(t_sorted) + 1)
                plt.figure(figsize=(14, 6))
                plt.plot(t_sorted["ENTRY_DATE"], t_sorted["cumulative"], linewidth=2, label="Cumulative Stocks")
                plt.axhline(252, color="red", linestyle="--", label="Current survivors (252)")
                plt.title("Cumulative Stock Entry into Index")
                plt.xlabel("Date")
                plt.ylabel("Number of Stocks")
                plt.legend()
                plt.tight_layout()
                plt.savefig(fig1_path, dpi=300, bbox_inches="tight")
                plt.close()
                log.info(f"  ✓ Saved: {fig1_path.name}")
        except Exception as e:
            log.warning(f"Could not create timeline: {e}")

        # returns comparison
        fig2_path = self.figures_dir / "2_returns_comparison.png"
        try:
            surv = self.stats["surv_daily"] * 100
            comp = self.stats["comp_daily"] * 100
            # hist + cumulative + rolling sharpe + sharpe diff
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            axes = axes.flatten()

            # hist
            axes[0].hist(surv.dropna(), bins=50, alpha=0.6, label="Survivor", density=True)
            axes[0].hist(comp.dropna(), bins=50, alpha=0.6, label="Complete", density=True)
            axes[0].set_title("Returns Distribution Comparison")
            axes[0].legend()

            # cumulative
            surv_cum = (1 + self.stats["surv_daily"]).cumprod() - 1
            comp_cum = (1 + self.stats["comp_daily"]).cumprod() - 1
            axes[1].plot(surv_cum.index, surv_cum * 100, label="Survivor")
            axes[1].plot(comp_cum.index, comp_cum * 100, label="Complete")
            axes[1].set_title("Cumulative Returns (%)")
            axes[1].legend()

            # rolling sharpe
            window = 60
            surv_rolling = (self.stats["surv_daily"].rolling(window).mean() /
                            self.stats["surv_daily"].rolling(window).std() * np.sqrt(252))
            comp_rolling = (self.stats["comp_daily"].rolling(window).mean() /
                            self.stats["comp_daily"].rolling(window).std() * np.sqrt(252))
            axes[2].plot(surv_rolling.index, surv_rolling, label="Survivor")
            axes[2].plot(comp_rolling.index, comp_rolling, label="Complete")
            axes[2].set_title(f"{window}-day Rolling Sharpe")
            axes[2].legend()

            # sharpe diff
            sharpe_diff = surv_rolling - comp_rolling
            axes[3].plot(sharpe_diff.index, sharpe_diff, color="purple")
            axes[3].axhline(0, color="black", linestyle="--")
            axes[3].set_title("Rolling Sharpe Difference (Survivor - Complete)")

            plt.tight_layout()
            plt.savefig(fig2_path, dpi=300, bbox_inches="tight")
            plt.close()
            log.info(f"  ✓ Saved: {fig2_path.name}")
        except Exception as e:
            log.warning(f"Could not create returns comparison: {e}")

        # delisting analysis
        fig4_path = self.figures_dir / "4_delisting_analysis.png"
        try:
            u = self.universe.copy()
            if "STATUS" not in u.columns:
                u["STATUS"] = np.where(u.get("LIKELY_DELISTED", False), "delisted", "active")
            counts = u["STATUS"].value_counts()
            plt.figure(figsize=(10, 6))
            counts.plot(kind="bar", color=["green" if x == "active" else "red" for x in counts.index])
            plt.title("Stock Status (Active vs Delisted)")
            plt.tight_layout()
            plt.savefig(fig4_path, dpi=300, bbox_inches="tight")
            plt.close()
            log.info(f"  ✓ Saved: {fig4_path.name}")
        except Exception as e:
            log.warning(f"Could not create delisting analysis: {e}")

    def generate_report(self):
        report_file = self.results_dir / "reports" / "detailed_bias_analysis.txt"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("DETAILED SURVIVORSHIP BIAS ANALYSIS\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("SUMMARY METRICS\n")
            for k in ("surv_mean", "comp_mean", "surv_sharpe", "comp_sharpe", "sharpe_bias", "return_bias"):
                v = self.stats.get(k, None)
                f.write(f"{k}: {v}\n")
            f.write("\n")
            f.write("See figures/ for visual output.\n")
        log.info(f"  ✓ Saved report: {report_file.name}")
        return report_file

    def run_complete_analysis(self, price_file: Path, timeline_file: Path, universe_file: Path):
        self.load_data(price_file, timeline_file, universe_file)
        self.ensure_returns_and_flags()
        self.calculate_basic_stats()
        self.create_visualizations()
        report = self.generate_report()
        log.info("\nANALYSIS COMPLETE")
        log.info(f"Figures in: {self.figures_dir.resolve()}")
        log.info(f"Report: {report.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Run survivorship bias analysis")
    parser.add_argument("--data_dir", type=str, default="data/processed", help="Processed data directory")
    parser.add_argument("--constituents_dir", type=str, default="data/constituents", help="Constituents/timeline dir")
    parser.add_argument("--results_dir", type=str, default="results", help="Results output directory")
    parser.add_argument("--price_file", type=str, default=None, help="CSV file for price data (overrides data_dir default)")
    parser.add_argument("--timeline_file", type=str, default=None, help="CSV file for timeline (overrides constituents_dir default)")
    parser.add_argument("--universe_file", type=str, default=None, help="CSV file for universe (overrides data_dir default)")
    args = parser.parse_args()

    # file defaults
    price_file = Path(args.price_file) if args.price_file else Path(args.data_dir) / "price_data_for_backtest.csv"
    timeline_file = Path(args.timeline_file) if args.timeline_file else Path(args.constituents_dir) / "index_entry_exit_timeline.csv"
    universe_file = Path(args.universe_file) if args.universe_file else Path(args.data_dir) / "complete_stock_universe.csv"

    analyzer = SurvivorshipBiasAnalyzer(data_dir=args.data_dir, constituents_dir=args.constituents_dir, results_dir=args.results_dir)
    analyzer.run_complete_analysis(price_file=price_file, timeline_file=timeline_file, universe_file=universe_file)


if __name__ == "__main__":
    main()
