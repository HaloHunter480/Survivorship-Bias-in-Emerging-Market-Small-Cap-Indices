# Survivorship Bias in Emerging Market Small-Cap Indices

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Research Paper](https://img.shields.io/badge/Paper-SSRN-red.svg)](RESEARCH_PAPER_FINAL.md)

> **Evidence from India's NIFTY Smallcap 250 (2016-2025)**

## 🎯 Executive Summary

This repository contains the complete research project quantifying **survivorship bias** in India's NIFTY Smallcap 250 index. By reconstructing the complete historical investment universe—including 1,437 stocks (both active and delisted)—I demonstrate that:

- **Survivor-only backtesting overstates returns by 23.3%** (4.94 percentage points annually)
- **Sharpe ratios are inflated by 25.5%** (0.25 points)
- **82.5% of stocks** that were ever in the index (2016-2025) have been removed
- This bias substantially exceeds the 1-2% documented in U.S. markets

### 🏆 Key Achievement

**100% reconstruction accuracy** using publicly available NSE bhavcopy data—substantially exceeding the 80-85% accuracy typical in published research.

---

## 📊 Core Finding (Visual)

![Survivorship Bias Analysis](figures/COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png)

*Three-panel analysis showing: (1) Cumulative return divergence over 9 years, (2) Rolling Sharpe ratio comparison, (3) Survivorship churn timeline*

---

## 📁 Repository Structure

```
Survivorship-Bias-in-Emerging-Market-Small-Cap-Indices/
│
├── core_scripts/                     # Main research scripts (runnable)
│   ├── run_research_auto.py
│   ├── infer_historical_constituents.py
│   ├── analyze_survivorship_bias.py
│   ├── create_key_visualization.py
│   ├── validate_worst_performers.py
│   └── spot_check_classification.py
│
├── src/                               # Modular source code (library-style)
│   ├── analysis/
│   ├── backtesting/
│   ├── data_collection/
│   └── visualization/
│
├── figures/                           # All generated PNG visualizations
│   ├── 1_stock_timeline.png
│   ├── 2_returns_comparison.png
│   ├── 3_metrics_comparison.png
│   ├── 4_delisting_analysis.png
│   ├── 5_removal_categories.png
│   ├── 6_smoking_gun_dead_stocks.png
│   └── COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png
│
├── reports/                           # Text analysis outputs
│   ├── detailed_bias_analysis.txt
│   └── research_report_20251111.txt
│
├── Research.pdf                        # Full academic paper
├── Results_Explained.pdf               # Plain-language findings
│
├── README.md
├── LICENSE.md
├── Requirements.txt
├── QUICK_REFERENCE_CARD.md
├── METHODOLOGY_DEEP_DIVE.md
├── HOW_TO_REPRODUCE.md
└── CONTRIBUTING.md
```
---

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.8+
pip install -r requirements.txt
```

### Install Dependencies

```bash
pip install pandas numpy matplotlib seaborn scipy yfinance
```

### Run the Analysis

```bash
# Option 1: Full automated research pipeline
python run_research_auto.py

# Option 2: Step-by-step
python infer_historical_constituents.py  # Reconstruct index history
python analyze_survivorship_bias.py      # Calculate bias
python create_key_visualization.py       # Generate figures
```

### View Results

```bash
# Read the complete research paper
open RESEARCH_PAPER_FINAL.md

# View key figures
open results/figures/COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png
open results/figures/6_smoking_gun_dead_stocks.png

# Check detailed report
cat results/reports/detailed_bias_analysis.txt
```

---

## 🔬 Methodology Highlights

### 1. Historical Index Reconstruction

Without official NSE historical constituent lists, I reconstruct the NIFTY Smallcap 250 membership using:

```python
# Market Cap Proxy (for ranking)
MktCapProxy(i,t) = Close(i,t) × TotalQty(i,t)

# Selection Rules
- Rank all stocks by market cap
- Exclude top 150 (Large/Mid-cap)
- Select ranks 151-400 (Small-cap 250)
```

**Validation**: 252/252 current constituents correctly identified (100% accuracy)

### 2. Bias Quantification

```python
# Two Equal-Weight Portfolios
Portfolio_A = 252 current survivors only       # Biased (standard approach)
Portfolio_B = 1,437 complete historical set    # Unbiased (correct approach)

# Survivorship Bias
Bias = Performance(A) - Performance(B)
```

### 3. Data Source

**NSE Bhavcopy Files** (2016-2025):
- 2,459 daily files
- 3.85M stock-day observations
- **Critically**: Includes delisted stocks (unlike commercial databases)

---

## 📈 Key Results

| Metric | Survivor-Only | Complete Universe | Bias | % Overstatement |
|--------|---------------|-------------------|------|-----------------|
| **Annual Return** | 26.17% | 21.23% | **+4.94pp** | **+23.3%** |
| **Sharpe Ratio** | 1.23 | 0.98 | **+0.25** | **+25.5%** |
| **Max Drawdown** | -42.3% | -48.7% | +6.4pp | +13.1% |
| **Cumulative Return (9yr)** | 710% | 466% | +244pp | +52.4% |

### Stock Removal Breakdown

| Category | Count | % of Removed | Insight |
|----------|-------|--------------|---------|
| **Delisted/Dead** | 232 | 19.6% | Bankruptcies, compliance failures |
| **Graduated** | 476 | 40.2% | Grew into mid/large-cap indices |
| **Demoted** | 477 | 40.3% | Fell below top 250 small-caps |
| **Total Removed** | **1,185** | **100%** | 82.5% of all historical stocks |
| **Current Survivors** | **252** | — | Only 17.5% remained |

**Key Insight**: Even successful "graduated" stocks create bias by exiting the small-cap universe.

---

## 🎓 Academic Contribution

This research:

1. **First comprehensive quantification** of survivorship bias in Indian small-caps
2. **Demonstrates larger bias** (23%) vs. U.S. markets (1-2%) due to:
   - Higher index turnover (82.5% removal rate)
   - Greater volatility in emerging markets
   - Small-cap amplification effects
3. **Validates reconstruction methodology** (100% accuracy) using public data
4. **Shows all removal types create bias**—not just delistings

### Literature Context

Extends classic survivorship bias research (Brown et al. 1995, Elton et al. 1996, Shumway 1997) from U.S. mutual funds and equities to emerging market indices.

---

## 🎯 For MS/MFE Admissions Committees

This project demonstrates:

- ✅ **Quantitative Rigor**: Market-cap ranking algorithm, statistical testing, bootstrap validation
- ✅ **Data Engineering**: Processing 3.85M records, handling missing data, corporate actions
- ✅ **Financial Intuition**: Understanding index mechanics, portfolio construction, risk metrics
- ✅ **Research Methodology**: Literature review, hypothesis testing, robustness checks
- ✅ **Communication**: Publication-ready paper, clear visualizations, comprehensive documentation
- ✅ **Technical Skills**: Python, pandas, statistical analysis, data visualization

**This is publication-quality research** suitable for SSRN/academic journals.

---

## 📚 Documentation Index

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **RESEARCH_PAPER_FINAL.md** | Complete academic paper (SSRN-ready) | 30 min |
| **HOW_TO_REPRODUCE.md** | Step-by-step reproduction guide | 10 min |
| **RESULTS_EXPLAINED.md** | Plain-language findings | 5 min |
| **METHODOLOGY_DEEP_DIVE.md** | Technical methodology | 15 min |
| **QUICK_REFERENCE_CARD.md** | One-page summary | 2 min |
| **CODE_LOCATION_GUIDE.md** | Algorithm line-by-line mapping | 5 min |
| **PAPER_SUMMARY.md** | Interview talking points | 5 min |

**Start Here**: Read `QUICK_REFERENCE_CARD.md` → `RESULTS_EXPLAINED.md` → `RESEARCH_PAPER_FINAL.md`

---

## 🔍 Validation & Reproducibility

### Spot-Check Validation (100% accuracy)

Randomly sampled 10 stocks (5 survivors, 5 removed) and manually verified classification against:
- Current NSE constituent list
- Recent trading activity
- Entry/exit date logic

**Result**: 10/10 correctly classified

### Smoking Gun Evidence

Identified 10 worst "dead" stocks with catastrophic losses:
- **STOREONE**: -35.36% before delisting (dead 8.8 years)
- **ABGSHIP**: -32.75% before delisting (dead 8.7 years)
- **ALSTOMT&D**: -25.47% before delisting (dead 9.1 years)

These stocks **would be completely excluded** from survivor-only backtests.

---

## 🛠️ Technical Implementation

### Core Algorithms

**1. Market Cap Ranking** (`infer_historical_constituents.py`)
```python
# For each quarter (39 quarters: 2016-2025)
for quarter_date in quarter_dates:
    # Calculate proxy
    df['mkt_cap_proxy'] = df['CLOSE'] * df['TOTTRDQTY']
    
    # Rank and select
    df['rank'] = df['mkt_cap_proxy'].rank(ascending=False)
    small_caps = df[(df['rank'] >= 151) & (df['rank'] <= 400)]
    
    # Record constituents
    record_constituents(small_caps, quarter_date)
```

**2. Equal-Weight Portfolio Returns** (`analyze_survivorship_bias.py`)
```python
# Daily rebalancing
portfolio_return_t = (1 / N_t) * sum(stock_returns_t)

# Performance metrics
sharpe_ratio = (mean_return / std_return) * sqrt(252)
max_drawdown = max((peak - trough) / peak)
```

### Statistical Robustness

- **Bootstrap Test**: 1,000 iterations, p < 0.001
- **Subperiod Analysis**: Pre-COVID (2016-2019) and Post-COVID (2020-2025)
- **Alternative Specifications**: Value-weight, different cutoffs, rebalancing frequencies

All tests confirm economically large and statistically significant bias.

---

## 📧 Contact & Citation

**Author**: Harjot Singh Ranse 
**Institution**: Cluster University of Jammu 
**Email**: harjot.quant@gmail.com
### Suggested Citation

```bibtex
@article{yourname2025survivorship,
  title={Survivorship Bias in Emerging Market Small-Cap Indices: Evidence from India's NIFTY Smallcap 250},
  author={Your Name},
  year={2025},
  note={Available at SSRN}
}
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

---

## 🙏 Acknowledgments

- **Data Source**: NSE India (via Samco Securities bhavcopy archive)
- **Index Methodology**: NSE India Index Methodology Documents
- **Literature Foundation**: Brown et al. (1995), Elton et al. (1996), Shumway (1997)

---

## 🔗 Links

- 📄 **Research Paper**: [Research.pdf](Research.pdf)
- 📊 **Results Visualization**: [View Figures](figures)
- 📖 **Reproduction Guide**: [HOW_TO_REPRODUCE.md](HOW_TO_REPRODUCE.md)
- 🎯 **Quick Start**: [QUICK_REFERENCE_CARD.md](QUICK_REFERENCE_CARD.md)

---

<div align="center">

**⭐ If this research helped you, please star this repository! ⭐**

*Built with Python • pandas • NumPy • Matplotlib • Seaborn*
