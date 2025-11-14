#!/usr/bin/env python3
"""
infer_historical_constituents.py

Cleaned and reproducible version of your reconstruction script.
Accepts CLI args, safe defaults, and a quick/demo mode.
"""

from pathlib import Path
from datetime import datetime
from typing import List
import argparse
import pandas as pd
import numpy as np
import warnings
import logging

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("Inferrer")


class HistoricalConstituentInferrer:
    """
    Infer historical NIFTY Smallcap 250 constituents using multiple methods.

    Methods retained:
      - market cap ranking from bhavcopies (inferred)
      - include current constituents (known)
      - manual correction template support
    """

    def __init__(self, bhavcopies_dir: Path, data_dir: Path = Path("data")):
        self.bhav_dir = Path(bhavcopies_dir)
        self.data_dir = Path(data_dir)
        self.constituents_dir = self.data_dir / "constituents"
        self.constituents_dir.mkdir(parents=True, exist_ok=True)

    def load_current_constituents(self, current_file: Path) -> pd.DataFrame:
        """Load the current NIFTY Smallcap 250 list."""
        if not current_file.exists():
            raise FileNotFoundError(f"Current constituents file not found: {current_file}")

        df = pd.read_csv(current_file)
        # Standardize column names
        df.columns = df.columns.str.upper()
        if "SYMBOL" not in df.columns:
            raise ValueError("Current constituents file must contain a SYMBOL column")
        log.info(f"✓ Loaded {len(df)} current constituents from {current_file.name}")
        return df

    def load_all_bhavcopies(self, quick: bool = False, quick_n: int = 10) -> pd.DataFrame:
        """Load bhavcopies CSVs. quick=True loads first `quick_n` files for demo/testing."""
        log.info("Loading bhavcopies...")
        log.info(f"From: {self.bhav_dir.resolve()}")

        if not self.bhav_dir.exists():
            raise FileNotFoundError(f"Bhavcopies directory does not exist: {self.bhav_dir}")

        csv_files = sorted(self.bhav_dir.rglob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.bhav_dir}")

        if quick:
            csv_files = csv_files[:quick_n]
            log.info(f"Quick mode: loading first {len(csv_files)} files for demo")

        log.info(f"Found {len(csv_files)} files to process")
        all_data = []
        for file in csv_files:
            try:
                df = pd.read_csv(file)
            except Exception as e:
                log.warning(f"Warning: Could not read {file.name}: {e}")
                continue

            # Standardize columns
            df.columns = df.columns.str.upper()

            # Ensure at least SYMBOL and CLOSE present
            if "SYMBOL" not in df.columns or "CLOSE" not in df.columns:
                log.warning(f"Skipping {file.name}: missing SYMBOL or CLOSE column")
                continue

            # Add DATE column heuristics
            if "DATE" not in df.columns:
                if "TIMESTAMP" in df.columns:
                    df["DATE"] = df["TIMESTAMP"]
                else:
                    # try infer from filename (common pattern) - fallback to NaT
                    df["DATE"] = pd.NaT

            # Filter to equity series if available
            if "SERIES" in df.columns:
                try:
                    df = df[df["SERIES"] == "EQ"]
                except Exception:
                    pass

            all_data.append(df)

        if not all_data:
            raise ValueError("No valid bhavcopy data loaded. Check files and columns.")

        combined = pd.concat(all_data, ignore_index=True)

        # Normalize/convert date
        combined["DATE"] = pd.to_datetime(combined["DATE"], errors="coerce")

        # Some bhavcopies don't have TOTTRDQTY column name — try common alternatives
        if "TOTTRDQTY" not in combined.columns:
            for alt in ("TOTTRDQTY", "TOT_TRD_QTY", "TRDQTY", "VOLUME"):
                if alt in combined.columns:
                    combined.rename(columns={alt: "TOTTRDQTY"}, inplace=True)
                    break

        # Ensure numeric conversions
        for col in ("CLOSE", "TOTTRDQTY", "TOTTRDVAL"):
            if col in combined.columns:
                combined[col] = pd.to_numeric(combined[col], errors="coerce")

        log.info(f"✓ Loaded {len(combined):,} records")
        if combined["DATE"].notna().any():
            log.info(f"✓ Date range: {combined['DATE'].min()} to {combined['DATE'].max()}")
        log.info(f"✓ Unique symbols: {combined['SYMBOL'].nunique():,}")

        return combined

    def calculate_market_caps(self, bhav_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate approximate market caps for all stocks.
        Market Cap Proxy = CLOSE × TOTTRDQTY (proxy using volume).
        """
        log.info("\nCalculating market cap proxies...")
        # Fill minimal NaNs to avoid groupby issues
        bhav_df = bhav_df.copy()
        if "TOTTRDQTY" not in bhav_df.columns:
            log.warning("TOTTRDQTY missing; proceeding with CLOSE as proxy rank (less precise)")
            bhav_df["TOTTRDQTY"] = 1.0

        grouped = bhav_df.groupby(["DATE", "SYMBOL"], as_index=False).agg({
            "CLOSE": "last",
            "TOTTRDQTY": "sum",
            "TOTTRDVAL": "sum" if "TOTTRDVAL" in bhav_df.columns else ("CLOSE" if "CLOSE" in bhav_df.columns else "sum")
        })

        grouped["MARKET_CAP_PROXY"] = grouped["CLOSE"] * grouped["TOTTRDQTY"]
        grouped = grouped.dropna(subset=["MARKET_CAP_PROXY"])

        log.info(f"✓ Calculated market caps for {len(grouped):,} date-symbol pairs")
        return grouped

    def infer_constituents_by_ranking(self,
                                     market_data: pd.DataFrame,
                                     date: pd.Timestamp,
                                     top_n: int = 250,
                                     exclude_largecap_n: int = 150) -> List[str]:
        """
        Infer NIFTY Smallcap 250 constituents for a specific date.
        """
        # Attempt exact match first
        date_data = market_data[market_data["DATE"] == date]
        if date_data.empty:
            # choose nearest date
            all_dates = market_data["DATE"].dropna().unique()
            if len(all_dates) == 0:
                return []
            closest_date = min(all_dates, key=lambda x: abs((pd.Timestamp(x) - pd.Timestamp(date)).days))
            date_data = market_data[market_data["DATE"] == closest_date].copy()
        date_data = date_data.sort_values("MARKET_CAP_PROXY", ascending=False)
        smallcaps = date_data.iloc[exclude_largecap_n:exclude_largecap_n + top_n]
        return smallcaps["SYMBOL"].tolist()

    def reconstruct_historical_index(self,
                                     bhav_df: pd.DataFrame,
                                     current_constituents: pd.DataFrame,
                                     rebalance_frequency: str = "Q") -> pd.DataFrame:
        """
        Reconstruct historical index composition; semi-annual official, but we reconstruct quarterly by default.
        """
        log.info("\n" + "=" * 60)
        log.info("RECONSTRUCTING HISTORICAL INDEX COMPOSITION")
        log.info("=" * 60)

        market_data = self.calculate_market_caps(bhav_df)

        start_date = bhav_df["DATE"].min()
        end_date = bhav_df["DATE"].max()
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq=rebalance_frequency)

        log.info(f"Reconstructing for {len(rebalance_dates)} rebalancing periods...")
        historical_data = []

        for i, date in enumerate(rebalance_dates):
            log.info(f"Period {i + 1}/{len(rebalance_dates)}: {date.date()} ...", end=" ")
            constituents = self.infer_constituents_by_ranking(
                market_data,
                date,
                top_n=250,
                exclude_largecap_n=150
            )
            for symbol in constituents:
                historical_data.append({
                    "date": pd.Timestamp(date).date(),
                    "symbol": symbol,
                    "in_index": True,
                    "method": "inferred_ranking"
                })
            log.info(f"✓ {len(constituents)} stocks")

        historical_df = pd.DataFrame(historical_data)

        # Append known current constituents as the latest date to ensure completeness
        if "SYMBOL" in current_constituents.columns:
            latest_date = pd.Timestamp(end_date).date()
            known_df = pd.DataFrame({
                "date": [latest_date] * current_constituents.shape[0],
                "symbol": current_constituents["SYMBOL"].astype(str).tolist(),
                "in_index": [True] * current_constituents.shape[0],
                "method": ["known_current"] * current_constituents.shape[0]
            })
            historical_df = pd.concat([historical_df, known_df], ignore_index=True)

        output_file = self.constituents_dir / "reconstructed_historical_constituents.csv"
        historical_df.to_csv(output_file, index=False)
        log.info(f"\n✓ Saved reconstructed index: {output_file}")
        return historical_df

    def identify_index_changes(self, historical_df: pd.DataFrame) -> pd.DataFrame:
        """Identify entry and exit dates per symbol."""
        log.info("\n" + "=" * 60)
        log.info("IDENTIFYING INDEX ENTRY/EXIT EVENTS")
        log.info("=" * 60)

        rows = []
        for symbol in historical_df["symbol"].unique():
            s = historical_df[historical_df["symbol"] == symbol].sort_values("date")
            entry_date = pd.to_datetime(s["date"]).min()
            exit_date = pd.to_datetime(s["date"]).max()
            periods = len(s)
            latest_method = s[s["date"] == s["date"].max()]["method"].iloc[0]
            currently_in_index = latest_method == "known_current"
            rows.append({
                "symbol": symbol,
                "entry_date": entry_date.date() if not pd.isna(entry_date) else pd.NaT,
                "exit_date": exit_date.date() if not pd.isna(exit_date) else pd.NaT,
                "periods_in_index": periods,
                "currently_in_index": currently_in_index,
                "status": "active" if currently_in_index else "removed"
            })

        timeline_df = pd.DataFrame(rows)
        out = self.constituents_dir / "index_entry_exit_timeline.csv"
        timeline_df.to_csv(out, index=False)
        log.info(f"✓ Analyzed {len(timeline_df)} unique stocks")
        log.info(f"  - Currently in index: {timeline_df['currently_in_index'].sum()}")
        log.info(f"  - Removed from index: {(~timeline_df['currently_in_index']).sum()}")
        log.info(f"✓ Saved timeline: {out}")
        return timeline_df

    def create_manual_correction_template(self) -> None:
        """Create a CSV template for manual corrections (to merge later)."""
        log.info("\nCreating manual corrections template...")
        template = pd.DataFrame({
            "date": ["2024-09-30", "2024-03-31", "2023-09-30"],
            "symbol": ["EXAMPLE1", "EXAMPLE2", "EXAMPLE3"],
            "action": ["add", "remove", "add"],
            "reason": ["Index rebalancing", "Market cap drop", "IPO inclusion"],
            "source": ["NSE Circular XYZ", "NSE Circular ABC", "NSE Circular DEF"],
            "verified": [True, True, False],
            "notes": ["Confirmed from circular", "Cross-checked with BSE", "Need verification"]
        })
        template_file = self.constituents_dir / "manual_corrections_template.csv"
        template.to_csv(template_file, index=False)
        log.info(f"✓ Created template: {template_file}")


def main():
    parser = argparse.ArgumentParser(description="Reconstruct historical NIFTY Smallcap constituents from bhavcopies")
    parser.add_argument("--bhav_dir", type=str, default="data/sample",
                        help="Directory containing bhavcopy CSVs (default: data/sample for demos)")
    parser.add_argument("--current_file", type=str, default="data/sample/nifty_smallcap_250_current.csv",
                        help="CSV file of current constituents (default: data/sample/...)")
    parser.add_argument("--data_dir", type=str, default="data",
                        help="Output data directory (default: data/)")
    parser.add_argument("--quick", action="store_true", help="Quick demo mode: process first few files only")
    parser.add_argument("--quick_n", type=int, default=10, help="Number of files to load in quick mode")
    args = parser.parse_args()

    bhav_dir = Path(args.bhav_dir)
    current_file = Path(args.current_file)
    data_dir = Path(args.data_dir)

    log.info("=" * 60)
    log.info("HISTORICAL CONSTITUENT RECONSTRUCTION")
    log.info("Using bhavcopies + current constituents (demo-safe defaults)")
    log.info("=" * 60)

    inferrer = HistoricalConstituentInferrer(bhavcopies_dir=bhav_dir, data_dir=data_dir)

    # Step 1: load current constituents
    try:
        current = inferrer.load_current_constituents(current_file)
    except Exception as e:
        log.error(f"Error loading current constituents: {e}")
        return

    # Step 2: load bhavcopies
    try:
        bhav_data = inferrer.load_all_bhavcopies(quick=args.quick, quick_n=args.quick_n)
    except Exception as e:
        log.error(f"Error loading bhavcopies: {e}")
        return

    # Step 3: reconstruct index
    historical = inferrer.reconstruct_historical_index(bhav_data, current, rebalance_frequency="Q")

    # Step 4: identify entry/exit events
    timeline = inferrer.identify_index_changes(historical)

    # Step 5: create manual correction template
    inferrer.create_manual_correction_template()

    log.info("\nRECONSTRUCTION COMPLETE!")
    log.info("Files created:")
    log.info(f"- {inferrer.constituents_dir / 'reconstructed_historical_constituents.csv'}")
    log.info(f"- {inferrer.constituents_dir / 'index_entry_exit_timeline.csv'}")
    log.info(f"- {inferrer.constituents_dir / 'manual_corrections_template.csv'}")
    log.info("\nTo run full analysis on full raw bhavcopies, pass --bhav_dir path/to/your/bhavcopies --current_file path/to/current.csv")


if __name__ == "__main__":
    main()
