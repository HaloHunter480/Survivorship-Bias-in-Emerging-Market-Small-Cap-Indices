"""
Visualization functions for survivorship bias research.
Create publication-quality plots for research paper.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


class SurvivorshipBiasVisualizer:
    """Create visualizations for survivorship bias research."""
    
    def __init__(self, output_dir: str = "results/figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_portfolio_comparison(self,
                                 survivor_results: pd.DataFrame,
                                 complete_results: pd.DataFrame,
                                 title: str = "Survivorship Bias Impact on Portfolio Performance",
                                 save: bool = True) -> None:
        """
        Plot side-by-side comparison of portfolio performance.
        
        Args:
            survivor_results: Portfolio results from survivor dataset
            complete_results: Portfolio results from complete dataset
            title: Plot title
            save: Whether to save the figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # 1. Cumulative returns
        ax = axes[0, 0]
        ax.plot(survivor_results['date'], 
               survivor_results['cumulative_returns'] * 100,
               label='Survivor-Only', linewidth=2, color='green')
        ax.plot(complete_results['date'],
               complete_results['cumulative_returns'] * 100,
               label='Complete Dataset', linewidth=2, color='red')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Return (%)')
        ax.set_title('Cumulative Returns Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Portfolio values
        ax = axes[0, 1]
        ax.plot(survivor_results['date'],
               survivor_results['portfolio_value'],
               label='Survivor-Only', linewidth=2, color='green')
        ax.plot(complete_results['date'],
               complete_results['portfolio_value'],
               label='Complete Dataset', linewidth=2, color='red')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_title('Portfolio Value Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Returns distribution
        ax = axes[1, 0]
        survivor_returns = survivor_results['returns'].dropna() * 100
        complete_returns = complete_results['returns'].dropna() * 100
        
        ax.hist(survivor_returns, bins=50, alpha=0.5, label='Survivor-Only', color='green')
        ax.hist(complete_returns, bins=50, alpha=0.5, label='Complete Dataset', color='red')
        ax.set_xlabel('Returns (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Returns Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 4. Rolling Sharpe Ratio
        ax = axes[1, 1]
        window = 12  # 12-period rolling window
        
        surv_rolling_sharpe = (
            survivor_results['returns'].rolling(window).mean() / 
            survivor_results['returns'].rolling(window).std() * np.sqrt(12)
        )
        comp_rolling_sharpe = (
            complete_results['returns'].rolling(window).mean() / 
            complete_results['returns'].rolling(window).std() * np.sqrt(12)
        )
        
        ax.plot(survivor_results['date'],
               surv_rolling_sharpe,
               label='Survivor-Only', linewidth=2, color='green')
        ax.plot(complete_results['date'],
               comp_rolling_sharpe,
               label='Complete Dataset', linewidth=2, color='red')
        ax.set_xlabel('Date')
        ax.set_ylabel('Rolling Sharpe Ratio')
        ax.set_title(f'{window}-Period Rolling Sharpe Ratio')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filename = self.output_dir / "portfolio_comparison.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to {filename}")
        
        plt.show()
    
    def plot_metrics_comparison(self,
                               survivor_metrics: Dict,
                               complete_metrics: Dict,
                               save: bool = True) -> None:
        """
        Create bar chart comparing key metrics.
        
        Args:
            survivor_metrics: Metrics from survivor dataset
            complete_metrics: Metrics from complete dataset
            save: Whether to save the figure
        """
        # Select key metrics to visualize
        metrics_to_plot = [
            'sharpe_ratio',
            'annualized_return',
            'volatility',
            'max_drawdown'
        ]
        
        # Prepare data
        survivor_values = [survivor_metrics.get(m, 0) for m in metrics_to_plot]
        complete_values = [complete_metrics.get(m, 0) for m in metrics_to_plot]
        
        # Create labels
        labels = ['Sharpe Ratio', 'Annual Return', 'Volatility', 'Max Drawdown']
        
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Performance Metrics Comparison', fontsize=16, fontweight='bold')
        
        for idx, (metric, label) in enumerate(zip(metrics_to_plot, labels)):
            ax = axes[idx // 2, idx % 2]
            
            values = [survivor_metrics.get(metric, 0), complete_metrics.get(metric, 0)]
            categories = ['Survivor-Only', 'Complete Dataset']
            colors = ['green', 'red']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.7)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.4f}',
                       ha='center', va='bottom', fontweight='bold')
            
            ax.set_title(label, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add bias annotation
            bias = values[0] - values[1]
            bias_pct = (bias / abs(values[1]) * 100) if values[1] != 0 else 0
            ax.text(0.5, max(values) * 0.9,
                   f'Bias: {bias:.4f} ({bias_pct:.1f}%)',
                   ha='center',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        if save:
            filename = self.output_dir / "metrics_comparison.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to {filename}")
        
        plt.show()
    
    def plot_delisting_analysis(self,
                               universe: pd.DataFrame,
                               save: bool = True) -> None:
        """
        Visualize delisting patterns.
        
        Args:
            universe: Universe DataFrame with delisting info
            save: Whether to save the figure
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Delisting Analysis', fontsize=16, fontweight='bold')
        
        # 1. Status distribution
        ax = axes[0]
        if 'status' in universe.columns:
            status_counts = universe['status'].value_counts()
            colors = ['green' if status == 'active' else 'red' 
                     for status in status_counts.index]
            
            bars = ax.bar(status_counts.index, status_counts.values, color=colors, alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontweight='bold')
            
            ax.set_xlabel('Status')
            ax.set_ylabel('Number of Stocks')
            ax.set_title('Stock Status Distribution')
            ax.grid(True, alpha=0.3, axis='y')
        
        # 2. Delisting reasons (if available)
        ax = axes[1]
        if 'removal_reason' in universe.columns:
            delisted = universe[universe['status'].isin(['removed', 'delisted'])]
            if len(delisted) > 0:
                reason_counts = delisted['removal_reason'].value_counts()
                
                ax.pie(reason_counts.values,
                      labels=reason_counts.index,
                      autopct='%1.1f%%',
                      startangle=90)
                ax.set_title('Delisting Reasons Distribution')
            else:
                ax.text(0.5, 0.5, 'No delisting data available',
                       ha='center', va='center', transform=ax.transAxes)
        else:
            ax.text(0.5, 0.5, 'Delisting reason data not available',
                   ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        
        if save:
            filename = self.output_dir / "delisting_analysis.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to {filename}")
        
        plt.show()
    
    def plot_bias_over_time(self,
                           survivor_results: pd.DataFrame,
                           complete_results: pd.DataFrame,
                           window: int = 12,
                           save: bool = True) -> None:
        """
        Plot how survivorship bias evolves over time.
        
        Args:
            survivor_results: Survivor portfolio results
            complete_results: Complete portfolio results
            window: Rolling window size
            save: Whether to save the figure
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle('Survivorship Bias Evolution Over Time', fontsize=16, fontweight='bold')
        
        # Calculate rolling metrics
        surv_rolling_return = survivor_results['returns'].rolling(window).mean() * 12
        comp_rolling_return = complete_results['returns'].rolling(window).mean() * 12
        
        surv_rolling_vol = survivor_results['returns'].rolling(window).std() * np.sqrt(12)
        comp_rolling_vol = complete_results['returns'].rolling(window).std() * np.sqrt(12)
        
        # 1. Rolling Return Bias
        ax = axes[0]
        return_bias = surv_rolling_return - comp_rolling_return
        
        ax.plot(survivor_results['date'], return_bias * 100,
               linewidth=2, color='purple')
        ax.fill_between(survivor_results['date'], 0, return_bias * 100,
                        alpha=0.3, color='purple')
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        ax.set_xlabel('Date')
        ax.set_ylabel('Return Bias (%)')
        ax.set_title(f'{window}-Period Rolling Return Bias')
        ax.grid(True, alpha=0.3)
        
        # 2. Rolling Sharpe Bias
        ax = axes[1]
        surv_rolling_sharpe = surv_rolling_return / surv_rolling_vol
        comp_rolling_sharpe = comp_rolling_return / comp_rolling_vol
        sharpe_bias = surv_rolling_sharpe - comp_rolling_sharpe
        
        ax.plot(survivor_results['date'], sharpe_bias,
               linewidth=2, color='orange')
        ax.fill_between(survivor_results['date'], 0, sharpe_bias,
                        alpha=0.3, color='orange')
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        ax.set_xlabel('Date')
        ax.set_ylabel('Sharpe Ratio Bias')
        ax.set_title(f'{window}-Period Rolling Sharpe Ratio Bias')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filename = self.output_dir / "bias_evolution.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to {filename}")
        
        plt.show()
    
    def create_summary_table(self,
                            survivor_metrics: Dict,
                            complete_metrics: Dict,
                            bias_analysis: Dict,
                            save: bool = True) -> pd.DataFrame:
        """
        Create formatted summary table for research paper.
        
        Args:
            survivor_metrics: Metrics from survivor dataset
            complete_metrics: Metrics from complete dataset
            bias_analysis: Bias analysis results
            save: Whether to save the table
            
        Returns:
            Formatted DataFrame
        """
        data = {
            'Metric': [
                'Annual Return (%)',
                'Annual Volatility (%)',
                'Sharpe Ratio',
                'Maximum Drawdown (%)',
                'Win Rate (%)'
            ],
            'Survivor-Only': [
                f"{survivor_metrics.get('annualized_return', 0) * 100:.2f}",
                f"{survivor_metrics.get('volatility', 0) * 100:.2f}",
                f"{survivor_metrics.get('sharpe_ratio', 0):.4f}",
                f"{survivor_metrics.get('max_drawdown', 0) * 100:.2f}",
                f"{survivor_metrics.get('win_rate', 0) * 100:.2f}"
            ],
            'Complete Dataset': [
                f"{complete_metrics.get('annualized_return', 0) * 100:.2f}",
                f"{complete_metrics.get('volatility', 0) * 100:.2f}",
                f"{complete_metrics.get('sharpe_ratio', 0):.4f}",
                f"{complete_metrics.get('max_drawdown', 0) * 100:.2f}",
                f"{complete_metrics.get('win_rate', 0) * 100:.2f}"
            ],
            'Bias': [
                f"{bias_analysis.get('return_bias', 0) * 100:.2f}",
                "-",
                f"{bias_analysis.get('sharpe_bias', 0):.4f}",
                "-",
                "-"
            ],
            'Bias (%)': [
                f"{bias_analysis.get('return_bias_pct', 0):.1f}",
                "-",
                f"{bias_analysis.get('sharpe_bias_pct', 0):.1f}",
                "-",
                "-"
            ]
        }
        
        summary_df = pd.DataFrame(data)
        
        if save:
            filename = self.output_dir.parent / "tables" / "summary_metrics.csv"
            filename.parent.mkdir(parents=True, exist_ok=True)
            summary_df.to_csv(filename, index=False)
            print(f"✓ Saved summary table to {filename}")
        
        return summary_df


def main():
    """Demonstration."""
    print("="*70)
    print("Survivorship Bias Visualization Tools")
    print("="*70)
    print("\nThis module provides:")
    print("1. Portfolio performance comparison plots")
    print("2. Metrics comparison visualizations")
    print("3. Delisting pattern analysis")
    print("4. Time-series bias evolution plots")
    print("5. Publication-ready summary tables")
    print("="*70)


if __name__ == "__main__":
    main()

