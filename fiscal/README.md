# Treasury API Interface - Analisi dell'Impulso Fiscale (Desk-Grade)

Questo progetto implementa un sistema di analisi macroeconomica "Desk-Grade" per monitorare la liquidità e l'impulso fiscale degli Stati Uniti, replicando le metodologie utilizzate da Primary Dealers e Macro Hedge Funds (es. "Fiscal Week").

## Scopo del Progetto

L'obiettivo è fornire un monitoraggio ad alta frequenza (giornaliero) del **Fiscal Impulse** e della **Liquidità**, indicatori chiave per i mercati dei Treasury e per l'economia reale.

## Metodologia "Fiscal Week"

L'analisi si basa sui dati del **Daily Treasury Statement (DTS)** e integra dati macroeconomici dinamici (PIL da FRED).

### 1. Fonte Dati
- **US Treasury API**: `v1/accounting/dts/deposits_withdrawals_operating_cash` (Prelievi e Depositi).
- **US Treasury API**: `v1/accounting/dts/operating_cash_balance` (TGA Balance).
- **FRED API**: `GDP` (PIL Nominale dinamico).

### 2. Metriche Chiave (Advanced)

Lo script `fiscal/fiscal_analysis.py` calcola le seguenti metriche avanzate:

#### Fiscal Impulse & GDP
-   **Weekly Impulse % GDP**: La metrica "gold standard". Calcolata come `(MA20 * 5) / PIL Nominale`. Target di riferimento: ~0.64%.
-   **MA20 & MA5**: Media mobile a 20 giorni (trend mensile) e 5 giorni (burst settimanali).

#### Time-Based Analysis
-   **MTD (Month-to-Date)**: Cumulativo di spesa dall'inizio del mese corrente.
-   **LTD (Late-to-Date)**: Analisi degli spike di liquidità di fine mese.
-   **FYTD (Fiscal Year-to-Date)**: Cumulativo dall'inizio dell'anno fiscale (1 Ottobre).

#### Historical Context
-   **Cumulative YoY**: Differenza cumulativa rispetto allo stesso periodo dell'anno scorso.
-   **3-Year Baseline**: Confronto con la media mobile a 3 anni per filtrare le anomalie.
-   **Implied Value**: Valore atteso basato sulla stagionalità storica.

#### Liquidity & Absorption
-   **TGA Balance**: Saldo del Treasury General Account (riserva di liquidità).
-   **Household Absorption**: Quota di spesa diretta alle famiglie (Medicare, SSA, VA, Tax Refunds).
-   **Monthly Breakdown**: Analisi mensile per categoria di spesa (Interessi, Benefits, ecc.).

## Istruzioni per l'Uso

### Prerequisiti
- Python 3.x
- Virtual environment (consigliato)
- API Key FRED (opzionale, per PIL dinamico)

### Esecuzione
1.  Attivare l'ambiente virtuale:
    ```bash
    source venv/bin/activate
    ```
2.  Eseguire lo script di analisi avanzata:
    ```bash
    python fiscal/fiscal_analysis.py
    ```

Lo script scaricherà i dati storici, aggiornerà il PIL da FRED e genererà un report dettagliato a video e un file CSV (`fiscal_analysis_full.csv`).
