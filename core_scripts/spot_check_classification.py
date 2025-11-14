#!/usr/bin/env python3
"""
spot_check_classification.py

Spot-check stock classification (survivor vs removed).
Repo-ready: CLI, safe defaults, logging, and reproducible sampling.

Usage (demo):
  python core_scripts/spot_check_classification.py --data_dir data/sample --results_dir results/demo --seed 42

Full run:
  python core_scripts/spot_check_classification.py --data_dir data --results_dir results --seed 42
"""

from pathlib import Path
import argparse
import logging
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("SpotCheck")

DEFAULT_SAMPLE_N = 10


def _read_csv_upper(p: Path, parse_dates=None):
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {p}")
    df = pd.read_csv(p)
    df.columns = df.columns.str.upper()
    if parse_dates:
        for c in parse_dates:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


class SpotCheck:
    def __init__(self, data_dir: Path, bhav_dir: Path = None, known_current_file: Path = None, results_dir: Path = Path("results")):
        self.data_dir = Path(data_dir)
        self.bhav_dir = Path(bhav_dir) if bhav_dir else None
        self.known_current_file = Path(known_current_file) if known_current_file else None
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.sample_out = self.results_dir / "spot_check_sample.csv"

        self.timeline = None
        self.universe = None
        self.bhav = None
        self.known_current = None

    def load(self):
        # expected files inside data_dir
        timeline_path = self.data_dir / "constituents" / "index_entry_exit_timeline.csv"
        universe_path = self.data_dir / "processed" / "complete_stock_universe.csv"
        bhav_path = self.data_dir / "processed" / "all_bhavcopies_combined.csv"

        # try file overrides if placed directly under data_dir (compatibility)
        if not timeline_path.exists():
            alt = self.data_dir / "constituent_timeline.csv"
            if alt.exists():
                timeline_path = alt

        log.info("Loading timeline: %s", timeline_path)
        self.timeline = _read_csv_upper(timeline_path, parse_dates=["ENTRY_DATE", "EXIT_DATE"])

        log.info("Loading universe: %s", universe_path)
        self.universe = _read_csv_upper(universe_path, parse_dates=["FIRST_DATE", "LAST_DATE"])

        log.info("Loading combined bhavcopies: %s", bhav_path)
        self.bhav = _read_csv_upper(bhav_path, parse_dates=["DATE"])

        # known current list optional
        if self.known_current_file and self.known_current_file.exists():
            kc = _read_csv_upper(self.known_current_file)
            # try to find a symbol column
            for col in ("SYMBOL", "STOCK", "TICKER", "CODE", "SECURITY"):
                if col in kc.columns:
                    self.known_current = set(kc[col].astype(str).str.upper().tolist())
                    break
            if not self.known_current:
                log.warning("Known current file loaded but no symbol column found.")
        else:
            self.known_current = None
            log.info("No known-current file provided (optional).")

        # normalize symbol column casing
        for df in (self.timeline, self.universe, self.bhav):
            if "SYMBOL" in df.columns:
                df["SYMBOL"] = df["SYMBOL"].astype(str).str.upper()

        log.info("✓ Loaded timeline (%d), universe (%d), bhav rows (%d)\n",
                 len(self.timeline), len(self.universe), len(self.bhav))

    def run_spot_check(self, sample_n=DEFAULT_SAMPLE_N, seed=42):
        np.random.seed(seed)

        # Ensure CURRENTLY_IN_INDEX present and boolean
        if "CURRENTLY_IN_INDEX" not in self.timeline.columns:
            # Try to infer from exit date presence
            self.timeline["CURRENTLY_IN_INDEX"] = self.timeline["EXIT_DATE"].isna()

        survivors = self.timeline[self.timeline["CURRENTLY_IN_INDEX"] == True].copy()
        removed = self.timeline[self.timeline["CURRENTLY_IN_INDEX"] == False].copy()

        if len(survivors) == 0 or len(removed) == 0:
            raise RuntimeError("Insufficient survivors or removed stocks in timeline to sample.")

        # sample roughly half and half, but not exceeding available counts
        n_each = min(max(1, sample_n // 2), min(len(survivors), len(removed)))
        sample_survivors = survivors.sample(n=n_each, random_state=seed)
        sample_removed = removed.sample(n=n_each, random_state=seed+1)
        sample = pd.concat([sample_survivors, sample_removed]).reset_index(drop=True)

        latest_date = pd.to_datetime(self.bhav["DATE"].max())

        # Collect results for saving
        rows = []
        for idx, row in sample.iterrows():
            sym = str(row.get("SYMBOL", "")).upper()
            entry = row.get("ENTRY_DATE", pd.NaT)
            exit_date = row.get("EXIT_DATE", pd.NaT)
            currently_in = bool(row.get("CURRENTLY_IN_INDEX", False))
            status = row.get("STATUS", "")

            # merge with universe
            urow = self.universe[self.universe["SYMBOL"] == sym]
            if not urow.empty:
                u = urow.iloc[0]
                first_date = u.get("FIRST_DATE", pd.NaT)
                last_date = u.get("LAST_DATE", pd.NaT)
                days_since = u.get("DAYS_SINCE_LAST_TRADE", np.nan)
                likely_delisted = bool(u.get("LIKELY_DELISTED", False))
                avg_price = u.get("AVG_PRICE", np.nan)
                market_cap_proxy = u.get("MARKET_CAP_PROXY", np.nan)
            else:
                first_date = last_date = pd.NaT
                days_since = np.nan
                likely_delisted = False
                avg_price = np.nan
                market_cap_proxy = np.nan

            # recent trades in last 90 days
            recent_trades = self.bhav[(self.bhav["SYMBOL"] == sym) & (pd.to_datetime(self.bhav["DATE"]) >= (latest_date - pd.Timedelta(days=90)))]
            recent_trading_days = len(recent_trades)
            latest_price = recent_trades["CLOSE"].iloc[-1] if recent_trading_days > 0 else np.nan
            latest_trade_date = recent_trades["DATE"].iloc[-1] if recent_trading_days > 0 else pd.NaT

            # cross-check with known current
            in_known_current = sym in self.known_current if self.known_current else None

            # logical checks
            days_since_exit = (latest_date - pd.to_datetime(exit_date)).days if pd.notna(exit_date) else np.nan
            exit_before_entry = False
            if pd.notna(exit_date) and pd.notna(entry):
                exit_before_entry = pd.to_datetime(exit_date) < pd.to_datetime(entry)

            rows.append({
                "SYMBOL": sym,
                "STATUS": status,
                "CURRENTLY_IN_INDEX": currently_in,
                "ENTRY_DATE": entry,
                "EXIT_DATE": exit_date,
                "PERIODS_IN_INDEX": row.get("PERIODS_IN_INDEX", np.nan),
                "FIRST_DATE": first_date,
                "LAST_DATE": last_date,
                "DAYS_SINCE_LAST_TRADE": days_since,
                "LIKELY_DELISTED": likely_delisted,
                "AVG_PRICE": avg_price,
                "MARKET_CAP_PROXY": market_cap_proxy,
                "RECENT_TRADING_DAYS_90": recent_trading_days,
                "LATEST_PRICE": latest_price,
                "LATEST_TRADE_DATE": latest_trade_date,
                "IN_KNOWN_CURRENT": in_known_current,
                "DAYS_SINCE_EXIT": days_since_exit,
                "EXIT_BEFORE_ENTRY": exit_before_entry
            })

        sample_df = pd.DataFrame(rows)
        sample_df.to_csv(self.sample_out, index=False)
        log.info("✓ Saved sample spot-check to: %s", self.sample_out)

        # Print summary to console (concise)
        log.info("\nSPOT-CHECK SAMPLE SUMMARY\n" + "-" * 50)
        log.info("Latest bhav date: %s", latest_date.date())
        log.info("Sample size: %d", len(sample_df))
        log.info(sample_df[["SYMBOL", "CURRENTLY_IN_INDEX", "RECENT_TRADING_DAYS_90", "IN_KNOWN_CURRENT", "EXIT_BEFORE_ENTRY"]].to_string(index=False))
        log.info("\nManual inspection saved; use sample CSV for deeper checks.\n")

        return sample_df

    def compare_with_known_current(self):
        if not self.known_current:
            log.info("No known current list available for comparison.")
            return None

        survivors = set(self.timeline[self.timeline["CURRENTLY_IN_INDEX"] == True]["SYMBOL"].astype(str).tolist())
        in_both = survivors & self.known_current
        we_say_yes_they_no = survivors - self.known_current
        we_say_no_they_yes = self.known_current - survivors

        total_known = len(self.known_current) if len(self.known_current) else 1
        accuracy = len(in_both) / total_known * 100

        log.info("\nComparison with known current list:")
        log.info("  Agreed survivors: %d", len(in_both))
        log.info("  We say survivor, they do not: %d", len(we_say_yes_they_no))
        log.info("  They list, we say removed: %d", len(we_say_no_they_yes))
        log.info("  Accuracy estimate: %.1f%% (%d/%d)\n", accuracy, len(in_both), total_known)

        # return dict for programmatic use
        return {
            "in_both": in_both,
            "we_say_yes_they_no": we_say_yes_they_no,
            "we_say_no_they_yes": we_say_no_they_yes,
            "accuracy_pct": accuracy
        }


def parse_args():
    p = argparse.ArgumentParser(description="Spot-check stock classification (survivor vs removed)")
    p.add_argument("--data_dir", type=str, default="data", help="Base data directory (expects subfolders /processed and /constituents)")
    p.add_argument("--known_current", type=str, default=None, help="Optional CSV with known current constituents")
    p.add_argument("--results_dir", type=str, default="results", help="Results directory")
    p.add_argument("--sample_n", type=int, default=10, help="Total sample size (default 10)")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return p.parse_args()


def main():
    args = parse_args()
    sc = SpotCheck(data_dir=Path(args.data_dir), known_current_file=Path(args.known_current) if args.known_current else None, results_dir=Path(args.results_dir))
    sc.load()
    sample_df = sc.run_spot_check(sample_n=args.sample_n, seed=args.seed)
    _ = sc.compare_with_known_current()


if __name__ == "__main__":
    main()
