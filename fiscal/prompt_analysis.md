# Richiesta di Analisi: Fiscal Impulse & Liquidity Monitor (Desk-Grade)

## Obiettivo
Generare un report giornaliero sulla liquidità e l'impulso fiscale degli Stati Uniti, replicando la metodologia "Fiscal Week" utilizzata dai Primary Dealers.

## Input Dati
1.  **Daily Treasury Statement (DTS)**:
    *   Table II: Withdrawals (Spending) & Deposits (Taxes).
    *   Table I: Operating Cash Balance (TGA).
2.  **Macro Data**:
    *   Nominal GDP (Annualized, from FRED).

## Metriche Richieste (Deterministiche)

### 1. Fiscal Impulse (Core)
*   **Total Impulse**: Somma giornaliera dei prelievi (escluso Debt Redemption).
*   **MA20 Impulse**: Media mobile a 20 giorni lavorativi.
*   **Weekly Impulse % GDP**: `(MA20 * 5) / Nominal GDP`.
    *   *Target Benchmark*: ~0.64%.

### 2. Time-Frame Analysis
*   **MTD (Month-to-Date)**: Somma cumulativa dall'inizio del mese corrente.
*   **LTD (Month-End)**: Analisi specifica degli ultimi 3 giorni lavorativi del mese.
*   **FYTD (Fiscal Year-to-Date)**: Somma cumulativa dal 1° Ottobre.

### 3. Historical Comparison
*   **YoY Delta**: Differenza rispetto allo stesso giorno dell'anno precedente (shift 252 giorni).
*   **Cumulative YoY**: Differenza tra FYTD corrente e FYTD anno precedente.
*   **3-Year Baseline**: Confronto dell'MA20 corrente con la media degli MA20 di t-1, t-2, t-3 anni.
*   **Implied Value**: Valore atteso basato sulla stagionalità storica.

### 4. Liquidity & Composition
*   **TGA Balance**: Saldo di chiusura del conto generale del Tesoro.
*   **Household Absorption**: Somma di (Medicare + SSA + VA + Unemployment + Tax Refunds).
    *   *Output*: Valore assoluto ($) e % sul totale.
*   **Monthly Breakdown**: Aggregazione mensile per categoria (Interessi, Difesa, Benefits, ecc.).

## Output Atteso
Un report testuale e tabellare che evidenzi:
1.  Il trend attuale dell'impulso fiscale (% GDP).
2.  La deviazione rispetto allo storico (Delta vs Implied, 3Y Baseline).
3.  La composizione della spesa (Household vs Corporate).
4.  Lo stato della liquidità (TGA).
