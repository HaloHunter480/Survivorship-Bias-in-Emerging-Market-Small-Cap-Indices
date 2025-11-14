"""
Module to fetch price data for ALL stocks including delisted ones.
This is critical for survivorship bias research.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import time
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')

try:
    from nsepy import get_history
    NSEPY_AVAILABLE = True
except ImportError:
    NSEPY_AVAILABLE = False
    print("Warning: nsepy not available. Install with: pip install nsepy")


class PriceFetcher:
    """
    Fetches historical price data for Indian stocks.
    Handles both active and delisted stocks.
    
    Challenges with delisted stocks:
    1. Yahoo Finance may not have complete data
    2. NSE historical data is limited
    3. Need to use multiple sources and cross-validate
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw" / "prices"
        self.processed_dir = self.data_dir / "processed" / "prices"
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Suffix for Indian stocks on Yahoo Finance
        self.yahoo_suffix = ".NS"  # NSE
        self.yahoo_suffix_bse = ".BO"  # BSE as fallback
        
    def _get_yahoo_symbol(self, nse_symbol: str) -> str:
        """Convert NSE symbol to Yahoo Finance format."""
        # Clean the symbol
        clean_symbol = nse_symbol.strip().replace(' ', '').upper()
        return f"{clean_symbol}{self.yahoo_suffix}"
    
    def fetch_single_stock(self, 
                          symbol: str, 
                          start_date: str,
                          end_date: str,
                          source: str = 'yahoo') -> Optional[pd.DataFrame]:
        """
        Fetch price data for a single stock.
        
        Args:
            symbol: Stock symbol (NSE format)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source ('yahoo' or 'nsepy')
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            if source == 'yahoo':
                return self._fetch_yahoo(symbol, start_date, end_date)
            elif source == 'nsepy' and NSEPY_AVAILABLE:
                return self._fetch_nsepy(symbol, start_date, end_date)
            else:
                print(f"Source {source} not available")
                return None
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def _fetch_yahoo(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Fetch data from Yahoo Finance."""
        yahoo_symbol = self._get_yahoo_symbol(symbol)
        
        try:
            # Try NSE first
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                # Try BSE as fallback
                yahoo_symbol_bse = symbol + self.yahoo_suffix_bse
                ticker = yf.Ticker(yahoo_symbol_bse)
                df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                df['symbol'] = symbol
                df.reset_index(inplace=True)
                
                # Standardize column names
                df.columns = df.columns.str.lower()
                return df
            
            return None
            
        except Exception as e:
            return None
    
    def _fetch_nsepy(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Fetch data from NSE Python library."""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            df = get_history(
                symbol=symbol,
                start=start_dt,
                end=end_dt,
                index=False
            )
            
            if not df.empty:
                df['symbol'] = symbol
                df.columns = df.columns.str.lower()
                return df
            
            return None
            
        except Exception as e:
            return None
    
    def fetch_multiple_stocks(self,
                            symbols: List[str],
                            start_date: str,
                            end_date: str,
                            save_individual: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Fetch price data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            save_individual: Whether to save individual stock files
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        print(f"Fetching price data for {len(symbols)} stocks...")
        print(f"Date range: {start_date} to {end_date}")
        
        results = {}
        failed_stocks = []
        
        for symbol in tqdm(symbols, desc="Downloading prices"):
            # Try Yahoo Finance first
            df = self.fetch_single_stock(symbol, start_date, end_date, source='yahoo')
            
            # If Yahoo fails and nsepy available, try nsepy
            if df is None and NSEPY_AVAILABLE:
                time.sleep(0.5)  # Rate limiting
                df = self.fetch_single_stock(symbol, start_date, end_date, source='nsepy')
            
            if df is not None and not df.empty:
                results[symbol] = df
                
                if save_individual:
                    filename = self.raw_dir / f"{symbol}_{start_date}_{end_date}.csv"
                    df.to_csv(filename, index=False)
            else:
                failed_stocks.append(symbol)
            
            time.sleep(0.1)  # Be respectful to APIs
        
        print(f"\n✓ Successfully fetched: {len(results)} stocks")
        print(f"✗ Failed to fetch: {len(failed_stocks)} stocks")
        
        if failed_stocks:
            # Save failed stocks list for manual investigation
            failed_file = self.raw_dir / f"failed_stocks_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(failed_file, 'w') as f:
                for stock in failed_stocks:
                    f.write(f"{stock}\n")
            print(f"Failed stocks list saved to: {failed_file}")
        
        return results
    
    def create_combined_dataset(self, 
                              price_data: Dict[str, pd.DataFrame],
                              output_format: str = 'long') -> pd.DataFrame:
        """
        Combine individual stock data into a single dataset.
        
        Args:
            price_data: Dictionary of symbol -> DataFrame
            output_format: 'long' (stacked) or 'wide' (pivoted)
            
        Returns:
            Combined DataFrame
        """
        print(f"Combining {len(price_data)} stocks into {output_format} format...")
        
        if output_format == 'long':
            # Stack all dataframes
            all_data = []
            for symbol, df in price_data.items():
                df_copy = df.copy()
                df_copy['symbol'] = symbol
                all_data.append(df_copy)
            
            combined = pd.concat(all_data, ignore_index=True)
            
            # Sort by date and symbol
            combined = combined.sort_values(['date', 'symbol'])
            
            # Save
            output_file = self.processed_dir / "combined_prices_long.csv"
            combined.to_csv(output_file, index=False)
            print(f"✓ Saved long format to: {output_file}")
            
            return combined
            
        elif output_format == 'wide':
            # Pivot to have symbols as columns
            # This is useful for correlation analysis
            
            # Extract close prices
            close_prices = {}
            for symbol, df in price_data.items():
                if 'close' in df.columns and 'date' in df.columns:
                    df_copy = df[['date', 'close']].copy()
                    df_copy.set_index('date', inplace=True)
                    close_prices[symbol] = df_copy['close']
            
            combined = pd.DataFrame(close_prices)
            combined.index = pd.to_datetime(combined.index)
            combined = combined.sort_index()
            
            # Save
            output_file = self.processed_dir / "combined_prices_wide.csv"
            combined.to_csv(output_file)
            print(f"✓ Saved wide format to: {output_file}")
            
            return combined
    
    def identify_delisted_stocks(self, 
                                universe: pd.DataFrame,
                                price_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Identify stocks that are delisted or have missing data.
        
        Args:
            universe: Complete stock universe DataFrame
            price_data: Fetched price data
            
        Returns:
            DataFrame with delisting analysis
        """
        print("Analyzing delisted and missing stocks...")
        
        analysis = []
        
        for _, row in universe.iterrows():
            symbol = row['symbol']
            
            info = {
                'symbol': symbol,
                'company_name': row.get('company_name', ''),
                'status_in_universe': row.get('status', 'unknown'),
                'data_available': symbol in price_data,
                'data_start_date': None,
                'data_end_date': None,
                'total_trading_days': 0,
                'likely_delisted': False
            }
            
            if symbol in price_data:
                df = price_data[symbol]
                if not df.empty:
                    info['data_start_date'] = df['date'].min()
                    info['data_end_date'] = df['date'].max()
                    info['total_trading_days'] = len(df)
                    
                    # Check if data ends significantly before present
                    last_date = pd.to_datetime(df['date'].max())
                    days_since_last_data = (datetime.now() - last_date).days
                    
                    if days_since_last_data > 365:  # No data for > 1 year
                        info['likely_delisted'] = True
            
            analysis.append(info)
        
        analysis_df = pd.DataFrame(analysis)
        
        # Save analysis
        output_file = self.processed_dir / "delisting_analysis.csv"
        analysis_df.to_csv(output_file, index=False)
        
        print(f"\n✓ Delisting analysis complete:")
        print(f"  - Total stocks analyzed: {len(analysis_df)}")
        print(f"  - Data available: {analysis_df['data_available'].sum()}")
        print(f"  - Likely delisted: {analysis_df['likely_delisted'].sum()}")
        print(f"  - Saved to: {output_file}")
        
        return analysis_df
    
    def calculate_returns(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate returns from price data.
        
        Args:
            price_data: DataFrame with price data (long format)
            
        Returns:
            DataFrame with returns added
        """
        print("Calculating returns...")
        
        df = price_data.copy()
        
        # Sort by symbol and date
        df = df.sort_values(['symbol', 'date'])
        
        # Calculate returns for each symbol
        df['return'] = df.groupby('symbol')['close'].pct_change()
        df['log_return'] = np.log(df['close'] / df.groupby('symbol')['close'].shift(1))
        
        # Calculate cumulative returns
        df['cumulative_return'] = df.groupby('symbol')['return'].apply(
            lambda x: (1 + x).cumprod() - 1
        )
        
        print("✓ Returns calculated")
        return df


def main():
    """Main function to demonstrate usage."""
    print("="*70)
    print("Price Data Fetcher for Survivorship Bias Research")
    print("="*70)
    print()
    
    # Example: Fetch data for a few stocks
    fetcher = PriceFetcher(data_dir="data")
    
    # Example stocks (mix of current and potentially delisted)
    example_stocks = ['RELIANCE', 'TCS', 'INFY', 'WIPRO', 'HDFCBANK']
    
    start_date = "2020-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Fetching example data for {len(example_stocks)} stocks...")
    price_data = fetcher.fetch_multiple_stocks(
        symbols=example_stocks,
        start_date=start_date,
        end_date=end_date
    )
    
    if price_data:
        # Create combined dataset
        combined = fetcher.create_combined_dataset(price_data, output_format='long')
        
        # Calculate returns
        with_returns = fetcher.calculate_returns(combined)
        
        print("\nSample data with returns:")
        print(with_returns.head(10))
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Load your complete stock universe")
        print("2. Fetch historical prices for ALL stocks (including delisted)")
        print("3. Analyze data completeness and identify delisting patterns")
        print("4. Prepare data for survivorship bias analysis")
        print("="*70)


if __name__ == "__main__":
    main()

