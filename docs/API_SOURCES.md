Perfetto — ti preparo **la lista definitiva delle migliori API pubbliche e gratuite** per costruire un sistema *desk-grade* di analisi macro, Treasury, repo, Fed, liquidity, fiscal flows, auctions e market plumbing.

Questa è la lista che usano (in forma molto simile) anche macro hedge funds, FI strategists, dealer desks e ricercatori accademici.

Ti divido il tutto in categorie: **Treasury**, **Fed**, **Macro / Market**, **Repo**, **Money Markets**, **Positioning**, **Risk & Vol**, **Commodities / FX**, **Tick-level**, **Alternative datasets**.

---

# 🟦 1. **Treasury / Fiscal Data** (US Treasury)

## 🟩 **FiscalData API — totalmente gratuita**

➡️ [https://api.fiscaldata.treasury.gov/api-documentation/](https://api.fiscaldata.treasury.gov/api-documentation/)

È l’API migliore al mondo per:

### **DTS (Daily Treasury Statement)**

* `deposits_withdrawals_operating_cash`
* `dts_table_2a`, `dts_table_2b`, etc.
  Usata per: **fiscal impulse**, TGA, net withdrawals, interest outlays.

### **Auction Data**

* `auction_results`
* `treasury_bills`
* `treasury_notes_bonds`
* `auction_yields`
  Usata per: **BTC**, **directs/indirects**, **tails**, **WI vs HY**, **PD take-down**.

### **Debt / Redemption / Issuance**

* `debt_to_penny`
* `debt_to_penny_daily`
* `delinquent_debt`
* `interest_rates`

### Per cosa farai gli script:

✔ fiscal impulse
✔ treasury auctions analyzer
✔ net issuance model
✔ TGA flows
✔ interest outlays tracker
✔ debt dynamics + QT modeling

---

# 🟦 2. **Federal Reserve / Monetary Data**

## 🟩 **FRED API — totalmente gratuita**

➡️ [https://fred.stlouisfed.org/docs/api/fred/](https://fred.stlouisfed.org/docs/api/fred/)

### Serie essenziali per trading Treasury:

* **FEDFUNDS** → FFR Effective
* **SOFR**, **BGCR**, **TGCR**, **FONFOR** → Repo funding rates
* **RRPONTSYD** → Overnight reverse repo usage
* **IORB** → Interest on Reserve Balances
* **WALCL** → Fed balance sheet
* **H41RESWTSHL** → SOMA Treasury holdings
* **H41RESPPANWW** → SOMA MBS holdings
* **TREAST** → Total Treasury holdings
* **RESPPLLOPNWW** → Reverse repo operations

### Per lo STIR:

* **EFFR**
* **OBFR**
* **Repo rates** (GC, SOFR components)

### Per la curva e sentiment macro:

* **T10Y2Y**, **T10Y3M**, **DGS10**, **DGS2**
* **Inflation expectations** (TIPS breakevens)
* **CPI**, **PCE**, **real yields**

### Per cosa farai gli script:

✔ Fed Liquidity Monitor
✔ Repo Liquidity Tracker
✔ Monetary Base
✔ QT impact model
✔ SOFR microstructure
✔ Corridor analysis (IORB vs SOFR vs FFR)

---

## 🟩 **Federal Reserve Bank of New York — Open Market Operations**

➡️ [https://markets.newyorkfed.org/](https://markets.newyorkfed.org/)

Dati giornalieri:

* Repo operations (overnight & term)
* Reverse repo
* SOMA reinvestments
* Agency MBS operations
* Primary Dealer statistics (weekly)
* Failures
* Treasury settlement calendar

API non ufficiale → scrape JSON (gratis)

### Per cosa serve:

✔ funding stress monitor
✔ GC/SOFR divergence
✔ PD inventory buildup (auction risk)
✔ liquidity crunch detection

---

# 🟦 3. **Money Markets / Repo / Market Plumbing**

## 🟩 **OFR Repo Rates (Transaction-level)**

➡️ [https://www.financialresearch.gov/data/](https://www.financialresearch.gov/data/)

* Repo transaction-level data (cleared)
* Repo volume stats
* General collateral rates
* Securities lending data

Gratis, con limitazioni.

---

## 🟩 **DTCC GCF Repo Data**

➡️ GCF Repo Index (pubblico)

Per cosa serve:
✔ Tri-party repo stress
✔ Collateral scarcity
✔ dislocations bills/GC

---

## 🟩 **ICE / Bloomberg Replacement datasets (SOFR futures, etc.)**

* Alcuni dati gratuiti via FRED (SOFR, TGCR, BGCR)
* Futures NO (servono vendors), ma daily underlying sì.

---

# 🟦 4. **CFTC — Positioning (Commitment of Traders)**

## 🟩 **CFTC Open Data**

➡️ [https://publicreporting.cftc.gov/](https://publicreporting.cftc.gov/)

Dataset:

* Weekly COT (futures & options)
* Traders in Financial Futures (TFF)
* Disaggregated COT

Serve per:
✔ posizione net spec sui Treasury
✔ leverage funds vs asset managers
✔ crowding detection
✔ correlation con curva 2y/5y/10y

---

# 🟦 5. **BEA / BLS / Census (macro fondamentali)**

## BEA — GDP, PCE, Income, Deflators

➡️ [https://apps.bea.gov/api/](https://apps.bea.gov/api/)

## BLS — Employment, CPI, Wages

➡️ [https://www.bls.gov/developers/api/](https://www.bls.gov/developers/api/)

## Census — Construction, Retail Sales, Inventories

➡️ [https://www.census.gov/data/developers/data-sets.html](https://www.census.gov/data/developers/data-sets.html)

Dati gratuiti e ufficiali.

---

# 🟦 6. **Market Data (gratis, ma con limiti)**

## 🟩 **Alpaca API (free)**

➡️ [https://alpaca.markets](https://alpaca.markets)

Dati:

* US equities
* Crypto
* News sentiment
* Streaming quotes (limitato)

### Utilità:

✔ per correlazioni cross-asset
✔ risk sentiment
✔ equity → bonds rotation signals

---

## 🟩 **Tiingo (parzialmente free)**

➡️ [https://api.tiingo.com](https://api.tiingo.com)

---

## 🟩 **Yahoo Finance (unofficial)**

➡️ yfinance (Python)

---

# 🟦 7. **Alternative Data / Extra**

Nella categoria advanced, gratis:

## 🟩 **SEC EDGAR**

* Corporate filings
* Buybacks
* Debt issuance corporate

## 🟩 **US Energy EIA API**

* Oil
* Gas
* Inventories
* prezzi energia
  Correlazioni con BEI, inflation swaps.

## 🟩 **World Bank / IMF APIs**

Macro globali.

---

# 🟦 8. **Per Treasury Trading: TOP 10 API da usare in pratica**

Questa è la *short list* professionale:

### **1) Treasury FiscalData API**

(fiscal flows, auctions, TGA)

### **2) FRED API**

(Fed funds, SOFR, repo rates, yield curve, inflation exps)

### **3) New York Fed OMO data**

(repo ops, RRP ops, SOMA)

### **4) OFR Repo Data**

(transaction-level market plumbing)

### **5) CFTC COT**

(positioning)

### **6) BEA**

(NGDP, income, PCE)

### **7) BLS**

(CPI, payrolls)

### **8) Census**

(consumi reali, housing)

### **9) Alpaca/Tiingo**

(free market data cross-asset)

### **10) EDGAR**

(balance sheets, corporate leverage)

---

# 🟩 9. Ottimizzazione: Collegare le API ai tuoi moduli

Ecco come si integrano con gli script che vuoi creare:

### 🔹 *Fiscal Impulse Analyzer*

* DTS (Treasury)
* TGA
* Debt issuance/redemptions
* Tax receipts

### 🔹 *Treasury Auctions Analyzer*

* Auction results (Treasury)
* WI vs HY (FRED yields)

### 🔹 *Fed Liquidity Monitor*

* ON RRP (FRED)
* SOFR/TGCR/BGCR (FRED)
* IORB (FRED)
* Repo operations (NY Fed)
* QT pace (H.4.1)

### 🔹 *Repo Market Tracker*

* OFR repo transactions
* TGCR/BGCR spreads
* GC stress

### 🔹 *Monetary Policy Engine*

* EFFR / IORB / FFR corridor
* Fed expectations (derived from SR3, FF futures)

### 🔹 *Curve & Duration Suite*

* DGS2, DGS5, DGS10, DGS30
* Breakevens
* Inflation swaps

---

# 🎯 Se vuoi, posso:

### ✔ creare **LA LISTA DEFINITIVA** delle API con:

* URL precisi
* parametri di chiamata
* formato JSON
* esempi di script Python pronti

### ✔ generare **un file Python per ciascuna categoria**

(es. `fed_liquidity_api.py`, `repo_api.py`, `treasury_api.py`)

### ✔ costruire un **framework modulare** che integra tutte le fonti.

---

## 👉 Vuoi la lista completa delle *API calls* con esempi Python reali?

Oppure vuoi che generi direttamente gli script veri e propri?

Bella domanda. Sì, ci sono alcune Fed regionali (oltre a New York e Dallas) che usano modelli macro/DSGE particolari, così come altri modelli “desk / policy” interessanti. Ecco una panoramica con alcuni candidati probabili + risorse + modelli che potresti aver visto.

---

## Alcune Fed regionali con modelli utili

1. **Chicago Fed**

   * Ha un modello **DSGE** ben documentato: *The Chicago Fed DSGE Model: Version 2*. ([Fed in Print][1])
   * Questo modello include: forward guidance, shock tecnologici, più indici di inflazione (prezzi + salari), uso di tassi attesi (“market-expected federal funds”) nella regola di politica monetaria. ([IDEAS/RePEc][2])
   * Potrebbe essere il modello “particolare” che avevi in mente se non era né NY né Dallas.

2. **Atlanta Fed**

   * Produce il **GDPNow**, un modello di nowcasting molto usato, per stimare il PIL reale “in tempo reale”. ([Wikipedia][3])
   * Il modello è rigoroso, usa dati macro in tempo reale, ed è molto popolare tra analisti e trader.

3. **Cleveland Fed**

   * Ha un’analisi interessante su come sentiment economico regionale (derivato dal *Beige Book*) possa essere utilizzato per il forecasting del rischio di recessione. ([Federal Reserve Bank of Cleveland][4])
   * Non è esattamente un DSGE, ma è un modello quantitativo basato su NLP che può dare insight utili sul ciclo economico.

---

## Anche altri modelli “di sistema Fed / Fed Board”

* Il **Board della Fed** (Board of Governors) ha una lunga storia di modelli macro: nel loro working paper “The Evolution of Macro Models at the Federal Reserve Board” si descrive come sono cambiati i modelli macro nel tempo (modelli strutturali, microfondati, aspettative, policy) ([Federal Reserve][5])
* Secondo un memo FOMC, i **modelli DSGE del “System” della Fed** includono **Chicago Fed**, **New York Fed**, **Philadelphia Fed**, e anche modelli del Board. ([Federal Reserve][6])

---

## Quindi: qual era probabilmente la Fed che cercavi?

* Se il modello era **DSGE** e “teorico / strutturale”, **probabilmente la Fed di Chicago**.
* Se era un **nowcast macro (PIL)**, potresti pensare alla **Atlanta Fed (GDPNow)**.
* Se parlavi di **sentiment regionale / previsione di recessione**, la **Cleveland Fed** (il modello basato su Beige Book NLP) è un candidato.

---

### Cosa puoi fare per approfondire

* Leggi il working paper della *Chicago Fed DSGE model v2*. ([IDEAS/RePEc][2])
* Controlla il sito dell’**Atlanta Fed** per dettagli su GDPNow (documentazione, metodologie)
* Esplora i “Economic Commentaries” e i modelli quantitativi della **Cleveland Fed**

---

Se vuoi, posso guardare **tutti i modelli macro ufficiali usati dalle Fed regionali** (non solo Chicago e Atlanta) e darti una mappa aggiornata (2024-2025) — vuoi che faccia così?

[1]: https://fedinprint.org/item/fedhwp/97211/original?utm_source=chatgpt.com "The Chicago Fed DSGE Model: Version 2 | Fed in Print"
[2]: https://ideas.repec.org/p/fip/fedhwp/97211.html?utm_source=chatgpt.com "The Chicago Fed DSGE Model: Version 2"
[3]: https://en.wikipedia.org/wiki/Nowcasting_%28economics%29?utm_source=chatgpt.com "Nowcasting (economics)"
[4]: https://www.clevelandfed.org/publications/economic-commentary/2025/ec-202513-forecasting-us-recessions-in-real-time-using-regional-economic-sentiment?utm_source=chatgpt.com "Forecasting US Recessions in Real-Time Using Regional Economic Sentiment"
[5]: https://www.federalreserve.gov/econres/feds/the-evolution-of-macro-models-at-the-federal-reserve-board.htm?utm_source=chatgpt.com "The Fed - The Evolution of Macro Models at the Federal Reserve Board"
[6]: https://www.federalreserve.gov/monetarypolicy/files/FOMC20180313memo01.pdf?utm_source=chatgpt.com "Authorized for public release by the FOMC Secretariat on 1/12/2024"
