# Settlement Fails: A Deep Dive into Treasury Market Plumbing

This document provides a comprehensive exploration of settlement fails in U.S. Treasury markets, explaining what they are, why they occur, what they signal about market health, and how this project monitors them to assess liquidity conditions.

## 1. What are Settlement Fails and Why They Matter

In the U.S. Treasury market, trillions of dollars in securities change hands every day. When a transaction is executed, the buyer and seller agree on a price and a settlement date—typically two business days later (T+2). On the settlement date, the seller is supposed to deliver the securities, and the buyer is supposed to deliver the cash. A **settlement fail** occurs when one party fails to fulfill their obligation on the agreed-upon date.

There are two types of fails:
- **Fail to Deliver (FTD):** The seller does not deliver the securities they promised.
- **Fail to Receive (FTR):** The buyer does not receive the securities they purchased (from their perspective).

While occasional, minor fails are a normal part of market operations—arising from innocent errors, miscommunications, or minor operational glitches—a sustained or dramatic increase in settlement fails is a red flag. It indicates deeper problems in the market's infrastructure, often related to **collateral scarcity**.

### The Cost of Fails

Settlement fails are not cost-free. Under the Federal Reserve's Fails Charge Policy, a party that fails to deliver Treasury securities may be subject to financial penalties. Beyond explicit penalties, fails create operational headaches, tie up capital, and can cascade through the financial system as one party's failure to deliver creates another party's failure to receive, potentially triggering a chain reaction.

## 2. The Economic Significance of Fails

Settlement fails are far more than an operational nuisance. They are a critical barometer of stress in the deepest and most liquid market in the world.

### Collateral Scarcity

The most economically significant driver of elevated settlement fails is **collateral scarcity**. This occurs when there is intense demand for a specific Treasury security (or Treasuries in general) but insufficient supply available for immediate delivery. This can happen for several reasons:

- **Heavy Short Selling:** Hedge funds or dealers shorting a particular Treasury security need to borrow it to deliver to the buyer. If the security is in high demand (i.e., many others are also trying to short it or use it as collateral), it becomes difficult to source, leading to fails.
- **Increased Repo Demand:** During periods of tight financial conditions, the demand for high-quality collateral to use in repo transactions skyrockets. If the supply of available Treasuries cannot keep pace with this demand, settlement fails increase.
- **Central Bank or Regulatory Actions:** Central bank policies (like QE, which removes Treasuries from circulation) or regulatory changes (like Basel III, which increase banks' demand for high-quality liquid assets) can structurally reduce the available supply of Treasuries, making fails more common.

### The Link to Repo Rates

There is a direct relationship between settlement fails and repo rates. When a particular Treasury security is scarce and in high demand, participants will pay a premium to borrow it in the repo market. This premium manifests as a **special repo rate**—a rate significantly below the general collateral repo rate. The existence of elevated fails often coincides with these special rates, as market participants are unable to source the security even at a premium.

### Historical Episodes

- **2008 Financial Crisis:** During the peak of the crisis, settlement fails spiked as market participants hoarded safe-haven Treasuries and liquidity evaporated. This created severe operational strain and amplified market stress.
- **COVID-19 Pandemic (March 2020):** As investors fled to the safety of Treasuries, massive buying pressure combined with operational disruptions led to a sharp rise in fails, particularly in the most liquid on-the-run securities.
- **Recent Spikes:** Even in more "normal" times, quarter-end and year-end reporting periods often see elevated fails as banks and dealers adjust their balance sheets to meet regulatory requirements.

### Why Primary Dealer Fails Matter Most

This project focuses on **primary dealer** settlement fails because primary dealers are the core intermediaries in the Treasury market. They are the counterparties to the Federal Reserve in open market operations and the main liquidity providers to the broader market. If primary dealers are experiencing settlement fails, it is a clear sign that stress has reached the heart of the market's plumbing.

## 3. Data Structure and Methodology

Our settlement fails monitoring system taps directly into the Federal Reserve Bank of New York's Primary Dealer Statistics API, providing a comprehensive and high-frequency view of fails across the Treasury market.

### NY Fed Primary Dealer Statistics API

The NY Fed publishes weekly data on primary dealer positions, transactions, financing, and settlement fails as part of its transparency and market monitoring mandate. This data is released every Thursday, covering the activity of the prior week.

### The 22 Treasury Series

Rather than relying on a single aggregate fails number, this system fetches **22 distinct timeseries**, broken down by Treasury maturity and type:

- **Nominal Treasuries:** 2-year, 3-year, 5-year, 7-year, 10-year, 20-year, 30-year
- **Floating Rate Notes (FRNs):** 2-year FRNs
- **TIPS (Treasury Inflation-Protected Securities):** 5-year, 10-year, 30-year TIPS

For each maturity and type, the API provides two series:
- **Fails to Deliver (TD):** The value of securities that dealers failed to deliver
- **Fails to Receive (TR):** The value of securities that dealers failed to receive

### Aggregation into Total Fails

The headline metric calculated by this system is **Total Fails**, which is simply the sum of all 22 series. This provides a comprehensive measure of overall settlement stress in the Treasury market. While analyzing fails by maturity can provide granular insights (e.g., "Are fails concentrated in 10-year notes?"), the total fails metric is the most reliable high-level indicator.

### Weekly Reporting and Data Lag

It's important to understand the cadence of this data. Fails are reported weekly, typically with a one-week lag. For example, data published on Thursday, November 21, 2025, would cover the week ending Wednesday, November 13, 2025. This means the fails data is not quite real-time, but it is still significantly more timely than many other market stress indicators.

## 4. Interpreting Fails Patterns

Raw fails data requires context to be meaningful. Here's how to interpret the patterns:

### Normal Range vs. Elevated Levels

Based on historical data since 2022, **normal** total fails for primary dealers range between **$2 billion and $5 billion** per week. Fails in the **$5 billion to $10 billion** range indicate **elevated stress** and warrant close monitoring. Fails exceeding **$10 billion** are a clear sign of **severe stress** or a significant dislocation in the Treasury market.

### Seasonal Patterns

Settlement fails exhibit predictable seasonal patterns:
- **Quarter-End:** Regulatory reporting requirements drive balance sheet adjustments, often causing a temporary spike in fails.
- **Year-End:** Similar dynamics to quarter-end, but amplified. December often sees the highest fails of the year.
- **Tax Deadlines:** Major corporate or individual tax payment dates can impact Treasury market activity and, by extension, settlement patterns.

An analyst must distinguish between these expected seasonal increases and true, structural stress.

### Maturity-Specific Stress

By examining the 22 individual series, we can identify which parts of the Treasury curve are under the most stress. For example:
- High fails in 10-year notes might indicate heavy hedging activity or a specific shortage of this benchmark security.
- High fails in 2-year notes might suggest stress in the front end of the curve, often related to Fed policy expectations.
- High TIPS fails could indicate strong demand for inflation protection.

### Using Z-Scores to Detect Anomalies

The system calculates a **Z-score** for total fails, which measures how many standard deviations the current fails level is from the historical mean. A Z-score:
- **Between -1 and +1:** Normal range
- **Between +1 and +2:** Elevated, worth watching
- **Above +2:** Significantly elevated, indicating stress

This statistical approach helps cut through the noise and identify truly anomalous events.

## 5. Technical Implementation

The `nyfed_settlement_fails.py` script and the `fetch_settlement_fails()` method in `api_client.py` handle the complex task of retrieving and processing this multi-series data.

### Multiple API Endpoint Queries

The NY Fed API requires a separate query for each of the 22 timeseries. The script iterates through a predefined list of series IDs (e.g., `PDSI10F-TD` for 10-year fails to deliver, `PDSI10F-TR` for 10-year fails to receive) and fetches each one individually. This design ensures that if one series is unavailable or returns an error, the script continues and fetches the others.

### Handling Suppressed Data

To protect the confidentiality of individual primary dealers, the NY Fed sometimes suppresses data by replacing numerical values with an asterisk (`*`). The script is designed to handle these cases by converting `*` to `NaN` (Not a Number), ensuring that the analysis can proceed without crashing, while making it clear that data for that period is missing.

### Calculating Moving Averages and Z-Scores

Once the 22 series are fetched and aggregated into a total fails timeseries, the script calculates:
- **MA5 (5-period moving average):** Smooths short-term volatility
- **MA20 (20-period moving average):** Reveals the underlying trend
- **Z-Score:** Statistical measure of how unusual the current fails level is

These derived metrics are exported alongside the raw data to `outputs/fed/nyfed_settlement_fails.csv`.

## 6. Integration with the Liquidity Composite Index

Settlement fails data is not analyzed in isolation. It is a core component of the **Market Plumbing Index**, which in turn feeds into the overall **Liquidity Composite Index (LCI)**.

### Weighting in the LCI

The Market Plumbing Index represents 25% of the overall LCI. Within the Market Plumbing Index:
- **Repo Submission Ratio:** 60% weight
- **Settlement Fails:** 40% weight

This weighting reflects the fact that both repo stress and settlement fails are critical, complementary indicators of market health.

### The Combined Signal

A healthy market exhibits low repo facility usage and low settlement fails. Conversely, when both indicators are elevated simultaneously, it paints a clear picture of systemic stress. For example:
- **High repo usage + high fails:** Clear sign of liquidity crunch and collateral scarcity
- **Low repo usage + high fails:** Possible maturity-specific shortage or operational issue
- **High repo usage + low fails:** Suggests cash scarcity but adequate collateral availability

By integrating these signals, the LCI provides a nuanced, comprehensive assessment of liquidity conditions.

## 7. Running the Analysis

To fetch and analyze settlement fails data:

```bash
source venv/bin/activate
python fed/nyfed_settlement_fails.py
```

This script will:
1. Query the NY Fed API for all 22 Treasury fails series
2. Aggregate them into a total fails metric
3. Calculate moving averages and Z-scores
4. Generate a comprehensive terminal report
5. Export all data to `outputs/fed/nyfed_settlement_fails.csv`

The exported CSV integrates seamlessly with the LCI calculation pipeline.

## 8. Conclusion

Settlement fails are a powerful, yet often overlooked, indicator of Treasury market health. By monitoring primary dealer fails across all maturities and types, this system provides an early warning system for collateral scarcity, funding stress, and broader liquidity disruptions. In combination with other components of this project—fiscal flows, Fed liquidity, and repo operations—settlement fails analysis contributes to a holistic understanding of the forces shaping financial market conditions.
