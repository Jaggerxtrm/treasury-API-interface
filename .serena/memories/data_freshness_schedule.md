# Data Freshness & Publication Schedules

## Standard Lags
- **Fiscal Data (DTS):** Published T+1 business day at 4:00 PM.
- **Reference Rates (SOFR, etc.):** Published T+1 business day at 8:00 AM.
- **Repo Operations:** Published Same Day (T).
- **Settlement Fails:** Published with ~2 week lag (mid-month and end-month).

## Holiday Impacts (Example: Thanksgiving)
- **Thanksgiving (Thursday):** Market Holiday. No data.
- **Wednesday Data:**
  - Repo Ops: Available Wednesday.
  - Reference Rates: Available Friday 8:00 AM (delayed by holiday).
  - Fiscal Data: Available Friday 4:00 PM (delayed by holiday).

## Current Status (as of Nov 28, 7:17 AM)
- **Repo Ops:** Up to Nov 26 (Wed) - Correct.
- **Reference Rates:** Up to Nov 25 (Tue) - Correct (Nov 26 releases at 8 AM today).
- **Fiscal Data:** Up to Nov 25 (Tue) - Correct (Nov 26 releases at 4 PM today).
