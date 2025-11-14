## ⏱️ Time Estimate

- **Quick Verification** (using provided processed data): **5 minutes**
- **Partial Reproduction** (reconstruct constituents, run analysis): **30 minutes**
- **Full Reproduction** (download all bhavcopies): **4-6 hours** (mostly automated)

---

## 🔧 Prerequisites

### System Requirements

- **OS**: macOS, Linux, or Windows (with WSL)
- **Python**: 3.8 or higher
- **RAM**: 8 GB minimum (16 GB recommended for full dataset)
- **Storage**: 2 GB for processed data, 5 GB if downloading raw bhavcopies

### Software Installation

```bash
# 1. Clone this repository
git clone https://github.com/yourusername/survivorship-bias-india.git
cd survivorship-bias-india

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Verify Installation

```bash
python -c "import pandas; import numpy; import matplotlib; print('✓ All dependencies installed')"
```

---

## 🚀 Reproduction Paths

Choose based on your needs:

---

## Path 1: Quick Verification (5 minutes)

**Goal**: Verify the analysis works using **existing processed data** (already in repository)

### Steps

```bash
# 1. Verify processed data exists
ls data/constituents/historical_constituents.csv
ls data/processed/all_bhavcopies_combined.csv

# 2. Run bias analysis (uses existing data)
python analyze_survivorship_bias.py

# 3. Generate visualizations
python create_key_visualization.py

# 4. Check outputs
open results/figures/COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png
open results/reports/detailed_bias_analysis.txt
```

### Expected Output

```
✓ Loaded 1,437 stocks from historical constituents
✓ Survivor portfolio: 252 stocks
✓ Complete portfolio: 1,437 stocks
✓ Survivorship bias: +4.94pp annual return
✓ Sharpe bias: +0.25 points
✓ Figures saved to results/figures/
```

**Result**: You've verified the core analysis works. All key findings should match the paper.

---

## Path 2: Partial Reproduction (30 minutes)

**Goal**: Reconstruct index constituents from existing bhavcopy data and re-run full analysis

### Steps

```bash
# 1. Verify you have the combined bhavcopy file
ls data/processed/all_bhavcopies_combined.csv
# Should show: ~500-800 MB file

# 2. Update paths in reconstruction script
nano infer_historical_constituents.py
# Line 280: Set bhavcopies_path and current_constituents_file
# (Instructions in script comments)

# 3. Reconstruct historical index membership (takes ~5-10 min)
python infer_historical_constituents.py

# 4. Run complete analysis pipeline
python run_research_auto.py

# 5. Review all outputs
ls results/figures/          # Should have 7 PNG files
ls results/reports/          # Should have detailed analysis
```

### Expected Files Generated

```
data/constituents/
  ├── historical_constituents.csv     # All 1,437 stocks with dates
  └── constituent_timeline.csv        # Entry/exit dates

results/figures/
  ├── COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png
  ├── 6_smoking_gun_dead_stocks.png
  ├── 5_removal_categories.png
  └── [4 additional figures]

results/reports/
  └── detailed_bias_analysis.txt
```

### Validation Checks

```bash
# Check reconstruction accuracy
python spot_check_classification.py
# Should show: "Current Survivors: 252/252 match (100% accuracy)"

# Check worst performers
python validate_worst_performers.py
# Should identify ~232 dead stocks
```

**Result**: You've independently reconstructed the index and verified all findings.

---

## Path 3: Full Reproduction (4-6 hours)

**Goal**: Download **all raw bhavcopies** from NSE/Samco and rebuild the entire dataset from scratch

### ⚠️ Important Notes

- Raw bhavcopies are **NOT included in this repository** due to size (3.85M records)
- You can download them from Samco Securities: https://www.samco.in/bhavcopy-nse-bse-mcx
- Samco limits downloads to **1 month at a time**, requiring ~110 manual downloads (2016-2025)
- Alternatively, use the provided automation script (requires browser)

### Steps

#### Option A: Manual Download (Tedious but Reliable)

```bash
# 1. Visit Samco bhavcopy archive
# https://www.samco.in/bhavcopy-nse-bse-mcx

# 2. Download monthly bhavcopies for each month from Sept 2016 to Sept 2025
# Save to: data/raw/bhavcopies/

# 3. Process all downloaded files
python process_existing_bhavcopies.py
# This will create: data/processed/all_bhavcopies_combined.csv
```

#### Option B: Semi-Automated Download (Recommended)

```bash
# 1. Install Selenium for browser automation
pip install selenium webdriver-manager

# 2. Run automated downloader (opens browser, requires manual CAPTCHA solving)
python auto_download_samco_monthly.py

# 3. Monitor progress
./check_progress.sh

# 4. Once complete, process files
python process_existing_bhavcopies.py
```

### After Data Collection

```bash
# Now proceed with full pipeline
python run_research_auto.py

# Or step-by-step:
python infer_historical_constituents.py    # ~10 min
python analyze_survivorship_bias.py        # ~5 min
python categorize_removals.py              # ~3 min
python create_key_visualization.py         # ~2 min
python validate_worst_performers.py        # ~2 min
```

**Result**: You've fully replicated the entire research from raw data to published results.

---

## 🔍 Detailed Script Descriptions

### Core Scripts

| Script | Purpose | Runtime | Input | Output |
|--------|---------|---------|-------|--------|
| `infer_historical_constituents.py` | Reconstruct index membership (2016-2025) | 10 min | Bhavcopies | `historical_constituents.csv` |
| `analyze_survivorship_bias.py` | Calculate bias metrics | 5 min | Historical constituents | Figures, reports |
| `create_key_visualization.py` | Generate 3-panel main figure | 2 min | Analysis results | PNG files |
| `categorize_removals.py` | Classify removed stocks | 3 min | Constituents | Removal breakdown |
| `validate_worst_performers.py` | Identify dead stocks | 2 min | Constituents + prices | Dead stock list |
| `spot_check_classification.py` | Validate accuracy | 1 min | Constituents | Accuracy report |

### One-Command Full Pipeline

```bash
# Runs everything in sequence
python run_research_auto.py
```

**What it does**:
1. Loads bhavcopy data
2. Reconstructs historical constituents
3. Builds survivor vs. complete portfolios
4. Calculates performance metrics
5. Quantifies survivorship bias
6. Generates all figures
7. Writes detailed report

**Expected runtime**: 15-20 minutes (with existing processed data)

---

## ✅ Validation Checklist

After running the analysis, verify these key numbers:

| Metric | Expected Value | Where to Check |
|--------|----------------|----------------|
| Total unique stocks | 1,437 | `historical_constituents.csv` (unique symbols) |
| Current survivors | 252 | `detailed_bias_analysis.txt` |
| Removed stocks | 1,185 | `detailed_bias_analysis.txt` |
| Removal rate | 82.5% | `detailed_bias_analysis.txt` |
| Survivor annual return | 26.17% | `detailed_bias_analysis.txt` |
| Complete annual return | 21.23% | `detailed_bias_analysis.txt` |
| **Survivorship bias** | **+4.94pp** | `detailed_bias_analysis.txt` |
| Sharpe bias | +0.25 | `detailed_bias_analysis.txt` |
| Dead stocks | 232 | `dead_stocks_list.csv` |
| Reconstruction accuracy | 100% (252/252) | Run `spot_check_classification.py` |

### Quick Validation Command

```bash
# Check all key metrics at once
grep -E "Survivor|Complete|Bias|Sharpe|stocks" results/reports/detailed_bias_analysis.txt | head -20
```

---

## 🐛 Troubleshooting

### Issue: "FileNotFoundError: data/processed/all_bhavcopies_combined.csv"

**Solution**: You need to either:
1. Download processed data from releases (if available)
2. Download raw bhavcopies and run `process_existing_bhavcopies.py`

### Issue: "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: Script runs but numbers don't match paper

**Solution**: Check paths in scripts
```bash
# Verify these variables are set correctly:
# In infer_historical_constituents.py (line ~280)
bhavcopies_path = "/path/to/your/BHAVCOPIES/"
current_constituents_file = "/path/to/current_list.csv"
```

### Issue: "Memory Error" when processing large datasets

**Solution**: Reduce chunk size
```python
# In process_existing_bhavcopies.py, use chunking:
for chunk in pd.read_csv(file, chunksize=100000):
    process(chunk)
```

### Issue: Figures not generating

**Solution**: Ensure matplotlib backend works
```bash
# macOS
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; print('✓ Backend OK')"

# If fails, install:
pip install pillow
```

---

## 📊 Expected Outputs

After successful reproduction:

### File Structure

```
results/
├── figures/
│   ├── COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png  # Main 3-panel figure
│   ├── 6_smoking_gun_dead_stocks.png                 # Worst performers
│   ├── 5_removal_categories.png                      # Removal breakdown
│   ├── 1_stock_timeline.png                          # Entry/exit timeline
│   ├── 2_returns_comparison.png                      # Distribution comparison
│   ├── 3_metrics_comparison.png                      # Bar charts
│   └── 4_delisting_analysis.png                      # Temporal patterns
│
├── reports/
│   ├── detailed_bias_analysis.txt                    # Full statistical output
│   └── research_report_YYYYMMDD.txt                  # Executive summary
│
└── tables/
    └── [statistical tables in CSV format]
```

### Key Figure Preview

**COMPREHENSIVE_SURVIVORSHIP_BIAS_ANALYSIS.png** should show:
- **Panel 1**: Cumulative returns diverging from ~0% to 244pp over 9 years
- **Panel 2**: Rolling Sharpe ratio consistently higher for survivor portfolio
- **Panel 3**: Stock count declining from ~1,200 to 252 over time

---

## 📞 Support

If you encounter issues:

1. **Check**: [Troubleshooting](#-troubleshooting) section above
2. **Read**: Detailed comments in each script
3. **Review**: `INDEX_OF_DOCUMENTATION.md` for specific topics
4. **Open Issue**: [GitHub Issues](https://github.com/HaloHunter480/survivorship-bias-india/issues)

---

## 🎯 For Academic Reviewers

**Recommended verification path**:

1. **Quick Check** (5 min): Run `python analyze_survivorship_bias.py` with provided data
2. **Validation** (2 min): Run `python spot_check_classification.py` to verify 100% accuracy
3. **Visual Inspection** (3 min): Review figures in `results/figures/`
4. **Read Paper** (30 min): `RESEARCH_PAPER_FINAL.md`

**Total verification time**: ~40 minutes to confirm core findings.

---

## 📜 Data Availability Statement

For academic journals requiring data availability:

> **Data**: All processed datasets are included in this repository (`data/constituents/`, `data/processed/`). Raw bhavcopies can be obtained from NSE India or Samco Securities' public archive (https://www.samco.in/bhavcopy-nse-bse-mcx). Processing code is provided (`process_existing_bhavcopies.py`).

> **Code**: All analysis code is open-source and available in this repository under MIT license.

> **Reproducibility**: Complete reproduction instructions provided in `HOW_TO_REPRODUCE.md`. Estimated reproduction time: 30 minutes (with processed data) to 6 hours (from raw data).

---

**Last Updated**: November 2025  
**Research Version**: 1.0  
**Python Version**: 3.8+
