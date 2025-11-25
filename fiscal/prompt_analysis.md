# Richiesta di Analisi: Fiscal Impulse & Liquidity Monitor (Desk-Grade)

## Obiettivo
Generare un report giornaliero **completo e integrato** sulla liquidità e l'impulso fiscale degli Stati Uniti, replicando la metodologia "Fiscal Week" utilizzata dai Primary Dealers e integrando i dati di liquidità Fed per un quadro macro olistico.

## Input Dati
1.  **Daily Treasury Statement (DTS)**:
    *   Table II: Withdrawals (Spending) & Deposits (Taxes).
    *   Table I: Operating Cash Balance (TGA).
2.  **Fed Liquidity Data**:
    *   Fed Balance Sheet (WALCL - Total Assets)
    *   RRP Balance (RRPONTSYD)
    *   Repo Operations (RPONTSYD)
    *   Net Liquidity = Fed Assets - RRP - TGA
3.  **Macro Data**:
    *   Nominal GDP (Annualized, from FRED).
    *   Repo spreads (SOFR-IORB, EFFR-IORB)
    *   UST yields curve

---

## Struttura del Report (OBBLIGATORIA)

Il report DEVE seguire esattamente questa struttura a 8 sezioni:

### SEZIONE 0: EXECUTIVE SUMMARY
- Apertura con sintesi di 3-5 bullet points
- Evidenziare regime monetario corrente (QT/QE/Neutral)
- Metriche chiave in formato tabella compatta:
  - Fiscal Impulse % GDP vs target 0.64%
  - Net Liquidity (valore + variazione MTD)
  - RRP Balance (valore + % MTD)
  - TGA Balance
  - Regime monetario con confidence %

**Esempio formato**:
```
EXECUTIVE SUMMARY
Key Findings:
- Fiscal Impulse: X.XX% of GDP (±XX% vs 0.64% target)
- Net Liquidity: $X.XXT (±$XXB MTD)
- RRP Balance: $XXB (±XX% MTD) - [Status: Normal/Warning/Critical]
- Monetary Regime: [QT/QE/Neutral] (XX% confidence)
```

---

### SEZIONE 1: FISCAL IMPULSE ANALYSIS (Core Metrics)

#### 1.1 Current Standing vs Target
Tabella formattata con separatori:
```
Metric                    Current      Target      Gap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Weekly Impulse % GDP      X.XX%       0.64%       ±XX%
MA20 Daily Impulse        $XXB        $XXB        ±XX%
Daily Impulse (date)      $XXB        —           —
4-Week Cumulative         $XXB        —           —
```

**Interpretation**: Paragrafo che spiega:
- Se l'impulso è above/below target e perché
- Confronto YoY (spending up/down $XXB/day)
- Contesto stagionale (es. "mid-November lull typical")

#### 1.2 Velocity & Trend
- 5-Day MA: trend (rising/declining)
- MTD Acceleration: $XXB in XX days = $XXB/day avg
- Forecast: previsione qualitativa prossimi 30 giorni

---

### SEZIONE 2: TIME-FRAME DECOMPOSITION

#### 2.1 Month-to-Date (MTD)
Tabella dettagliata per categoria:
```
Category              MTD Total    Daily Avg    vs [Prev Month] MTD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Impulse         $XXB         $XXB         [Elevated/On-trend/Low]
HHS/Medicare          $XXB         $XXB         [Status]
SSA Benefits          $XXB         $XXB         [Status]
Interest on Debt      $XXB         $XXB         [Status]
VA Benefits           $XXB         $XXB         [Status]
Unemployment          $XXB         $XXB         [Status]
```

**Household Absorption**: Calcolo e % del totale
- Includere interpretazione (es. "Below target XX% mix suggests more debt service")

#### 2.2 Fiscal Year-to-Date (FYTD)
```
Metric                    FY XXXX     FY XXXX     Delta
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FYTD Cumulative           $X,XXXB     $X,XXXB     +$XXB (+X.X%)
Annualized Pace           $X,XXXB     —           —
Days Elapsed              XX          XX          —
```

**YoY Context**: Spiegazione driver del delta (es. interest payments, transfers)
- Implicazioni per deficit FY (es. "tracking $XXB higher than FY XXXX")

#### 2.3 Quarter-to-Date (QTD)
- Fed QT Pace: annualized vs expected caps
- RRP Drawdown: $ e % change
- Net effect: QT offset calculation

---

### SEZIONE 3: HISTORICAL COMPARISON & DEVIATION ANALYSIS

#### 3.1 Year-over-Year Delta
```
Timeframe        Current    vs LY      Change    Interpretation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Daily (date)     $XXB       $XXB       +$XXB     [Elevated/Moderate/Low]
4-Week Avg       $XXB       $XXB       +$XXB     [Context]
FYTD Cum         $X,XXXB    $X,XXXB    +$XXB     [Strong/Weak] YoY
```

**Implied vs Actual**:
- Modello stagionale (LY baseline)
- Actual vs implied = beat/miss %
- Spiegazione anomalie (spike days, front-loading)

#### 3.2 3-Year Baseline Comparison
- Current MA20: $XXB
- 3Y Avg MA20: $XXB
- Deviation: +$XXB (+X.X%)

**Trend**: Driver strutturali (interest rates, mandatory spending, structural deficit)

---

### SEZIONE 4: LIQUIDITY COMPOSITION & FLOW DYNAMICS

#### 4.1 TGA (Treasury General Account) Balance
```
Date           Balance    Change     Context
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Current]      $XXXB      —          [Status]
[Previous]     $XXXB      ±$XXB WoW  [Context]
3M Average     ~$XXXB     —          [Band status]
```

**Status**: Interpretazione
- Days of spending coverage
- Cash constraint signals o pre-funding buildup
- Correlation with Net Liquidity

#### 4.2 Household Absorption Breakdown
```
Category           [Date]     % of Total   YoY Trend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SSA Benefits       $XXB       XX.X%        [Stable/Growing/Declining]
Medicare (HHS)     $XXB       XX.X%        [Trend]
VA Benefits        $XXB       XX.X%        [Trend]
Unemployment       $XXB       XX.X%        [Trend + context]
Tax Refunds        $XXB       XX.X%        [Seasonal note]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL Household    $XXB       XX.X%        —
```

**Interpretation**:
- % household-directed vs historical norms
- Labor market signals (unemployment benefits)
- Seasonal effects

#### 4.3 Monthly Category Breakdown
Top 5 categorie con % del totale:
1. **Category 1** ($XXB, XX.X%) - [note]
2. **Category 2** ($XXB, XX.X%) - [note]
...

---

### SEZIONE 5: FED LIQUIDITY & MONETARY CONDITIONS

#### 5.1 Net Liquidity Status
```
Component              Current     MTD Δ      QTD Δ      Trend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fed Assets            $X,XXXB     ±$XXB      ±$XXB      [QT/QE/Stable]
RRP Balance           $XXB        ±$XXB      ±$XXB      [Status]
TGA Balance           $XXXB       ±$XXB      ±$XXB      [Status]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NET LIQUIDITY         $X,XXXB     ±$XXB      —          [Rising/Falling]
```

**Critical Insight**: Spiegazione dinamiche (es. "Despite QT, net liquidity rising due to...")
- Breakdown dei driver (RRP, TGA, QT pace)
- 5-Day Forecast con confidence %

#### 5.2 Repo Market Stress Indicators
```
Metric                  Current    MA20      Threshold   Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOFR-IORB Spread        X.X bps    X.X bps   >10 bps     ✅/⚠️ [Status]
EFFR-IORB Spread        X.X bps    —         —           ✅/⚠️ [Status]
SOFR Volatility (5D)    [Level]    —         —           ✅/⚠️ [Status]
RRP Usage               $XXB       $XXB      <$50B       ✅/⚠️ [Critical?]
Stress Index            X/100      —         >50         ✅/⚠️ [Status]
```

**Spike Activity**:
- MTD/QTD spike counts
- Max spike value + date + context
- Current assessment

**RRP Critical Level**: Se <$50B, warning esplicito:
- Implication per reserve scarcity
- Fed policy implications (slow QT, SRF activation)

#### 5.3 Monetary Regime Confidence
- Regime: [QT/QE/Neutral] (XX% confidence)
- Signals: lista segnali (asset decline, RRP drain, ecc.)
- Pace: annualized vs policy caps

---

### SEZIONE 6: INTEGRATED LIQUIDITY VIEW

#### 6.1 Fiscal + Monetary Net Effect
Tabella dei flussi settimanali:
```
Source              Weekly Flow    Direction    Net Liquidity Impact
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fiscal Impulse      +$XXB/week     Injection    +$XXB
Tax Receipts        -$XXB/week     Drain        -$XXB
Fed QT (Assets)     -$XXB/week     Drain        -$XXB
RRP Drawdown        +$XXB/week     Injection    +$XXB
TGA Net Change      ±$XXB/week     [Direction]  ±$XXB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NET WEEKLY          —              —            ±$XXB/week
```

**Conclusion**:
- Net liquid positive/negative
- Dominance fiscale vs monetaria
- Implications per asset pricing

#### 6.2 Correlations (3-Month)
Liste di correlazioni con interpretazione:
- Net Liq vs TGA: X.XX (mechanical inverse expected)
- RRP vs SOFR Spread: X.XX (interpretation)
- Fed Assets vs Inflation Expectations: X.XX
- Net Liq vs SOFR Spread: X.XX (stress indicator)

---

### SEZIONE 7: RISK ASSESSMENT & OUTLOOK

#### 7.1 Key Risks
Lista numerata con severity:
1. **Risk Name (SEVERITY)**
   - Description
   - Threshold/trigger
   - Implication

Esempi:
- RRP Depletion Risk (CRITICAL)
- Interest Payment Spiral (ELEVATED)
- Fiscal Impulse Fade (MODERATE)
- Year-End TGA Volatility (LOW)

#### 7.2 Base Case Outlook (30 Days)
Lista bullet con forecast:
- Fiscal Impulse: direction + drivers
- Net Liquidity: expected change + range
- TGA: seasonal pattern
- Fed Policy: expected actions

#### 7.3 Tail Scenarios
**Bullish Liquidity**:
- Scenario triggers
- Impact quantification
- Net effect

**Bearish Liquidity**:
- Scenario triggers
- Impact quantification
- Risk catalysts

---

### SEZIONE 8: ACTIONABLE INTELLIGENCE

Diviso per audience:

#### For Rates Traders:
- Front-end positioning
- Curve trades
- Supply implications

#### For Equity/Credit:
- Risk-on/off implications
- Volatility catalysts
- Growth/earnings implications

#### For Macro Strategy:
- Regime characterization
- GDP/inflation impacts
- Policy implications

---

### CONCLUSION (Finale)

Paragrafo di sintesi che:
1. Caratterizza il regime corrente (es. "Stealth Easing", "QT Dominant", ecc.)
2. Sintetizza le 3 metriche chiave (net liquidity, fiscal impulse, RRP status)
3. Bottom line per market positioning
4. Next key dates da monitorare

**Formato esempio**:
```
CONCLUSION

The U.S. is in a **"[Regime Name]"** regime:
- [Key dynamic 1]
- [Key dynamic 2]
- [Key dynamic 3]

Bottom Line: [Market implication summary]

Next Key Dates:
- [Date 1]: [Event]
- [Date 2]: [Event]
```

---

## Requisiti di Formattazione

1. **Tabelle**: Usare caratteri box-drawing Unicode (━ ─ │) per separatori
2. **Status Indicators**: Usare emoji/simboli (✅ ⚠️ 🔴 ↑ ↓ →)
3. **Numeri**:
   - Miliardi: $XXB o $X,XXXB
   - Trilioni: $X.XXT
   - Percentuali: X.XX% (2 decimali)
   - Basis points: X.X bps o XX bps
4. **Dates**: YYYY-MM-DD o "Nov 25" format
5. **Emphasis**: **Bold** per metriche chiave, *italic* per note

## Tone & Style

- **Professional desk-grade**: linguaggio da trading desk/macro research
- **Quantitativo ma interpretato**: non solo numeri, ma "so what?"
- **Actionable**: ogni sezione deve concludere con implication pratica
- **Integrated**: connettere fiscal e monetary, non silos separati

---

## Checklist Pre-Pubblicazione

Prima di finalizzare il report, verificare:
- [ ] Tutte le 8 sezioni sono presenti e complete
- [ ] Executive Summary cattura i 3-5 key findings
- [ ] Ogni tabella ha interpretation paragraph
- [ ] Sezione 6 integra fiscal + Fed data
- [ ] Sezione 7 ha risk assessment con severity levels
- [ ] Sezione 8 ha actionable intelligence per 3 audiences
- [ ] Conclusion ha regime characterization + next key dates
- [ ] Formattazione consistente (tabelle, simboli, numeri)
- [ ] Nessun dato mancante o "N/A" senza spiegazione
