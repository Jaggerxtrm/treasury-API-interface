# Treasury API Interface: Liquidity Monitoring System

A comprehensive system for monitoring U.S. dollar liquidity conditions through real-time analysis of fiscal flows, Federal Reserve operations, and money market dynamics. This project synthesizes data from multiple authoritative sources into a single **Liquidity Composite Index (LCI)** that provides actionable insights into market liquidity conditions.

## Project Overview

The Treasury API Interface tracks the three fundamental pillars of market liquidity:

3. **Market Plumbing** (25% weight) - Repo market stress and settlement fails

By integrating these components, the system provides a holistic view of liquidity conditions that no single indicator can capture.

## Features

✅ **Automated Data Collection**
- Treasury Daily Statement (DTS) via official Treasury API
- Federal Reserve data via FRED API
- NY Fed Markets API for repo operations and settlement fails
- Money market reference rates (SOFR, EFFR, BGCR, TGCR)

✅ **Comprehensive Analysis**
- Fiscal impulse calculation and TGA monitoring
- Net liquidity framework (Fed Assets - RRP - TGA)
- Repo submission ratios and stress indicators
- Settlement fails across all Treasury maturities
- Monetary policy regime detection (QE vs QT)

✅ **Composite Index**
- Z-score normalization for component comparability
- Weighted aggregation into single LCI metric
- Regime classification (Very Tight to Very Loose)
- Moving averages (MA5, MA20) for trend analysis

✅ **Production Ready**
- Robust error handling and data validation
- Automatic duplicate detection and aggregation
- CSV exports for all datasets
- Comprehensive terminal reports

## Quick Start

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/treasury-API-interface.git
cd treasury-API-interface
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure API keys:**

Edit `fed/config.py` and add your FRED API key:
```python
FRED_API_KEY = "your_fred_api_key_here"
```

Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html

### Running the Pipeline

Execute the complete liquidity analysis pipeline:

```bash
# Activate virtual environment
source venv/bin/activate

# Run each component in sequence
python fiscal/fiscal_analysis.py
python fed/fed_liquidity.py
python fed/nyfed_operations.py
python fed/nyfed_reference_rates.py
python fed/nyfed_settlement_fails.py

# Generate the Liquidity Composite Index
python fed/liquidity_composite_index.py
```

**Or run the complete pipeline with a single command:**

```bash
source venv/bin/activate && \
python fiscal/fiscal_analysis.py && \
python fed/fed_liquidity.py && \
python fed/nyfed_operations.py && \
python fed/nyfed_reference_rates.py && \
python fed/nyfed_settlement_fails.py && \
python fed/liquidity_composite_index.py
```

### Output Files

All analysis outputs are saved to the `outputs/` directory:

```
outputs/
├── fiscal/
│   └── fiscal_analysis_full.csv
└── fed/
    ├── fed_liquidity_full.csv
    ├── nyfed_repo_ops.csv
    ├── nyfed_rrp_ops.csv
    ├── nyfed_reference_rates.csv
    └── nyfed_settlement_fails.csv

liquidity_composite_index.csv (root directory)
```

## Comprehensive Documentation

Each component has detailed narrative documentation explaining the methodology, economic reasoning, and interpretation:

### Core Components

**[Fiscal Analysis](docs/FISCAL_ANALYSIS.md)**
- Understanding fiscal impulse and government cash flows
- Treasury General Account (TGA) as liquidity indicator
- Daily Treasury Statement (DTS) methodology
- Fiscal week alignment and GDP estimation

**[Fed Liquidity Monitor](docs/FED_LIQUIDITY.md)**
- The Net Liquidity framework
- QE vs QT regime detection
- SOFR-IORB spread as stress signal
- Reverse Repo (RRP) dynamics

**[NY Fed Operations](docs/NY_FED_OPERATIONS.md)**
- Standing Repo Facility (SRF) mechanics
- Submission ratios as stress indicators
- Reference rates (SOFR, EFFR, BGCR, TGCR)
- Money market plumbing health

**[Settlement Fails](docs/SETTLEMENT_FAILS.md)**
- What settlement fails indicate about market stress
- Primary dealer statistics methodology
- Collateral scarcity signals
- Fails to Deliver vs Fails to Receive

### The Composite Index

**[Liquidity Composite Index (LCI)](docs/LIQUIDITY_COMPOSITE_INDEX.md)**
- Three-pillar theoretical framework
- Component construction and normalization
- Weighting rationale (40/35/25)
- Regime classification and interpretation
- Practical applications for trading and risk management

## Project Structure

```
treasury-API-interface/
├── fiscal/
│   ├── fiscal_analysis.py           # Government spending/taxation analysis
│   └── utils/
├── fed/
│   ├── fed_liquidity.py              # Fed balance sheet & net liquidity
│   ├── nyfed_operations.py           # Repo/RRP operations
│   ├── nyfed_reference_rates.py      # Money market rates
│   ├── nyfed_settlement_fails.py     # Primary dealer fails
│   ├── liquidity_composite_index.py  # Main LCI calculator
│   ├── config.py                     # Configuration & API keys
│   └── utils/
│       ├── api_client.py             # FRED & NY Fed API clients
│       ├── data_loader.py            # Data loading utilities
│       └── report_generator.py       # Terminal output formatting
├── docs/                             # Comprehensive documentation
├── outputs/                          # Generated data files
└── README.md                         # This file
```

## Data Sources

- **Treasury API**: https://api.fiscaldata.treasury.gov/
- **FRED (Federal Reserve Economic Data)**: https://fred.stlouisfed.org/
- **NY Fed Markets API**: https://markets.newyorkfed.org/api/
- **NY Fed Primary Dealer Statistics**: https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics

## Requirements

- Python 3.8+
- pandas
- numpy
- requests
- FRED API key (free registration)

See `requirements.txt` for complete dependency list.

## Key Metrics Explained

### Fiscal Component
- **Total Impulse**: Government spending minus taxes (net cash injection)
- **TGA Balance**: Treasury's cash at the Fed (inverse liquidity indicator)
- **MA20 Impulse**: 20-day moving average smooths daily volatility

### Monetary Component
- **Net Liquidity**: Fed Assets - RRP - TGA (available private sector liquidity)
- **RRP Change**: Reverse repo decline releases liquidity
- **SOFR-IORB Spread**: Widening indicates funding stress

### Plumbing Component
- **Submission Ratio**: Repo demand / facility limit (stress when high)
- **Total Fails**: Settlement failures across all Treasuries (collateral scarcity)

## Interpreting the LCI

| LCI Score | Regime | Interpretation |
|-----------|--------|----------------|
| > +1.5 | Very Loose | Abundant liquidity, supportive of risk assets |
| +0.5 to +1.5 | Loose | Above-average liquidity conditions |
| -0.5 to +0.5 | Neutral | Balanced liquidity environment |
| -1.5 to -0.5 | Tight | Below-average liquidity, caution warranted |
| < -1.5 | Very Tight | Scarce liquidity, elevated stress conditions |

## Historical Context

The system provides historical data from **January 2022** onward, covering multiple liquidity regimes:
- Post-pandemic QE tapering
- 2022-2023 QT aggressive phase
- 2024-2025 QT maintenance phase
- Multiple quarter-end and tax deadline stress events

## Contributing

This is a research and analysis tool. Contributions are welcome for:
- Additional data sources
- Enhanced analytics
- Visualization tools
- Documentation improvements

## Disclaimer

This tool is for informational and educational purposes only. It is not financial advice. The Liquidity Composite Index is a model based on historical relationships that may change. Users should conduct their own analysis and consult with financial professionals before making investment decisions.

## License

Boh.

## Support & Contact

For questions, issues, or feature requests, please open an issue on GitHub or contact jagger.xtrm@gmail.com.

---

## Recent Updates

### Settlement Fails Integration (November 2025)
- ✅ Discovered and integrated NY Fed Primary Dealer API endpoints
- ✅ Added 22 Treasury fails series across all maturities
- ✅ Complete Market Plumbing component (repo + fails)
- ✅ Full historical data from 2022 to present

### System Enhancements
- ✅ Fixed duplicate date handling in repo operations
- ✅ Added submission_ratio calculation
- ✅ Improved data aggregation logic
- ✅ Enhanced error handling and validation

## Acknowledgments

This project synthesizes methodologies from:
- Zoltan Pozsar's work on money markets and plumbing
- CrossBorder Capital's liquidity framework
- Academic research on fiscal-monetary interaction
- Federal Reserve research on market functioning

---

**Built with data from the U.S. Treasury, Federal Reserve, and NY Fed. Powered by Python and pandas.**
