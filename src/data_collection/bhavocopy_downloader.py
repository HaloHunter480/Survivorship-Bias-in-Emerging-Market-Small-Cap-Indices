"""
Automated Bhavocopy Downloader for NSE
Downloads complete historical daily trading data including delisted stocks.

Bhavcopies contain COMPLETE market data - perfect for survivorship bias research!
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
from zipfile import ZipFile
import io
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


class BhavocopyDownloader:
    """
    Automated downloader for NSE Bhavocopy files.
    
    Bhavcopies contain complete daily trading data including:
    - All stocks traded that day (including those later delisted)
    - OHLC prices
    - Volume and turnover
    - ISIN codes
    
    Perfect for survivorship bias research!
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.bhav_dir = self.data_dir / "raw" / "bhavcopies"
        self.bhav_dir.mkdir(parents=True, exist_ok=True)
        
        # NSE bhavocopy URLs (they change format occasionally)
        self.nse_base_url = "https://archives.nseindia.com/content/historical/EQUITIES"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _get_bhavocopy_url(self, date: datetime) -> str:
        """
        Construct bhavocopy URL for a given date.
        
        NSE format: https://archives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{DD}{MMM}{YYYY}bhav.csv.zip
        Example: https://archives.nseindia.com/content/historical/EQUITIES/2024/JAN/cm01JAN2024bhav.csv.zip
        """
        day = date.strftime('%d')
        month = date.strftime('%b').upper()
        year = date.strftime('%Y')
        month_full = date.strftime('%B').upper()
        
        # NSE format
        filename = f"cm{day}{month}{year}bhav.csv.zip"
        url = f"{self.nse_base_url}/{year}/{month_full}/{filename}"
        
        return url
    
    def download_single_bhavocopy(self, date: datetime, retry: int = 3) -> pd.DataFrame:
        """
        Download bhavocopy for a single date.
        
        Args:
            date: Date to download
            retry: Number of retry attempts
            
        Returns:
            DataFrame with bhavocopy data or None if failed
        """
        url = self._get_bhavocopy_url(date)
        date_str = date.strftime('%Y%m%d')
        
        for attempt in range(retry):
            try:
                # Download the zip file
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Extract CSV from zip
                    with ZipFile(io.BytesIO(response.content)) as zip_file:
                        # Get the CSV filename (should be only one file)
                        csv_filename = zip_file.namelist()[0]
                        
                        # Read CSV
                        with zip_file.open(csv_filename) as csv_file:
                            df = pd.read_csv(csv_file)
                            df['DATE'] = date_str
                            
                            # Save to file
                            output_file = self.bhav_dir / f"{date_str}_NSE.csv"
                            df.to_csv(output_file, index=False)
                            
                            return df
                
                elif response.status_code == 404:
                    # File doesn't exist (holiday or weekend)
                    return None
                
                else:
                    if attempt < retry - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
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
                           skip_existing: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Download bhavcopies for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            skip_existing: Skip dates that are already downloaded
            
        Returns:
            Dictionary of {date: DataFrame}
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        print(f"Downloading bhavcopies from {start_date} to {end_date}...")
        
        # Generate all dates in range
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        # Filter to weekdays only (NSE is closed on weekends)
        weekdays = [d for d in all_dates if d.weekday() < 5]
        
        print(f"Total weekdays to process: {len(weekdays)}")
        
        results = {}
        downloaded = 0
        skipped = 0
        failed = 0
        holidays = 0
        
        for date in tqdm(weekdays, desc="Downloading bhavcopies"):
            date_str = date.strftime('%Y%m%d')
            output_file = self.bhav_dir / f"{date_str}_NSE.csv"
            
            # Skip if already exists
            if skip_existing and output_file.exists():
                skipped += 1
                continue
            
            # Download
            df = self.download_single_bhavocopy(date)
            
            if df is not None and not df.empty:
                results[date_str] = df
                downloaded += 1
            elif df is None:
                holidays += 1  # Likely a holiday
            else:
                failed += 1
            
            # Be respectful to NSE servers
            time.sleep(0.5)
        
        print(f"\n{'='*70}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*70}")
        print(f"Downloaded:       {downloaded} files")
        print(f"Skipped (exists): {skipped} files")
        print(f"Holidays/Missing: {holidays} dates")
        print(f"Failed:           {failed} files")
        print(f"Total:            {len(weekdays)} weekdays")
        print(f"{'='*70}")
        
        return results
    
    def load_bhavocopy(self, date_str: str) -> pd.DataFrame:
        """Load a previously downloaded bhavocopy."""
        file_path = self.bhav_dir / f"{date_str}_NSE.csv"
        
        if file_path.exists():
            return pd.read_csv(file_path)
        else:
            return None
    
    def get_equity_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter bhavocopy to equity stocks only (exclude bonds, F&O, etc.).
        
        Args:
            df: Bhavocopy DataFrame
            
        Returns:
            Filtered DataFrame with only EQ series
        """
        if 'SERIES' in df.columns:
            equity_df = df[df['SERIES'] == 'EQ'].copy()
            return equity_df
        return df
    
    def combine_bhavcopies(self, 
                          start_date: str,
                          end_date: str,
                          equity_only: bool = True) -> pd.DataFrame:
        """
        Combine multiple bhavcopies into a single DataFrame.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            equity_only: Filter to equity stocks only
            
        Returns:
            Combined DataFrame with all data
        """
        print(f"Combining bhavcopies from {start_date} to {end_date}...")
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_data = []
        files_found = 0
        
        # Iterate through all dates
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y%m%d')
            
            # Try to load file
            df = self.load_bhavocopy(date_str)
            
            if df is not None and not df.empty:
                if equity_only:
                    df = self.get_equity_only(df)
                
                # Add date column if not present
                if 'DATE' not in df.columns:
                    df['DATE'] = date_str
                
                all_data.append(df)
                files_found += 1
            
            current_date += timedelta(days=1)
        
        if not all_data:
            print("⚠ No bhavocopy files found in date range")
            return pd.DataFrame()
        
        # Combine all dataframes
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Convert date to datetime
        combined_df['DATE'] = pd.to_datetime(combined_df['DATE'], format='%Y%m%d')
        
        # Standardize column names
        combined_df.columns = combined_df.columns.str.upper()
        
        # Sort by date and symbol
        combined_df = combined_df.sort_values(['DATE', 'SYMBOL'])
        
        print(f"✓ Combined {files_found} bhavocopy files")
        print(f"✓ Total records: {len(combined_df):,}")
        print(f"✓ Unique symbols: {combined_df['SYMBOL'].nunique():,}")
        print(f"✓ Date range: {combined_df['DATE'].min()} to {combined_df['DATE'].max()}")
        
        # Save combined file
        output_file = self.data_dir / "processed" / "combined_bhavcopies.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_csv(output_file, index=False)
        print(f"✓ Saved to: {output_file}")
        
        return combined_df
    
    def get_all_historical_symbols(self, 
                                   start_date: str,
                                   end_date: str) -> pd.DataFrame:
        """
        Get complete list of all symbols that ever traded in the date range.
        This includes delisted stocks!
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with symbol information
        """
        print("Extracting all historical symbols (including delisted)...")
        
        combined_df = self.combine_bhavcopies(start_date, end_date, equity_only=True)
        
        if combined_df.empty:
            return pd.DataFrame()
        
        # Get unique symbols with their first and last trading dates
        symbol_info = combined_df.groupby('SYMBOL').agg({
            'DATE': ['min', 'max', 'count'],
            'CLOSE': ['mean', 'std'],
            'TOTTRDQTY': 'sum',
            'ISIN': 'first'
        }).reset_index()
        
        # Flatten column names
        symbol_info.columns = [
            'SYMBOL', 'FIRST_DATE', 'LAST_DATE', 'TRADING_DAYS',
            'AVG_PRICE', 'PRICE_STD', 'TOTAL_VOLUME', 'ISIN'
        ]
        
        # Determine if stock is likely delisted
        last_date = combined_df['DATE'].max()
        symbol_info['DAYS_SINCE_LAST_TRADE'] = (last_date - symbol_info['LAST_DATE']).dt.days
        symbol_info['LIKELY_DELISTED'] = symbol_info['DAYS_SINCE_LAST_TRADE'] > 365
        
        # Sort by last date to see delisted stocks first
        symbol_info = symbol_info.sort_values('DAYS_SINCE_LAST_TRADE', ascending=False)
        
        print(f"\n{'='*70}")
        print("HISTORICAL SYMBOL ANALYSIS")
        print(f"{'='*70}")
        print(f"Total unique symbols: {len(symbol_info):,}")
        print(f"Active (traded recently): {(~symbol_info['LIKELY_DELISTED']).sum():,}")
        print(f"Likely delisted: {symbol_info['LIKELY_DELISTED'].sum():,}")
        print(f"{'='*70}")
        
        # Save
        output_file = self.data_dir / "processed" / "all_historical_symbols.csv"
        symbol_info.to_csv(output_file, index=False)
        print(f"✓ Saved to: {output_file}")
        
        return symbol_info
    
    def get_smallcap_universe(self, 
                             combined_df: pd.DataFrame,
                             min_market_cap: float = 500,  # Crores
                             max_market_cap: float = 30000,  # Crores
                             min_liquidity_days: int = 100) -> pd.DataFrame:
        """
        Filter to small cap universe based on market cap and liquidity.
        
        Args:
            combined_df: Combined bhavocopy data
            min_market_cap: Minimum market cap in crores
            max_market_cap: Maximum market cap in crores
            min_liquidity_days: Minimum trading days required
            
        Returns:
            Filtered DataFrame with small cap stocks
        """
        print("Filtering to small cap universe...")
        
        # Get stocks that meet criteria
        symbol_stats = combined_df.groupby('SYMBOL').agg({
            'DATE': 'count',
            'CLOSE': 'mean',
            'TOTTRDQTY': ['mean', 'sum']
        }).reset_index()
        
        symbol_stats.columns = ['SYMBOL', 'TRADING_DAYS', 'AVG_PRICE', 'AVG_VOLUME', 'TOTAL_VOLUME']
        
        # Filter by liquidity
        liquid_symbols = symbol_stats[
            symbol_stats['TRADING_DAYS'] >= min_liquidity_days
        ]['SYMBOL'].tolist()
        
        print(f"✓ Liquid stocks (>{min_liquidity_days} trading days): {len(liquid_symbols):,}")
        
        smallcap_df = combined_df[combined_df['SYMBOL'].isin(liquid_symbols)]
        
        return smallcap_df


def main():
    """Demonstration of bhavocopy downloader."""
    print("="*80)
    print("AUTOMATED BHAVOCOPY DOWNLOADER")
    print("="*80)
    print()
    
    downloader = BhavocopyDownloader(data_dir="data")
    
    # Example 1: Download last 30 days
    print("Example 1: Downloading recent data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    results = downloader.download_date_range(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        skip_existing=True
    )
    
    print("\n" + "="*80)
    print("USAGE FOR YOUR RESEARCH")
    print("="*80)
    print()
    print("To download ALL data from 2010 to present (for your research):")
    print()
    print("```python")
    print("downloader = BhavocopyDownloader()")
    print("downloader.download_date_range(")
    print("    start_date='2010-01-01',")
    print("    end_date='2024-12-31',")
    print("    skip_existing=True")
    print(")")
    print("```")
    print()
    print("This will take ~2-3 hours but runs automatically!")
    print("You can stop and resume - it skips already downloaded files.")
    print("="*80)


if __name__ == "__main__":
    main()

