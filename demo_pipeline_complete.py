#!/usr/bin/env python3
"""
Quick Pipeline Demo - Shows complete output capture with 7 scripts including desk report
"""

import os
import sys
from datetime import datetime

def create_demo_with_complete_output():
    """Create a demo showing complete script output capture"""
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(PROJECT_ROOT, "outputs", f"pipeline_raw-{timestamp}.md")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Demo content showing complete output for all 7 scripts
    demo_content = f"""# Treasury API Pipeline Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status:** Demo Mode - Showing COMPLETE output capture (no truncation)  
**Total Scripts:** 7  
**Total Duration:** ~145.8 seconds  

## Execution Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Success | 7 | 100.0% |
| ❌ Failed | 0 | 0.0% |

## Script Results - COMPLETE OUTPUT CAPTURE

### 1. python fiscal/fiscal_analysis.py

**Status:** ✅ Success  
**Duration:** 45.2 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Starting Fiscal Analysis...
Loading DTS deposits and withdrawals data...
✓ Retrieved 1,247 transactions through 2025-11-26
Loading TGA balance data...
✓ Retrieved 891 daily TGA observations through 2025-11-26
Fetching current GDP data...
✓ Current GDP: $29.3T (2024 Q3, annualized)

Processing fiscal analysis...
- Daily impulse calculations complete
- 20-day moving averages computed
- Monthly aggregations processed

Fiscal Analysis Complete
========================
Latest Daily Metrics (2025-11-26):
- Net Impulse: +$245.8M
- MA20 Impulse: +$312.4M
- Weekly Impulse % GDP: 0.38%
- TGA Balance: $425.7B

Weekly Aggregations (Week of 2025-11-22):
- Total Deposits: +$3.2T
- Total Withdrawals: +$2.8T
- Net Position: +$425.8B
- Household Spending: $1.8T (56.3% of total)

Monthly Aggregations (October 2025):
- Month-to-Date Net: +$6.2T
- Net vs 3Y Baseline: +$1.8T (+40.9%)
- Total Spending: $18.4T

Year-to-Date Fiscal 2025:
- FYTD Net: +$52.3T
- vs LY FYTD: +$8.7T (+20.0%)
- Average Daily Impulse: +$208.2M

Files Generated:
- fiscal/fiscal_data_2025-11-26.json
- fiscal/fiscal_analysis_2025-11-26.json

Analysis complete: 1,247 transactions processed
```

---

### 2. python fed/fed_liquidity.py

**Status:** ✅ Success  
**Duration:** 28.7 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Fed Liquidity Analysis - Enhanced Temporal Analysis
==================================================

Loading Fed time series data...
✓ RRP Balance (RRPONTSYD) - 2,145 data points
✓ Treasury Securities (WLTRECL) - 2,145 data points  
✓ Agency MBS (WSHOUSE) - 2,145 data points
✓ Total Assets (WALCL) - 2,145 data points
✓ SOFR Rate (SOFR) - 1,987 data points
✓ IORB Rate (IORB) - 2,145 data points
✓ EFFR Rate (EFFR) - 2,145 data points

Processing metrics...
✓ Net liquidity calculations complete
✓ 20-day moving averages computed
✓ Year-over-year changes calculated
✓ Spread volatilities computed

Temporal Analysis Results (as of 2025-11-26):
==========================================

Month-to-Date Performance:
- Net Liquidity MTD: +$18.5B
- RRP Balance MTD: -$45.2B (-18.1%)
- Balance Sheet MTD: -$62.8B
- SOFR-IORB Spread MTD_avg: 4.2 bps (vol: 1.8 bps)

Quarter-to-Date Performance:
- Period: 2025-10-01 to 2025-11-26
- RRP QTD Change: -$125.8B (-38.9%)
- QT Pace Annualized: -$945.2B/year
- SOFR Spread QTD Volatility: 2.1 bps (std)

3-Month Rolling Metrics:
- 3M Avg Net Liquidity: +$42.7B
- 3M Trend: Declining
- Current Percentile: 25th percentile (tight liquidity)

Latest Daily Metrics (2025-11-26):
================================
- Fed Total Assets: $7,185.6B (-$62.8B MTD)
- RRP Balance: $201.2B (-$45.2B MTD, -18.1%)
- SOFR Rate: 4.83% (+0.02% MTD)
- IORB Rate: 4.83% (unchanged)
- SOFR-IORB Spread: 4.2 bps
- Net Liquidity: +$18.5B
- TGA Balance: $425.7B

Spike Detection:
- SOFR-IORB spread: 4.2 bps vs 3.8 bps MA20 (+1.1 bps)
- No significant spikes detected (threshold: >10 bps)

Stress Index Analysis:
- Current: 42.1/100 (LOW stress)
- Components:
  * Spread Stress: 15.2/50
  * RRP Depletion Stress: 18.9/30
  * Volatility Stress: 8.0/20

Regime Detection:
- Current: QT_Liq_Drain (65% confidence)
- Signals: RRP declining, net liquidity declining, QT pace active

Correlations (3M):
- Net Liq vs TGA: -0.87 (strong inverse as expected)
- RRP vs SOFR Spread: 0.34 (moderate positive)
- Net Liq vs SOFR Spread: -0.52 (negative stress correlation)

Forecast (5-day simple trend):
- Net Liquidity: Expected to decline at -$8.2B/day
- RRP: Expected to decline at -$4.5B/day

Files Generated:
- fed/fed_liquidity_2025-11-26.json
- fed/temporal_metrics_2025-11-26.json

Fed liquidity analysis complete: 2,145 data points processed
```

---

### 3. python fed/nyfed_operations.py

**Status:** ✅ Success  
**Duration:** 12.3 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Operations Analysis
==========================

Loading NY Fed operating data...

DOMESTIC OPERATIONS SUMMARY (2025-11-26):
=========================================

Open Market Operations:
- Treasury Securities Held: $6,845.2B
- Agency Mortgage-Backed Securities: $425.8B
- Total SOMA Holdings: $7,271.0B

Securities Holdings Breakdown:
- Treasury Bills (Maturing < 1Y): $425.3B
- Treasury Notes (2Y-10Y): $4,821.7B
- Treasury Bonds (>10Y): $1,098.2B
- Agency MBS: $425.8B

Portfolio Characteristics:
- Average Maturity (Treasury): 6.8 years
- MBS Pass-Through Rate: 3.82%
- Portfolio Yield: 3.94%

Liquidity Operations:
- Primary Dealer Credit Facility: $0.0B (inactive)
- Standing Repo Facility: $0.0B (unused)
- Term Securities Lending Facility: $0.0B (inactive)

Market Operations Activity (Last 30 Days):
- Reverse Repo Operations Daily Avg: $201.2B
- Overnight Repo Operations: Minimal activity
- Treasury Buybacks: None scheduled

Securities Lending Activity:
- Securities Lent Daily Avg: $12.8B
- Collateral Received: High-quality Treasuries
- On-Demand Lending: Active

Balance Sheet Management:
- MBS Runoff Rate: $15.2B/month (passive)
- Treasury Reinvestment: Full reinvestment of proceeds
- Net Portfolio Decline: -$62.8B MTD

Risk Metrics:
- Duration Risk: 6.2 years (moderate)
- Credit Quality: AAA (U.S. Government)
- Concentration: High (U.S. Treasuries dominant)

Market Impact:
- Yield Curve Influence: Significant (large holder)
- Repo Market: Floor provider via RRP
- Treasury Market: Primary buyer in secondary

Files Generated:
- fed/nyfed_operations_2025-11-26.json
- fed/soma_holdings_2025-11-26.json

NY Fed operations analysis complete
```

---

### 4. python fed/nyfed_reference_rates.py

**Status:** ✅ Success  
**Duration:** 8.9 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Reference Rates Analysis
===============================

Loading reference rate data...

FUNDAMENTAL RATES (2025-11-26):
================================

Effective Federal Funds Rate (EFFR):
- Current Rate: 4.83%
- Target Range: 4.75% - 5.00%
- Distance from Target: +0.08%
- 20-Day MA: 4.82%
- Trend: Stable

Secured Overnight Financing Rate (SOFR):
- Current Rate: 4.83%
- vs EFFR: +0.00%
- 20-Day MA: 4.81%
- 5-Day Volatility: 2.3 bps
- Trend: Slightly increasing

Overnight Bank Funding Rate (OBFR):
- Current Rate: 4.82%
- vs SOFR: -0.01%
- 20-Day MA: 4.80%
- Stability Index: 0.87 (high)

Interest on Reserve Balances (IORB):
- Current Rate: 4.83%
- Policy Rate: 4.83%
- Effective vs Policy Rate: 0.00%
- Reserves Impact: $3,200B

Repo Market Rates:
- General Collateral Rate (GC): 4.82%
- Three-Month Term Rate: 4.81%
- Tri-Party Rate: 4.80%

Rate Spread Analysis:
====================

SOFR - IORB: 0.00 bps (normal range: 0-2 bps)
EFFR - IORB: 0.00 bps (normal range: 0-2 bps)
SOFR - EFFR: 0.00 bps (tight, normal)
GC - SOFR: -1.00 bps (moderate repo tightness)

Policy Effectiveness:
=====================

Rate Control Strength: 0.95 (excellent)
Market Functionality: 0.88 (good)
Transmission Efficiency: 0.91 (very good)

Historical Context:
- 2022 Peak Rates: 4.85%
- Current vs 2022-23 Highs: -0.02%
- Recent Rate Volatility: Low (median 1.8 bps)

Risk Indicators:
- Rate Shock Risk: Low
- Transmission Lags: Minimal
- Market Confidence: High

Files Generated:
- fed/reference_rates_2025-11-26.json
- fed/rate_spreads_2025-11-26.json

Reference rates analysis complete
```

---

### 5. python fed/nyfed_settlement_fails.py

**Status:** ✅ Success  
**Duration:** 7.1 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
NY Fed Settlement Fails Analysis
================================

Loading settlement fails data...

TREASURY SECURITIES SETTLEMENT FAILS (2025-11-26):
===================================================

Daily Fail Metrics:
- Treasury Fails: $2.1B
- Agency Securities Fails: $0.8B
- Total Fails: $2.9B
- Fail Rate: 0.032% of daily volume

Trend Analysis (20-day comparison):
- Treasury fails vs MA20: +0.3B (+16.7%)
- Agency fails vs MA20: -0.1B (-11.1%)
- Total fails trend: Slightly increasing

Historical Context:
- 2023 Peak Total Fails: $15.8B (March 2023)
- Current vs Historical Peak: -81.6%
- 2024 Average Daily Fails: $1.8B
- Current vs 2024 Avg: +61.1%

Market Structure Analysis:
=========================

Primary Dealer Activity:
- Fail Volume Concentration: Top 5 dealers = 68%
- Most Active Dealer: Goldman Sachs ($0.8B)
- Dealer Risk Metrics: Normal range

Institutional Fails:
- Money Market Funds: 42% of treasury fails
- Hedge Funds: 28% of treasury fails
- Insurance Companies: 15% of treasury fails
- Other Institutions: 15%

Security Type Breakdown:
- 2-Year Treasury: 32% of fails
- 5-Year Treasury: 28% of fails
- 10-Year Treasury: 18% of fails
- 30-Year Treasury: 12% of fails
- TIPS: 10% of fails

Liquidity Impact Assessment:
=============================

Market Functioning:
- Settlement System Health: 0.87/1.0 (good)
- Cash-Collateral Match: 0.92/1.0 (good)
- Market Depth: Adequate

Risk Indicators:
- Systemic Risk: Low (fails < $5B threshold)
- Concentration Risk: Moderate (dealer clustering)
- Operational Risk: Low

Policy Implications:
====================

Current fails level suggests:
- Repo market functioning normally
- Adequate cash availability
- No immediate policy action needed
- Monitor for escalations above $5B

Comparative Analysis:
vs. Previous Periods:
- 1 Week Ago: +$0.4B (+16.0%)
- 1 Month Ago: +$1.1B (+61.1%)
- 3 Months Ago: +$0.8B (+38.1%)

Files Generated:
- fed/settlement_fails_2025-11-26.json
- fed/fail_trends_2025-11-26.json

Settlement fails analysis complete
```

---

### 6. python fed/liquidity_composite_index.py

**Status:** ✅ Success  
**Duration:** 19.8 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
Liquidity Composite Index Analysis
==================================

Loading composite data sources...

COMPOSITE INDEX COMPONENTS (2025-11-26):
========================================

1. Balance Sheet Component (Weight: 25%):
   - Net Balance Sheet Flow: -$62.8B MTD
   - QT Pace Annualized: -$945.2B/year
   - Component Score: 68.2/100 (contractionary)

2. Rate Spread Component (Weight: 20%):
   - SOFR-IORB Spread: 4.2 bps
   - Spread Volatility: 1.8 bps
   - Component Score: 75.4/100 (stable)

3. RRP Utilization Component (Weight: 20%):
   - RRP Balance: $201.2B
   - Depletion Rate: Moderate
   - Component Score: 71.1/100 (normalizing)

4. Market Functioning Component (Weight: 15%):
   - Settlement Fails: $2.9B
   - Repo Market Tightness: 4.00%
   - Component Score: 82.7/100 (functional)

5. Flow Dynamics Component (Weight: 10%):
   - Net Liquidity Flow: +$18.5B MTD
   - Fiscal-Monetary Balance: Slightly expansionary
   - Component Score: 78.9/100 (balanced)

6. Volatility Component (Weight: 10%):
   - Rate Volatility: Low (2.3 bps)
   - Market Volatility Index: 0.32 (low)
   - Component Score: 85.1/100 (stable)

COMPOSITE INDEX CALCULATION:
============================

Liquidity Composite Index: 75.3/100
Index Classification: MOISTURIZING (65-85 range)
Index Trend: Slightly declining (t-1: 76.8)

Historical Comparison:
- 30-Day Average: 72.4
- 90-Day Average: 68.9
- 2024 Average: 70.2
- Current vs 6M High: -4.2 points
- Current vs 6M Low: +12.6 points

LIQUIDITY REGIME ASSESSMENT:
============================

Current Regime: Moisturizing (Index 75.3)
Characteristics: Balance sheet contracting, but rate spreads stable and RRP providing ample floor support

Regime Stability: Medium (confidence 62%)
Regime Duration: 8 weeks (since early October)

Risk Assessment:
- Imminent Tightening Risk: Low (would need Index < 50)
- Flash Crash Risk: Very Low (requires Index < 25)
- Market Stress Risk: Moderate (Index trending down)

Regime Transition Probabilities (30 days):
- Stay Moisturizing: 65%
- Move to Tight (Index < 65): 25%
- Move to Overflowing (Index > 85): 10%

Policy Implications:
===================

Current Index suggests:
- Fed QT can continue at moderate pace
- RRP floor remains effective
- Repo markets functioning normally
- No immediate liquidity interventions needed

Monitoring Priorities:
- RRP depletion trajectory
- Spread volatility acceleration
- Settlement fail volume increases

Component Contribution Analysis:
- Positive contributors: Rate spreads (75.4), Market functioning (82.7)
- Negative contributors: Balance sheet (68.2), RRP utilization (71.1)
- Highest weighting impact: Balance sheet (25% weight)

Files Generated:
- fed/liquidity_composite_2025-11-26.json
- fed/composite_components_2025-11-26.json
- fed/regime_analysis_2025-11-26.json

Liquidity composite index analysis complete
```

---

### 7. python generate_desk_report.py

**Status:** ✅ Success  
**Duration:** 34.8 seconds  
**Start:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**End:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Output:**
```
======================================================
TREASURY LIQUIDITY DESK REPORT
======================================================
Report Date: 2025-11-27 02:15:42
Version: 1.0.0
======================================================

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 0: EXECUTIVE SUMMARY
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

Key Findings:
• Fiscal Impulse: 0.38% of GDP (-0.26% vs 0.64% target) - BELOW TARGET
• Net Liquidity: $0.02T (+$0.02T MTD)
• RRP Balance: $201,246,000,000B (-18.1% MTD) - WARNING
• Monetary Regime: QT_Liq_Drain (65% confidence)
• Market Stress: 42/100 (LOW) ✅

Quick Metrics:
Metric                         Current      Target       Status
──────────────────────────────────────────────────────────────────
Weekly Impulse % GDP           0.38%        0.64%       ↓ -0.26%
Net Liquidity (T)              $0.02T       —            +0.02T MTD
RRP Balance (B)                $201246B      —            -45000B MTD
Regime                         QT_Liq_Drain  —            65% conf

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 1: FISCAL IMPULSE ANALYSIS
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

1.1 Current Standing vs Target
Metric                    Current        Target        Gap
───────────────────────────────────────────────────────────
Weekly Impulse % GDP      0.38%       0.64%       -0.26%
MA20 Daily Impulse        $312M      —             —
Daily Impulse (latest)    $246M      —             —

Interpretation: Impulse is BELOW TARGET (-0.26%), indicating contractionary fiscal stance.

1.2 Household Absorption
Household Impulse:        $1,800M
Household Share:          56.3% of total

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 2: TIME-FRAME DECOMPOSITION
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

2.1 Month-to-Date (MTD)

Period: 2025-11-01 to 2025-11-26
RRP MTD Change:           -$45,200M
Net Liquidity MTD:        $18,500M
Balance Sheet MTD:        -$62,800M
Avg SOFR-IORB Spread:     4.20 bps

2.2 Quarter-to-Date (QTD)

Period: 2025-10-01 to 2025-11-26
RRP QTD Change:           -$125,800B (-38.9%)
QT Pace (Annualized):     -$945,200M/year
Spread Volatility:        2.10 bps (std)

2.3 3-Month Rolling

3M Avg Net Liquidity:     $42,700M
3M Trend:                 Declining
Current Percentile:       25th

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 3: HISTORICAL COMPARISON & DEVIATION ANALYSIS
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

3.1 Year-over-Year Delta
Timeframe        Current        vs LY          Change
───────────────────────────────────────────────────────────
FYTD Cumulative  $52,300M    —              +$8,700M

3.2 3-Year Baseline Comparison
Current MA20:             $312M
vs 3-Year Baseline:       +$104M

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 4: LIQUIDITY COMPOSITION & FLOW DYNAMICS
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

4.1 TGA (Treasury General Account) Balance

Current Balance:          $425,700M

Status: NORMAL range

4.2 Household Absorption Breakdown

Total Household:          $1,800M (56.3%)

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 5: FED LIQUIDITY & MONETARY CONDITIONS
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

5.1 Net Liquidity Status
Component              Current        MTD Δ          Trend
───────────────────────────────────────────────────────────
Fed Assets             $7,185,600M    -$62,800M    -$15,200M/wk
RRP Balance            $201,246B     -$45,200B
TGA Balance            $425,700M    —
───────────────────────────────────────────────────────────
NET LIQUIDITY          $18,500M      $18,500M

5.2 Repo Market Stress Indicators
Metric                  Current    MA20       Threshold   Status
───────────────────────────────────────────────────────────
SOFR-IORB Spread        4.2 bps    3.8 bps    >10 bps     ✅ NORMAL
EFFR-IORB Spread        0.0 bps    —          —           ✅
RRP Usage               $201B      —          <$50B       🟡 WARNING
Stress Index            42/100     —          >50         ✅ LOW

5.3 Monetary Regime Confidence

Regime:                   QT_Liq_Drain (65% confidence)
Signals:                  RRP declining, net liquidity declining, QT pace active

5.4 Effective Policy Stance (QT/QE Decomposition)

QUANTITÀ - Net Balance Sheet Flow:
  Weekly Change:        📉 -$15,200M
  Direction:            QT (Drain)

Open Market Operations:
  MBS Runoff:           -$15,200M
  Bill Purchases:       $0M

QUALITÀ - Shadow QE Support:
  Total Support:        $0M
  (Supporto qualitativo: duration, risk appetite)

Interpretazione:
  • QT aggressivo (-$15,200M) senza compensazione significativa

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 6: INTEGRATED LIQUIDITY VIEW
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

6.1 Fiscal + Monetary Net Effect (Latest Week)
Source              Weekly Flow    Direction       Net Liquidity Impact
──────────────────────────────────────────────────────────────────────────
Fiscal Impulse      +0.3B/week      Injection       +0.3B
Tax Receipts        -0.4B/week      Drain           -0.4B
Fed QT (Assets)     -1.5B/week      Drain           -1.5B
RRP Drawdown        +2.3B/week      Injection       +2.3B
TGA Net Change      -0.1B/week      Drain           -0.1B
──────────────────────────────────────────────────────────────────────────
NET WEEKLY          —              Net Injection       +0.6B/week

Conclusion: Moderate net injection - Supportive liquidity environment.

6.2 Correlations (3-Month)

Net Liq vs TGA:           -0.87 (mechanical inverse expected)
RRP vs SOFR Spread:       +0.34
Net Liq vs SOFR Spread:   -0.52 (stress indicator)

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 7: RISK ASSESSMENT & OUTLOOK
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

7.1 Key Risks

1. RRP Depletion Watch (ELEVATED) 🟡
   - RRP at $201246B, approaching $50B floor
   - Implication: Monitor for potential policy adjustment

7.2 Base Case Outlook (30 Days)

• Net Liquidity: Expected to trend declining (R²=0.82)
• RRP: Expected to trend declining
• Fed Policy: QT_Liq_Drain regime likely to continue barring major market disruption

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
SECTION 8: ACTIONABLE INTELLIGENCE
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

For Rates Traders:
• Front-end: RRP depletion suggests floor risk on short rates - favor receivers
• Curve: SOFR-IORB at 4.2 bps signals stress - flattener bias

For Equity/Credit:
• Risk-on: Net liquidity injection of +0.6B/week supportive

For Macro Strategy:
• Regime: QT_Liq_Drain with 65% confidence
• GDP Impact: Fiscal impulse at 0.38% GDP annualized

======================================================================
END OF REPORT
======================================================================

✓ Report saved to: outputs/desk_report_2025-11-27.md
```

---

## Pipeline Metadata

- **Pipeline Version:** 1.0.0
- **Python Version:** {sys.version}
- **Working Directory:** {PROJECT_ROOT}
- **Scripts Executed:**
  1. fiscal/fiscal_analysis.py
  2. fed/fed_liquidity.py
  3. fed/nyfed_operations.py
  4. fed/nyfed_reference_rates.py
  5. fed/nyfed_settlement_fails.py
  6. fed/liquidity_composite_index.py
  7. generate_desk_report.py
- **Output Directory:** os.path.dirname(output_file)

## Usage Instructions

To run the actual pipeline with real data execution and complete output capture:

**Python Version:**
```bash
python run_pipeline.py
```

**Bash Version:**  
```bash
./run_pipeline.sh
```

Both will create timestamped files like: `outputs/pipeline_raw-YYYY-MM-DD_HH-MM-SS.md`

*Note: This demo shows the format with COMPLETE (untruncated) script output as requested*

*End of Pipeline Report*
"""
    
    # Write demo report
    with open(output_file, 'w') as f:
        f.write(demo_content)
    
    print(f"Demo pipeline report created: {output_file}")
    print("This shows COMPLETE output capture - use run_pipeline.py or run_pipeline.sh for actual execution")
    
    return output_file

if __name__ == "__main__":
    create_demo_with_complete_output()
