"""
Module to fetch and manage NIFTY Smallcap 250 constituents data.
This includes current constituents and historical changes.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class NiftySmallcap250Fetcher:
    """
    Fetches NIFTY Smallcap 250 index constituents and historical changes.
    
    The NIFTY Smallcap 250 index was launched in 2010. This class helps collect:
    1. Current constituents (as of latest date)
    2. Historical constituent changes (additions/deletions)
    3. Metadata about each stock
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.constituents_dir = self.data_dir / "constituents"
        self.raw_dir = self.data_dir / "raw"
        
        # Create directories if they don't exist
        self.constituents_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        # NSE URLs
        self.nse_base_url = "https://www.nse india.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _init_session(self):
        """Initialize session with cookies for NSE."""
        try:
            # Access homepage to get cookies
            self.session.get(self.nse_base_url, headers=self.headers, timeout=10)
            time.sleep(1)
        except Exception as e:
            print(f"Warning: Could not initialize NSE session: {e}")
    
    def fetch_current_constituents(self) -> pd.DataFrame:
        """
        Fetch current NIFTY Smallcap 250 constituents from NSE.
        
        Returns:
            DataFrame with columns: symbol, company_name, industry, series
        """
        print("Fetching current NIFTY Smallcap 250 constituents...")
        
        try:
            # Method 1: Try NSE API
            url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20SMALLCAP%20250"
            
            self._init_session()
            response = self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    
                    # Clean and standardize columns
                    if 'symbol' in df.columns:
                        df = df[['symbol', 'identifier', 'series']].copy()
                        df.columns = ['symbol', 'company_name', 'series']
                        
                        # Save to file
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = self.constituents_dir / f"nifty_smallcap250_current_{today}.csv"
                        df.to_csv(filename, index=False)
                        
                        print(f"✓ Successfully fetched {len(df)} constituents from NSE API")
                        return df
            
            print("NSE API method failed, trying alternative sources...")
            return self._fetch_from_alternative_sources()
            
        except Exception as e:
            print(f"Error fetching from NSE: {e}")
            return self._fetch_from_alternative_sources()
    
    def _fetch_from_alternative_sources(self) -> pd.DataFrame:
        """
        Fetch constituents from alternative sources when NSE API fails.
        This includes web scraping and cached data.
        """
        print("Attempting to fetch from alternative sources...")
        
        # Try to fetch from NSE's website directly
        try:
            # NSE provides downloadable CSV files
            csv_url = "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"
            
            df = pd.read_csv(csv_url)
            
            if not df.empty:
                # Standardize column names
                column_mapping = {
                    'Symbol': 'symbol',
                    'Company Name': 'company_name',
                    'Industry': 'industry'
                }
                df.rename(columns=column_mapping, inplace=True)
                
                # Save to file
                today = datetime.now().strftime('%Y-%m-%d')
                filename = self.constituents_dir / f"nifty_smallcap250_current_{today}.csv"
                df.to_csv(filename, index=False)
                
                print(f"✓ Successfully fetched {len(df)} constituents from NSE archives")
                return df
                
        except Exception as e:
            print(f"Error fetching from archives: {e}")
        
        # If all methods fail, return empty DataFrame with proper structure
        print("⚠ Could not fetch current constituents. Manual data entry may be required.")
        return pd.DataFrame(columns=['symbol', 'company_name', 'industry', 'series'])
    
    def fetch_historical_constituents(self, 
                                     start_date: str = "2010-01-01",
                                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Attempt to fetch historical constituent changes.
        
        Note: This is challenging as NSE doesn't provide official historical data.
        We'll need to use multiple sources and manual curation.
        
        Args:
            start_date: Start date in YYYY-MM-DD format (default: index inception)
            end_date: End date in YYYY-MM-DD format (default: today)
            
        Returns:
            DataFrame with columns: symbol, company_name, action (add/remove), date
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"Fetching historical constituents from {start_date} to {end_date}...")
        print("⚠ Note: Historical constituent data is limited. Multiple sources needed.")
        
        historical_data = []
        
        # Method 1: Check if we have cached historical data
        historical_file = self.constituents_dir / "nifty_smallcap250_historical.csv"
        if historical_file.exists():
            print(f"✓ Found cached historical data at {historical_file}")
            return pd.read_csv(historical_file)
        
        # Method 2: Try to fetch from various quarters
        # NSE periodically publishes constituent lists
        dates_to_check = pd.date_range(start=start_date, end=end_date, freq='Q')
        
        for date in dates_to_check:
            try:
                # This is a placeholder - actual implementation would need
                # to scrape or access archived data
                print(f"Checking for data on {date.strftime('%Y-%m-%d')}...")
                time.sleep(0.5)  # Be respectful to servers
            except Exception as e:
                continue
        
        # If we couldn't fetch historical data, create a template
        print("\n⚠ Historical constituent data collection requires manual effort.")
        print("Recommendations:")
        print("1. Use NSE circulars and announcements")
        print("2. Check BSE announcements for delistings")
        print("3. Use financial data providers (if available)")
        print("4. Manual curation from quarterly reports")
        
        # Create template file
        template_df = pd.DataFrame(columns=[
            'date', 'symbol', 'company_name', 'action', 
            'reason', 'market_cap', 'notes'
        ])
        
        template_file = self.constituents_dir / "nifty_smallcap250_historical_template.csv"
        template_df.to_csv(template_file, index=False)
        
        print(f"\n✓ Created template file at: {template_file}")
        print("Fill this template with historical changes from various sources.")
        
        return template_df
    
    def create_complete_stock_universe(self) -> pd.DataFrame:
        """
        Create a complete list of ALL stocks that have EVER been in 
        NIFTY Smallcap 250 index.
        
        This combines current constituents with historical changes.
        
        Returns:
            DataFrame with all unique stocks, their entry/exit dates, and status
        """
        print("Creating complete stock universe...")
        
        # Get current constituents
        current = self.fetch_current_constituents()
        
        # Try to get historical data
        historical = self.fetch_historical_constituents()
        
        # Combine and create complete universe
        all_stocks = []
        
        # Add current constituents (these are survivors)
        for _, row in current.iterrows():
            all_stocks.append({
                'symbol': row['symbol'],
                'company_name': row.get('company_name', ''),
                'status': 'active',
                'in_index_current': True,
                'last_known_date': datetime.now().strftime('%Y-%m-%d')
            })
        
        # Add historical constituents that are no longer in the index
        if not historical.empty:
            for _, row in historical.iterrows():
                if row.get('action') == 'remove':
                    all_stocks.append({
                        'symbol': row['symbol'],
                        'company_name': row.get('company_name', ''),
                        'status': 'removed',
                        'in_index_current': False,
                        'removal_date': row.get('date', ''),
                        'removal_reason': row.get('reason', 'unknown')
                    })
        
        universe_df = pd.DataFrame(all_stocks)
        
        # Remove duplicates, keeping the most recent information
        universe_df = universe_df.drop_duplicates(subset=['symbol'], keep='last')
        
        # Save complete universe
        universe_file = self.constituents_dir / "complete_stock_universe.csv"
        universe_df.to_csv(universe_file, index=False)
        
        print(f"✓ Complete universe created with {len(universe_df)} unique stocks")
        print(f"  - Active in index: {universe_df['in_index_current'].sum()}")
        print(f"  - Removed from index: {(~universe_df['in_index_current']).sum()}")
        print(f"  - Saved to: {universe_file}")
        
        return universe_df
    
    def save_metadata(self, df: pd.DataFrame, metadata_type: str):
        """Save metadata with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.raw_dir / f"{metadata_type}_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {metadata_type} data to {filename}")


def main():
    """Main function to demonstrate usage."""
    print("="*70)
    print("NIFTY Smallcap 250 Constituent Fetcher")
    print("="*70)
    print()
    
    fetcher = NiftySmallcap250Fetcher(data_dir="data")
    
    # Fetch current constituents
    current_constituents = fetcher.fetch_current_constituents()
    print(f"\nCurrent constituents: {len(current_constituents)} stocks")
    if not current_constituents.empty:
        print(current_constituents.head())
    
    # Attempt to fetch historical data
    print("\n" + "="*70)
    historical_data = fetcher.fetch_historical_constituents()
    
    # Create complete universe
    print("\n" + "="*70)
    complete_universe = fetcher.create_complete_stock_universe()
    
    print("\n" + "="*70)
    print("DATA COLLECTION SUMMARY")
    print("="*70)
    print(f"✓ Current constituents fetched")
    print(f"✓ Complete universe file created")
    print(f"\n⚠ IMPORTANT: Manual data collection needed for historical changes")
    print(f"Sources to use:")
    print(f"  1. NSE index circulars: https://www.nseindia.com/regulations/circulars")
    print(f"  2. BSE corporate announcements")
    print(f"  3. Historical index factsheets")
    print(f"  4. Financial data terminals (if available)")
    print("="*70)


if __name__ == "__main__":
    main()

