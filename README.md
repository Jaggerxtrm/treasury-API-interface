# Treasury API Interface - Desk-Grade Macro Analysis

Questo progetto implementa un sistema di analisi macroeconomica "Desk-Grade" per monitorare la liquidità, l'impulso fiscale e le operazioni della Fed, replicando le metodologie utilizzate da Primary Dealers e Macro Hedge Funds.

## Moduli Principali

### 1. Fiscal Analysis (`fiscal/fiscal_analysis.py`)
Monitora l'impulso fiscale giornaliero del governo USA.
-   **Weekly Impulse % GDP**: La metrica "gold standard" (~0.52% attuale).
-   **MTD/LTD**: Analisi dei flussi mensili e degli spike di fine mese.
-   **Household Absorption**: Quota di spesa diretta alle famiglie.
-   **TGA Balance**: Riserve di liquidità del Tesoro.

### 2. Fed Liquidity Monitor (`fed/fed_liquidity.py`)
Monitora il lato monetario e la liquidità bancaria.
-   **RRP Usage**: Drenaggio di liquidità via Reverse Repo (con analisi YoY e MTD).
-   **Repo & SRF**: Iniezioni di liquidità e tasso del backstop facility (4.00%).
-   **Rate Spreads**: SOFR vs IORB (Stress indicator).
-   **QT Pace**: Ritmo settimanale e cumulativo (YoY) di riduzione del bilancio.
-   **Inflation Expectations**: TIPS Breakevens (5Y, 10Y).
-   **Global Stress**: Swap Lines usage.

## Istruzioni per l'Uso

### Prerequisiti
- Python 3.x
- Virtual environment (consigliato)
- API Key FRED (inclusa negli script)

### Installazione
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Esecuzione
1.  **Analisi Fiscale**:
    ```bash
    python fiscal/fiscal_analysis.py
    ```
2.  **Monitoraggio Fed**:
    ```bash
    python fed/fed_liquidity.py
    ```

Gli script genereranno report a video e file CSV (`fiscal_analysis_full.csv`, `fed_liquidity_full.csv`) con lo storico completo dal 2022.
