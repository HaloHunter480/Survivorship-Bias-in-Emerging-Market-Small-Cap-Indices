"""
Backtesting engine specifically designed for survivorship bias research.
Allows running identical strategies on survivor-only vs complete datasets.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class SurvivorshipBacktester:
    """
    Specialized backtesting engine for survivorship bias research.
    
    Key features:
    1. Run identical strategy on two datasets (survivors vs all stocks)
    2. Track performance metrics for both
    3. Calculate survivorship bias impact
    4. Support multiple strategies
    """
    
    def __init__(self, 
                 price_data: pd.DataFrame,
                 universe_data: pd.DataFrame,
                 initial_capital: float = 1_000_000):
        """
        Initialize backtester.
        
        Args:
            price_data: Long format price data with columns [date, symbol, close, ...]
            universe_data: Universe data with survivor status
            initial_capital: Starting capital for backtest
        """
        self.price_data = price_data.copy()
        self.universe_data = universe_data.copy()
        self.initial_capital = initial_capital
        
        # Ensure date column is datetime
        if 'date' in self.price_data.columns:
            self.price_data['date'] = pd.to_datetime(self.price_data['date'])
        
        # Separate survivor and complete datasets
        self._prepare_datasets()
    
    def _prepare_datasets(self):
        """Prepare survivor-only and complete datasets."""
        print("Preparing datasets for survivorship bias analysis...")
        
        # Get list of survivors (stocks currently in index)
        if 'in_index_current' in self.universe_data.columns:
            survivors = self.universe_data[
                self.universe_data['in_index_current'] == True
            ]['symbol'].unique()
        elif 'status' in self.universe_data.columns:
            survivors = self.universe_data[
                self.universe_data['status'] == 'active'
            ]['symbol'].unique()
        else:
            # If no status column, assume all are survivors (suboptimal)
            survivors = self.universe_data['symbol'].unique()
            print("Warning: Could not identify survivors vs non-survivors")
        
        # Create survivor-only dataset
        self.survivor_data = self.price_data[
            self.price_data['symbol'].isin(survivors)
        ].copy()
        
        # Complete dataset is already self.price_data
        self.complete_data = self.price_data.copy()
        
        print(f"✓ Survivor dataset: {len(survivors)} stocks")
        print(f"✓ Complete dataset: {self.price_data['symbol'].nunique()} stocks")
        print(f"✓ Difference: {self.price_data['symbol'].nunique() - len(survivors)} delisted/removed stocks")
    
    def run_strategy(self,
                    strategy_func: Callable,
                    dataset_type: str = 'both',
                    rebalance_freq: str = 'M',
                    **strategy_params) -> Dict:
        """
        Run a trading strategy on specified dataset(s).
        
        Args:
            strategy_func: Function that returns portfolio weights
            dataset_type: 'survivor', 'complete', or 'both'
            rebalance_freq: Rebalancing frequency ('D', 'W', 'M', 'Q')
            **strategy_params: Additional parameters for strategy
            
        Returns:
            Dictionary with backtest results
        """
        results = {}
        
        if dataset_type in ['survivor', 'both']:
            print(f"\nRunning strategy on SURVIVOR dataset...")
            results['survivor'] = self._run_single_backtest(
                data=self.survivor_data,
                strategy_func=strategy_func,
                rebalance_freq=rebalance_freq,
                **strategy_params
            )
        
        if dataset_type in ['complete', 'both']:
            print(f"\nRunning strategy on COMPLETE dataset...")
            results['complete'] = self._run_single_backtest(
                data=self.complete_data,
                strategy_func=strategy_func,
                rebalance_freq=rebalance_freq,
                **strategy_params
            )
        
        # Calculate survivorship bias if both datasets were run
        if dataset_type == 'both':
            results['bias_analysis'] = self._calculate_bias(
                results['survivor'],
                results['complete']
            )
        
        return results
    
    def _run_single_backtest(self,
                            data: pd.DataFrame,
                            strategy_func: Callable,
                            rebalance_freq: str,
                            **strategy_params) -> Dict:
        """
        Run backtest on a single dataset.
        
        Returns:
            Dictionary with portfolio values, returns, and metrics
        """
        # Get rebalancing dates
        rebalance_dates = self._get_rebalance_dates(data, rebalance_freq)
        
        # Initialize portfolio
        portfolio_value = [self.initial_capital]
        portfolio_dates = [rebalance_dates[0]]
        holdings = {}
        
        for i in range(len(rebalance_dates) - 1):
            current_date = rebalance_dates[i]
            next_date = rebalance_dates[i + 1]
            
            # Get available data up to current date
            historical_data = data[data['date'] <= current_date]
            
            # Get strategy signals/weights
            weights = strategy_func(historical_data, current_date, **strategy_params)
            
            if weights is None or len(weights) == 0:
                # No signals, hold cash
                portfolio_value.append(portfolio_value[-1])
                portfolio_dates.append(next_date)
                continue
            
            # Get prices for holding period
            period_data = data[
                (data['date'] > current_date) & 
                (data['date'] <= next_date)
            ]
            
            # Calculate portfolio return for this period
            period_return = self._calculate_portfolio_return(
                period_data, weights, portfolio_value[-1]
            )
            
            new_value = portfolio_value[-1] * (1 + period_return)
            portfolio_value.append(new_value)
            portfolio_dates.append(next_date)
        
        # Create results DataFrame
        results_df = pd.DataFrame({
            'date': portfolio_dates,
            'portfolio_value': portfolio_value
        })
        
        results_df['returns'] = results_df['portfolio_value'].pct_change()
        results_df['cumulative_returns'] = (
            results_df['portfolio_value'] / self.initial_capital - 1
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(results_df)
        
        return {
            'portfolio': results_df,
            'metrics': metrics
        }
    
    def _get_rebalance_dates(self, data: pd.DataFrame, freq: str) -> List:
        """Get rebalancing dates based on frequency."""
        all_dates = sorted(data['date'].unique())
        
        if freq == 'D':
            return all_dates
        elif freq == 'W':
            # Weekly rebalancing
            dates_df = pd.DataFrame({'date': all_dates})
            dates_df['week'] = pd.to_datetime(dates_df['date']).dt.isocalendar().week
            dates_df['year'] = pd.to_datetime(dates_df['date']).dt.year
            rebalance = dates_df.groupby(['year', 'week'])['date'].first().tolist()
            return sorted(rebalance)
        elif freq == 'M':
            # Monthly rebalancing
            dates_df = pd.DataFrame({'date': all_dates})
            dates_df['month'] = pd.to_datetime(dates_df['date']).dt.to_period('M')
            rebalance = dates_df.groupby('month')['date'].first().tolist()
            return sorted(rebalance)
        elif freq == 'Q':
            # Quarterly rebalancing
            dates_df = pd.DataFrame({'date': all_dates})
            dates_df['quarter'] = pd.to_datetime(dates_df['date']).dt.to_period('Q')
            rebalance = dates_df.groupby('quarter')['date'].first().tolist()
            return sorted(rebalance)
        else:
            return all_dates
    
    def _calculate_portfolio_return(self, 
                                    period_data: pd.DataFrame,
                                    weights: Dict[str, float],
                                    current_value: float) -> float:
        """
        Calculate portfolio return for a holding period.
        
        Args:
            period_data: Price data for the holding period
            weights: Dictionary of {symbol: weight}
            current_value: Current portfolio value
            
        Returns:
            Portfolio return for the period
        """
        if not weights:
            return 0.0
        
        total_return = 0.0
        
        for symbol, weight in weights.items():
            # Get price data for this symbol
            symbol_data = period_data[period_data['symbol'] == symbol]
            
            if symbol_data.empty:
                # Stock not available (possibly delisted during period)
                # Assume 100% loss for this position
                total_return += weight * (-1.0)
                continue
            
            # Calculate return for this symbol
            start_price = symbol_data.iloc[0]['close']
            end_price = symbol_data.iloc[-1]['close']
            
            symbol_return = (end_price - start_price) / start_price
            
            # Add weighted return
            total_return += weight * symbol_return
        
        return total_return
    
    def _calculate_metrics(self, results_df: pd.DataFrame) -> Dict:
        """Calculate performance metrics."""
        returns = results_df['returns'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # Annualization factor (assuming monthly rebalancing)
        periods_per_year = 12
        
        # Total return
        total_return = results_df['cumulative_returns'].iloc[-1]
        
        # Annualized return
        n_periods = len(returns)
        annualized_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
        
        # Volatility
        volatility = returns.std() * np.sqrt(periods_per_year)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate
        win_rate = (returns > 0).sum() / len(returns)
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'n_periods': n_periods
        }
        
        return metrics
    
    def _calculate_bias(self, survivor_results: Dict, complete_results: Dict) -> Dict:
        """
        Calculate survivorship bias impact.
        
        Args:
            survivor_results: Results from survivor dataset
            complete_results: Results from complete dataset
            
        Returns:
            Dictionary with bias metrics
        """
        print("\nCalculating survivorship bias...")
        
        surv_metrics = survivor_results['metrics']
        comp_metrics = complete_results['metrics']
        
        bias = {
            'sharpe_bias': surv_metrics['sharpe_ratio'] - comp_metrics['sharpe_ratio'],
            'return_bias': surv_metrics['annualized_return'] - comp_metrics['annualized_return'],
            'sharpe_bias_pct': (
                (surv_metrics['sharpe_ratio'] - comp_metrics['sharpe_ratio']) / 
                comp_metrics['sharpe_ratio'] * 100 
                if comp_metrics['sharpe_ratio'] != 0 else np.inf
            ),
            'return_bias_pct': (
                (surv_metrics['annualized_return'] - comp_metrics['annualized_return']) / 
                abs(comp_metrics['annualized_return']) * 100
                if comp_metrics['annualized_return'] != 0 else np.inf
            ),
            'survivor_sharpe': surv_metrics['sharpe_ratio'],
            'complete_sharpe': comp_metrics['sharpe_ratio'],
            'survivor_return': surv_metrics['annualized_return'],
            'complete_return': comp_metrics['annualized_return']
        }
        
        print(f"\n{'='*70}")
        print("SURVIVORSHIP BIAS ANALYSIS")
        print(f"{'='*70}")
        print(f"Survivor Sharpe Ratio:    {surv_metrics['sharpe_ratio']:.4f}")
        print(f"Complete Sharpe Ratio:    {comp_metrics['sharpe_ratio']:.4f}")
        print(f"Sharpe Bias:              {bias['sharpe_bias']:.4f} ({bias['sharpe_bias_pct']:.2f}%)")
        print(f"\nSurvivor Annual Return:   {surv_metrics['annualized_return']:.2%}")
        print(f"Complete Annual Return:   {comp_metrics['annualized_return']:.2%}")
        print(f"Return Bias:              {bias['return_bias']:.2%}")
        print(f"{'='*70}")
        
        return bias


# Example strategy functions

def momentum_strategy(data: pd.DataFrame, 
                     current_date,
                     lookback: int = 60,
                     n_stocks: int = 20) -> Dict[str, float]:
    """
    Simple momentum strategy: Buy top N stocks by past returns.
    
    Args:
        data: Historical price data
        current_date: Current rebalancing date
        lookback: Lookback period in days
        n_stocks: Number of stocks to hold
        
    Returns:
        Dictionary of {symbol: weight}
    """
    # Get data for lookback period
    lookback_start = current_date - pd.Timedelta(days=lookback)
    period_data = data[
        (data['date'] >= lookback_start) & 
        (data['date'] <= current_date)
    ]
    
    # Calculate returns for each stock
    returns = {}
    for symbol in period_data['symbol'].unique():
        symbol_data = period_data[period_data['symbol'] == symbol]
        if len(symbol_data) >= 2:
            ret = (symbol_data.iloc[-1]['close'] - symbol_data.iloc[0]['close']) / symbol_data.iloc[0]['close']
            returns[symbol] = ret
    
    # Sort by returns and select top N
    sorted_stocks = sorted(returns.items(), key=lambda x: x[1], reverse=True)
    top_stocks = sorted_stocks[:n_stocks]
    
    # Equal weight
    if top_stocks:
        weight = 1.0 / len(top_stocks)
        weights = {symbol: weight for symbol, _ in top_stocks}
        return weights
    
    return {}


def mean_reversion_strategy(data: pd.DataFrame,
                           current_date,
                           lookback: int = 60,
                           n_stocks: int = 20) -> Dict[str, float]:
    """
    Simple mean reversion strategy: Buy bottom N stocks by past returns.
    
    Args:
        data: Historical price data
        current_date: Current rebalancing date
        lookback: Lookback period in days
        n_stocks: Number of stocks to hold
        
    Returns:
        Dictionary of {symbol: weight}
    """
    # Get data for lookback period
    lookback_start = current_date - pd.Timedelta(days=lookback)
    period_data = data[
        (data['date'] >= lookback_start) & 
        (data['date'] <= current_date)
    ]
    
    # Calculate returns for each stock
    returns = {}
    for symbol in period_data['symbol'].unique():
        symbol_data = period_data[period_data['symbol'] == symbol]
        if len(symbol_data) >= 2:
            ret = (symbol_data.iloc[-1]['close'] - symbol_data.iloc[0]['close']) / symbol_data.iloc[0]['close']
            returns[symbol] = ret
    
    # Sort by returns and select bottom N (worst performers)
    sorted_stocks = sorted(returns.items(), key=lambda x: x[1])
    bottom_stocks = sorted_stocks[:n_stocks]
    
    # Equal weight
    if bottom_stocks:
        weight = 1.0 / len(bottom_stocks)
        weights = {symbol: weight for symbol, _ in bottom_stocks}
        return weights
    
    return {}


def main():
    """Demonstration of usage."""
    print("="*70)
    print("Survivorship Bias Backtester")
    print("="*70)
    print("\nThis module provides tools to:")
    print("1. Run identical strategies on survivor vs complete datasets")
    print("2. Calculate survivorship bias impact")
    print("3. Compare performance metrics")
    print("\nSee research.py for full implementation example")
    print("="*70)


if __name__ == "__main__":
    main()

