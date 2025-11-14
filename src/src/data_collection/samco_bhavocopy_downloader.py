"""
Automated Bhavocopy Downloader from Samco
Source: https://www.samco.in/bhavcopy-nse-bse-mcx

Samco provides bhavcopies from April 1, 2016 onwards.
This is PERFECT for your survivorship bias research!
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
from tqdm import tqdm
import warnings
from typing import Dict, List, Optional
warnings.filterwarnings('ignore')


class SamcoBhavocopyDownloader:
    """
    Downloads bhavcopies from Samco's service.
    
    Advantages over NSE:
    - Better organized and accessible
    - Available from April 2016
    - Multiple segments (NSE Cash, NSE F&O, BSE Cash, MCX)
    - More reliable downloads
    
    Perfect for survivorship bias research as it contains ALL stocks
    that traded on that day, including those later delisted!
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.bhav_dir = self.data_dir / "raw" / "bhavcopies"
        self.bhav_dir.mkdir(parents=True, exist_ok=True)
        
        # Samco bhavocopy API endpoint
        self.samco_api_url = "https://www.samco.in/api/bhavcopy"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.samco.in/bhavcopy-nse-bse-mcx',
            'Origin': 'https://www.samco.in',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def download_single_date(self, 
                            date: datetime, 
                            segment: str = 'NSE_CASH',
                            retry: int = 3) -> Optional[pd.DataFrame]:
        """
        Download bhavocopy for a single date from Samco.
        
        Args:
            date: Date to download
            segment: 'NSE_CASH', 'NSE_FO', 'BSE_CASH', or 'MCX'
            retry: Number of retry attempts
            
        Returns:
            DataFrame with bhavocopy data or None if failed
        """
        date_str = date.strftime('%Y-%m-%d')
        
        # Samco API parameters (you may need to adjust based on actual API)
        params = {
            'date': date_str,
            'segment': segment
        }
        
        for attempt in range(retry):
            try:
                # Try downloading the CSV directly
                # Samco format might be: https://www.samco.in/api/bhavcopy/download?date=YYYY-MM-DD&segment=NSE_CASH
                download_url = f"{self.samco_api_url}/download"
                
                response = self.session.get(download_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    # Check if response is CSV
                    if 'text/csv' in response.headers.get('Content-Type', '') or len(response.content) > 100:
                        # Parse CSV
                        from io import StringIO
                        df = pd.read_csv(StringIO(response.text))
                        
                        # Add metadata
                        df['DATE'] = date_str
                        df['SEGMENT'] = segment
                        
                        # Save to file
                        filename = f"{date.strftime('%Y%m%d')}_{segment}.csv"
                        output_file = self.bhav_dir / filename
                        df.to_csv(output_file, index=False)
                        
                        return df
                
                # If direct download fails, might need to use their form submission
                # This would require understanding their actual API structure
                
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
                    
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
        
        return None
    
    def download_date_range(self,
                           start_date: str,
                           end_date: str,
                           segment: str = 'NSE_CASH',
                           skip_existing: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Download bhavcopies for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            segment: Trading segment
            skip_existing: Skip already downloaded files
            
        Returns:
            Dictionary of {date: DataFrame}
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Samco data available from April 1, 2016
        earliest_date = datetime(2016, 4, 1)
        if start_dt < earliest_date:
            print(f"⚠ Samco data starts from {earliest_date.strftime('%Y-%m-%d')}")
            print(f"  Adjusting start date to {earliest_date.strftime('%Y-%m-%d')}")
            start_dt = earliest_date
        
        print(f"Downloading bhavcopies from Samco...")
        print(f"Date Range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
        print(f"Segment: {segment}")
        print()
        
        # Generate all dates
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        weekdays = [d for d in all_dates if d.weekday() < 5]
        
        print(f"Total weekdays to process: {len(weekdays)}")
        
        results = {}
        downloaded = 0
        skipped = 0
        failed = 0
        
        for date in tqdm(weekdays, desc="Downloading"):
            filename = f"{date.strftime('%Y%m%d')}_{segment}.csv"
            output_file = self.bhav_dir / filename
            
            if skip_existing and output_file.exists():
                skipped += 1
                continue
            
            df = self.download_single_date(date, segment)
            
            if df is not None and not df.empty:
                results[date.strftime('%Y%m%d')] = df
                downloaded += 1
            else:
                failed += 1
            
            time.sleep(0.5)  # Be respectful
        
        print(f"\n{'='*70}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*70}")
        print(f"Downloaded:       {downloaded} files")
        print(f"Skipped (exists): {skipped} files")
        print(f"Failed/Holidays:  {failed} dates")
        print(f"Total weekdays:   {len(weekdays)}")
        print(f"{'='*70}")
        
        return results
    
    def manual_download_instructions(self):
        """
        Provide instructions for manual download if automated method doesn't work.
        """
        print("="*80)
        print("MANUAL DOWNLOAD INSTRUCTIONS")
        print("="*80)
        print()
        print("If automated download doesn't work, you can download manually:")
        print()
        print("1. Visit: https://www.samco.in/bhavcopy-nse-bse-mcx")
        print()
        print("2. Select date range:")
        print("   - From: 2016-04-01 (earliest available)")
        print("   - To: Today's date")
        print()
        print("3. Select Segment: NSE Cash")
        print()
        print("4. Click 'Submit Download'")
        print()
        print("5. Save the downloaded CSV files to:")
        print(f"   {self.bhav_dir}")
        print()
        print("6. File naming convention:")
        print("   YYYYMMDD_NSE_CASH.csv")
        print("   Example: 20240101_NSE_CASH.csv")
        print()
        print("Note: You may need to do this in batches (3-6 months at a time)")
        print("      to avoid overwhelming the server.")
        print()
        print("="*80)
    
    def load_existing_files(self) -> pd.DataFrame:
        """
        Load all existing bhavocopy files from directory.
        Useful if you've manually downloaded files.
        """
        print("Loading existing bhavocopy files...")
        
        csv_files = list(self.bhav_dir.glob("*.csv"))
        
        if not csv_files:
            print("⚠ No bhavocopy files found in directory")
            return pd.DataFrame()
        
        print(f"Found {len(csv_files)} files")
        
        all_data = []
        for file in tqdm(csv_files, desc="Loading files"):
            try:
                df = pd.read_csv(file)
                all_data.append(df)
            except Exception as e:
                print(f"Warning: Could not load {file.name}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        
        # Standardize columns
        combined.columns = combined.columns.str.upper()
        
        # Ensure DATE column
        if 'DATE' in combined.columns:
            combined['DATE'] = pd.to_datetime(combined['DATE'])
        elif 'TIMESTAMP' in combined.columns:
            combined['DATE'] = pd.to_datetime(combined['TIMESTAMP'])
        
        print(f"✓ Loaded {len(combined):,} records")
        print(f"✓ Unique symbols: {combined['SYMBOL'].nunique():,}")
        print(f"✓ Date range: {combined['DATE'].min()} to {combined['DATE'].max()}")
        
        return combined
    
    def extract_equity_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract only equity stocks (exclude derivatives, bonds, etc.)."""
        if 'SERIES' in df.columns:
            equity = df[df['SERIES'] == 'EQ'].copy()
            print(f"Filtered to {len(equity):,} equity records")
            return equity
        return df
    
    def get_complete_stock_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract all unique stocks with their trading history.
        THIS IS YOUR SURVIVORSHIP BIAS GOLD!
        """
        print("\nExtracting complete stock universe...")
        
        # Get equity only
        equity_df = self.extract_equity_data(df)
        
        if equity_df.empty:
            return pd.DataFrame()
        
        # Analyze each symbol
        universe = equity_df.groupby('SYMBOL').agg({
            'DATE': ['min', 'max', 'count'],
            'CLOSE': ['mean', 'std', 'min', 'max'],
            'TOTTRDQTY': ['sum', 'mean'],
            'ISIN': 'first'
        }).reset_index()
        
        # Flatten column names
        universe.columns = [
            'SYMBOL', 'FIRST_TRADE_DATE', 'LAST_TRADE_DATE', 'TRADING_DAYS',
            'AVG_PRICE', 'PRICE_STD', 'MIN_PRICE', 'MAX_PRICE',
            'TOTAL_VOLUME', 'AVG_VOLUME', 'ISIN'
        ]
        
        # Calculate days since last trade
        latest_date = equity_df['DATE'].max()
        universe['DAYS_SINCE_LAST_TRADE'] = (
            latest_date - universe['LAST_TRADE_DATE']
        ).dt.days
        
        # Flag likely delisted stocks
        # If no trading for 365 days, likely delisted
        universe['LIKELY_DELISTED'] = universe['DAYS_SINCE_LAST_TRADE'] > 365
        universe['ACTIVE'] = ~universe['LIKELY_DELISTED']
        
        # Sort by status
        universe = universe.sort_values('DAYS_SINCE_LAST_TRADE', ascending=False)
        
        # Save
        output_file = self.data_dir / "processed" / "complete_stock_universe_samco.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        universe.to_csv(output_file, index=False)
        
        print(f"\n{'='*70}")
        print("COMPLETE STOCK UNIVERSE")
        print(f"{'='*70}")
        print(f"Total unique stocks:      {len(universe):,}")
        print(f"Active stocks:            {universe['ACTIVE'].sum():,}")
        print(f"Likely delisted:          {universe['LIKELY_DELISTED'].sum():,}")
        print(f"Delisting rate:           {universe['LIKELY_DELISTED'].mean():.1%}")
        print(f"{'='*70}")
        print(f"\n✓ Saved to: {output_file}")
        
        return universe


def main():
    """Demonstration and usage guide."""
    print("="*80)
    print("SAMCO BHAVOCOPY DOWNLOADER")
    print("Source: https://www.samco.in/bhavcopy-nse-bse-mcx")
    print("="*80)
    print()
    
    downloader = SamcoBhavocopyDownloader(data_dir="data")
    
    print("OPTION 1: Automated Download (May Require API Investigation)")
    print("-"*80)
    print("The automated approach requires understanding Samco's API.")
    print("If this doesn't work initially, use Option 2 (Manual Download).")
    print()
    
    print("OPTION 2: Manual Download (RECOMMENDED)")
    print("-"*80)
    downloader.manual_download_instructions()
    
    print("\nOPTION 3: Load Existing Files")
    print("-"*80)
    print("If you've already downloaded files manually, use:")
    print()
    print("```python")
    print("downloader = SamcoBhavocopyDownloader()")
    print("df = downloader.load_existing_files()")
    print("universe = downloader.get_complete_stock_universe(df)")
    print("```")
    print()
    
    print("="*80)
    print("WHY SAMCO DATA IS PERFECT FOR YOUR RESEARCH")
    print("="*80)
    print()
    print("✓ Contains ALL stocks that traded each day")
    print("✓ Includes stocks that later got delisted")
    print("✓ Complete OHLC and volume data")
    print("✓ Available from April 2016 (8+ years of data)")
    print("✓ Easy to identify delisted stocks (no trades for 365+ days)")
    print()
    print("This is exactly what you need to demonstrate survivorship bias!")
    print("="*80)


if __name__ == "__main__":
    main()

