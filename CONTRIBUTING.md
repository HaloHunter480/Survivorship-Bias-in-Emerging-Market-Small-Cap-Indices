# Contributing to Survivorship Bias Research

Thank you for your interest in this research project! While this is primarily an academic research repository, contributions are welcome.

---

## 🎯 Ways to Contribute

### 1. Report Issues

Found a bug or error in the analysis?

- **Check**: [Existing Issues](https://github.com/HaloHunter480/survivorship-bias-india/issues)
- **Create**: New issue with:
  - Clear title describing the problem
  - Steps to reproduce
  - Expected vs. actual behavior
  - Your environment (OS, Python version)

### 2. Suggest Improvements

Ideas for methodology enhancements, additional analyses, or extensions?

- **Open**: Feature request issue
- **Describe**: What improvement you'd like and why it matters
- **Example**: "Add rolling window bias analysis to capture temporal variation"

### 3. Extend the Research

Interested in building on this work?

**Potential Extensions**:
- Apply methodology to other Indian indices (NIFTY Midcap, sectoral indices)
- Compare bias across emerging markets (Brazil, China, South Africa)
- Test strategy-specific bias (momentum, value, quality)
- Incorporate corporate actions database (mergers, spin-offs)

If you pursue an extension, please:
- Fork this repository
- Create a new branch (`git checkout -b feature/your-extension`)
- Add your analysis with clear documentation
- Submit a pull request with detailed description

### 4. Improve Documentation

Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples or tutorials
- Improve code comments
- Translate documentation

---

## 🔧 Development Setup

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/survivorship-bias-india.git
cd survivorship-bias-india

# 3. Create a branch
git checkout -b your-branch-name

# 4. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Make your changes

# 6. Test your changes
python run_research_auto.py  # Ensure everything still works

# 7. Commit and push
git add .
git commit -m "Description of your changes"
git push origin your-branch-name

# 8. Open a pull request on GitHub
```

---

## 📝 Code Style Guidelines

### Python

- **PEP 8**: Follow Python style guidelines
- **Comments**: Document complex logic
- **Docstrings**: Use for all functions
- **Type Hints**: Preferred but not required

Example:
```python
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate annualized Sharpe ratio.
    
    Parameters:
    -----------
    returns : pd.Series
        Daily returns
    risk_free_rate : float, default=0.0
        Daily risk-free rate
        
    Returns:
    --------
    float
        Annualized Sharpe ratio
    """
    excess_returns = returns - risk_free_rate
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
```

### Documentation

- **Markdown**: Use for all documentation
- **Clear Headers**: Use hierarchy (##, ###)
- **Code Blocks**: Use syntax highlighting
- **Examples**: Include practical examples

---

## 🧪 Testing

Before submitting:

1. **Run Full Pipeline**:
   ```bash
   python run_research_auto.py
   ```

2. **Check Key Metrics**:
   ```bash
   # Verify survivorship bias is still ~4.93pp
   grep "Survivorship bias" results/reports/detailed_bias_analysis.txt
   ```

3. **Validate Figures**:
   ```bash
   # Ensure all figures generate
   ls results/figures/*.png | wc -l  # Should be 7
   ```

4. **Test Edge Cases**:
   - Empty data handling
   - Missing values
   - Date range boundaries

---

## 📊 Data Contributions

### New Data Sources

If you have access to:
- **Official historical constituent lists** from NSE (would validate reconstruction)
- **Free-float data** (would refine market cap proxy)
- **Corporate action databases** (would improve stock tracking)
- **Delisting returns** (would refine bias estimates)

Please open an issue to discuss integration.

### Data Format

Any contributed data should:
- Be publicly available or shareable
- Include clear source documentation
- Use CSV format with standardized column names
- Include a data dictionary

---

## 🎓 Academic Collaboration

### For Researchers

If you're extending this research academically:

1. **Citation**: Please cite this work (see [LICENSE](LICENSE.md))
2. **Collaboration**: Open to co-authorship for substantial extensions
3. **Replication**: Share your replication package

### For Students

Using this for coursework or thesis?

- ✅ **Allowed**: Use as reference, cite appropriately
- ✅ **Encouraged**: Build extensions, apply to other markets
- ❌ **Not Allowed**: Copy without attribution

---

## 🔍 Review Process

### Pull Request Review

PRs will be reviewed for:

1. **Scientific Rigor**: Does it maintain research quality?
2. **Code Quality**: Is it readable, documented, tested?
3. **Reproducibility**: Can others replicate your addition?
4. **Documentation**: Is it clearly explained?

### Timeline

- **Initial Review**: Within 1 week
- **Feedback**: Provided via PR comments
- **Merge**: After all concerns addressed

---

## 🐛 Bug Reporting Guidelines

### Good Bug Report

```markdown
**Title**: Incorrect Sharpe calculation for portfolios with gaps

**Description**: 
When a stock has missing data (no trades for several days), the current
Sharpe ratio calculation treats missing values as zeros, biasing results.

**To Reproduce**:
1. Run `analyze_survivorship_bias.py`
2. Check results for stocks with trading gaps
3. Compare to manually calculated Sharpe

**Expected Behavior**: 
Should skip missing days or forward-fill prices

**Environment**:
- OS: macOS 14.0
- Python: 3.9.6
- pandas: 2.0.0

**Proposed Solution**:
Use `df.dropna()` before Sharpe calculation, or implement forward-fill logic.
```

### What to Include

- ✅ Clear, descriptive title
- ✅ Steps to reproduce
- ✅ Expected vs. actual behavior
- ✅ Environment details
- ✅ Proposed solution (if you have one)

### What to Avoid

- ❌ Vague titles ("It doesn't work")
- ❌ Missing reproduction steps
- ❌ Unformatted code dumps
- ❌ Demanding immediate fixes

---

## 📞 Questions?

- **Research Questions**: Open an issue with "Question" label
- **Technical Help**: See [HOW_TO_REPRODUCE.md](HOW_TO_REPRODUCE.md) first
- **Collaboration**: Email harjot.quant@gmail.com


---

## 🙏 Acknowledgment

All contributors will be:
- Acknowledged in README
- Listed in CONTRIBUTORS.md (if substantial contribution)
- Cited in academic papers if contribution is research-significant

---

## 📜 Code of Conduct

### Our Standards

- Be respectful and professional
- Focus on constructive feedback
- Acknowledge contributions
- Be patient with questions

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or inflammatory comments
- Personal attacks
- Publishing others' private information

### Enforcement

Violations may result in:
1. Warning
2. Temporary ban from repository
3. Permanent ban for severe/repeated violations

Report violations to: harjot.quant@gmail.com

---

**Thank you for contributing to open, reproducible research!** 🎓

---

*This document follows the [Contributor Covenant](https://www.contributor-covenant.org/) principles.*

