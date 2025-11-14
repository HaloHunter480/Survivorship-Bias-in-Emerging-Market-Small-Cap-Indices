"""
Statistical tests for survivorship bias significance.
Compare emerging markets (India) vs developed markets.
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')


class SurvivorshipBiasAnalyzer:
    """
    Perform statistical analysis on survivorship bias.
    Test if bias in emerging markets is significantly higher than developed markets.
    """
    
    def __init__(self):
        pass
    
    def test_bias_significance(self,
                              survivor_returns: pd.Series,
                              complete_returns: pd.Series,
                              alpha: float = 0.05) -> Dict:
        """
        Test if difference between survivor and complete datasets is significant.
        
        Args:
            survivor_returns: Returns from survivor-only dataset
            complete_returns: Returns from complete dataset
            alpha: Significance level
            
        Returns:
            Dictionary with test results
        """
        print("Testing statistical significance of survivorship bias...")
        
        # T-test for difference in means
        t_stat, p_value = stats.ttest_ind(survivor_returns, complete_returns)
        
        # Mann-Whitney U test (non-parametric alternative)
        u_stat, u_pvalue = stats.mannwhitneyu(survivor_returns, complete_returns, alternative='two-sided')
        
        # Levene's test for equality of variances
        levene_stat, levene_pvalue = stats.levene(survivor_returns, complete_returns)
        
        # Effect size (Cohen's d)
        cohens_d = self._calculate_cohens_d(survivor_returns, complete_returns)
        
        results = {
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < alpha,
            'mann_whitney_u': u_stat,
            'mann_whitney_p': u_pvalue,
            'levene_statistic': levene_stat,
            'levene_p': levene_pvalue,
            'equal_variance': levene_pvalue > alpha,
            'cohens_d': cohens_d,
            'effect_size_interpretation': self._interpret_cohens_d(cohens_d)
        }
        
        print(f"\n{'='*70}")
        print("STATISTICAL SIGNIFICANCE TEST")
        print(f"{'='*70}")
        print(f"T-statistic:              {t_stat:.4f}")
        print(f"P-value:                  {p_value:.6f}")
        print(f"Significant (α={alpha}):   {results['significant']}")
        print(f"Cohen's d:                {cohens_d:.4f} ({results['effect_size_interpretation']})")
        print(f"{'='*70}")
        
        return results
    
    def _calculate_cohens_d(self, group1: pd.Series, group2: pd.Series) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        var1, var2 = group1.var(), group2.var()
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0
        
        # Cohen's d
        d = (group1.mean() - group2.mean()) / pooled_std
        return d
    
    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        d_abs = abs(d)
        if d_abs < 0.2:
            return "negligible"
        elif d_abs < 0.5:
            return "small"
        elif d_abs < 0.8:
            return "medium"
        else:
            return "large"
    
    def compare_markets(self,
                       india_bias: float,
                       developed_bias: float,
                       india_se: float,
                       developed_se: float) -> Dict:
        """
        Compare survivorship bias between emerging (India) and developed markets.
        
        Args:
            india_bias: Measured bias in India (e.g., Sharpe ratio difference)
            developed_bias: Measured bias in developed markets
            india_se: Standard error of India bias estimate
            developed_se: Standard error of developed market bias estimate
            
        Returns:
            Dictionary with comparison results
        """
        print("Comparing survivorship bias across markets...")
        
        # Z-test for difference between two independent proportions/means
        diff = india_bias - developed_bias
        se_diff = np.sqrt(india_se**2 + developed_se**2)
        
        if se_diff > 0:
            z_score = diff / se_diff
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        else:
            z_score = np.inf
            p_value = 0
        
        # Relative difference
        if developed_bias != 0:
            relative_diff = (india_bias - developed_bias) / abs(developed_bias) * 100
        else:
            relative_diff = np.inf
        
        results = {
            'india_bias': india_bias,
            'developed_bias': developed_bias,
            'absolute_difference': diff,
            'relative_difference_pct': relative_diff,
            'z_score': z_score,
            'p_value': p_value,
            'india_higher': india_bias > developed_bias,
            'significant': p_value < 0.05
        }
        
        print(f"\n{'='*70}")
        print("MARKET COMPARISON")
        print(f"{'='*70}")
        print(f"India Bias:               {india_bias:.4f}")
        print(f"Developed Market Bias:    {developed_bias:.4f}")
        print(f"Difference:               {diff:.4f} ({relative_diff:.1f}%)")
        print(f"Z-score:                  {z_score:.4f}")
        print(f"P-value:                  {p_value:.6f}")
        print(f"India Higher:             {results['india_higher']}")
        print(f"{'='*70}")
        
        return results
    
    def bootstrap_confidence_interval(self,
                                     survivor_returns: pd.Series,
                                     complete_returns: pd.Series,
                                     n_iterations: int = 10000,
                                     confidence: float = 0.95) -> Dict:
        """
        Calculate bootstrap confidence intervals for survivorship bias.
        
        Args:
            survivor_returns: Returns from survivor dataset
            complete_returns: Returns from complete dataset
            n_iterations: Number of bootstrap iterations
            confidence: Confidence level (e.g., 0.95 for 95%)
            
        Returns:
            Dictionary with confidence intervals
        """
        print(f"Running bootstrap analysis ({n_iterations} iterations)...")
        
        np.random.seed(42)
        
        bias_estimates = []
        
        for _ in range(n_iterations):
            # Resample with replacement
            surv_sample = survivor_returns.sample(n=len(survivor_returns), replace=True)
            comp_sample = complete_returns.sample(n=len(complete_returns), replace=True)
            
            # Calculate Sharpe ratio for each
            surv_sharpe = surv_sample.mean() / surv_sample.std() if surv_sample.std() > 0 else 0
            comp_sharpe = comp_sample.mean() / comp_sample.std() if comp_sample.std() > 0 else 0
            
            # Calculate bias
            bias = surv_sharpe - comp_sharpe
            bias_estimates.append(bias)
        
        bias_estimates = np.array(bias_estimates)
        
        # Calculate confidence interval
        alpha = 1 - confidence
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        ci_lower = np.percentile(bias_estimates, lower_percentile)
        ci_upper = np.percentile(bias_estimates, upper_percentile)
        
        results = {
            'mean_bias': bias_estimates.mean(),
            'median_bias': np.median(bias_estimates),
            'std_bias': bias_estimates.std(),
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'confidence_level': confidence,
            'n_iterations': n_iterations
        }
        
        print(f"\n{'='*70}")
        print(f"BOOTSTRAP CONFIDENCE INTERVAL ({int(confidence*100)}%)")
        print(f"{'='*70}")
        print(f"Mean Bias:                {results['mean_bias']:.4f}")
        print(f"Median Bias:              {results['median_bias']:.4f}")
        print(f"Confidence Interval:      [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"{'='*70}")
        
        return results
    
    def analyze_delisting_patterns(self, universe: pd.DataFrame) -> Dict:
        """
        Analyze patterns in delisted stocks.
        
        Args:
            universe: Universe DataFrame with delisting information
            
        Returns:
            Dictionary with delisting analysis
        """
        print("Analyzing delisting patterns...")
        
        if 'status' not in universe.columns:
            print("Warning: No status column found")
            return {}
        
        # Count by status
        status_counts = universe['status'].value_counts()
        
        # Delisting rate
        total_stocks = len(universe)
        delisted = status_counts.get('removed', 0) + status_counts.get('delisted', 0)
        delisting_rate = delisted / total_stocks if total_stocks > 0 else 0
        
        # Analyze delisting reasons if available
        delisting_reasons = {}
        if 'removal_reason' in universe.columns:
            reasons = universe[universe['status'].isin(['removed', 'delisted'])]['removal_reason'].value_counts()
            delisting_reasons = reasons.to_dict()
        
        results = {
            'total_stocks': total_stocks,
            'active_stocks': status_counts.get('active', 0),
            'delisted_stocks': delisted,
            'delisting_rate': delisting_rate,
            'delisting_reasons': delisting_reasons
        }
        
        print(f"\n{'='*70}")
        print("DELISTING ANALYSIS")
        print(f"{'='*70}")
        print(f"Total Stocks:             {total_stocks}")
        print(f"Active Stocks:            {results['active_stocks']}")
        print(f"Delisted Stocks:          {delisted}")
        print(f"Delisting Rate:           {delisting_rate:.2%}")
        if delisting_reasons:
            print(f"\nDelisting Reasons:")
            for reason, count in delisting_reasons.items():
                print(f"  - {reason}: {count}")
        print(f"{'='*70}")
        
        return results


class MetricsCalculator:
    """Calculate various performance metrics for comparison."""
    
    @staticmethod
    def calculate_all_metrics(returns: pd.Series, 
                             risk_free_rate: float = 0.0,
                             periods_per_year: int = 252) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Number of periods in a year
            
        Returns:
            Dictionary of metrics
        """
        if len(returns) == 0:
            return {}
        
        # Basic statistics
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Annualized metrics
        annual_return = mean_return * periods_per_year
        annual_vol = std_return * np.sqrt(periods_per_year)
        
        # Sharpe Ratio
        excess_return = annual_return - risk_free_rate
        sharpe = excess_return / annual_vol if annual_vol > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(periods_per_year)
        sortino = excess_return / downside_std if downside_std > 0 else 0
        
        # Maximum Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        # Calmar Ratio
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # Skewness and Kurtosis
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)
        
        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5)
        
        # Conditional Value at Risk (Expected Shortfall)
        cvar_95 = returns[returns <= var_95].mean()
        
        metrics = {
            'mean_return': mean_return,
            'std_return': std_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_dd,
            'calmar_ratio': calmar,
            'skewness': skew,
            'kurtosis': kurt,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'best_return': returns.max(),
            'worst_return': returns.min(),
            'positive_periods': (returns > 0).sum() / len(returns)
        }
        
        return metrics
    
    @staticmethod
    def compare_metrics(survivor_metrics: Dict, complete_metrics: Dict) -> pd.DataFrame:
        """
        Create comparison table of metrics.
        
        Args:
            survivor_metrics: Metrics from survivor dataset
            complete_metrics: Metrics from complete dataset
            
        Returns:
            DataFrame with side-by-side comparison
        """
        comparison = pd.DataFrame({
            'Survivor-Only': survivor_metrics,
            'Complete Dataset': complete_metrics
        })
        
        comparison['Difference'] = comparison['Survivor-Only'] - comparison['Complete Dataset']
        comparison['Bias %'] = (comparison['Difference'] / comparison['Complete Dataset'].abs() * 100)
        
        return comparison


def main():
    """Demonstration."""
    print("="*70)
    print("Statistical Analysis for Survivorship Bias")
    print("="*70)
    print("\nThis module provides:")
    print("1. Statistical significance tests")
    print("2. Market comparison (emerging vs developed)")
    print("3. Bootstrap confidence intervals")
    print("4. Comprehensive metrics calculation")
    print("="*70)


if __name__ == "__main__":
    main()

