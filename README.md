# Treasury API Interface - Analisi dell'Impulso Fiscale

Questo progetto mira a replicare sistematicamente le metodologie di analisi macroeconomica presentate in documenti accademici e newsletter finanziarie (es. "Fiscal week #44"), utilizzando i dati ufficiali forniti dall'API del Dipartimento del Tesoro degli Stati Uniti.

## Scopo del Progetto

L'obiettivo principale è monitorare il **Fiscal Impulse** (Impulso Fiscale), ovvero l'iniezione netta di liquidità nell'economia da parte del governo federale USA. Questo indicatore è fondamentale per comprendere le dinamiche di liquidità che influenzano i mercati finanziari e l'economia reale.

## Metodologia

L'analisi si basa sui dati del **Daily Treasury Statement (DTS)**, che offre una visione giornaliera delle disponibilità liquide e delle operazioni di debito del Tesoro.

### 1. Fonte Dati
Utilizziamo l'endpoint pubblico `v1/accounting/dts/deposits_withdrawals_operating_cash` dell'API Fiscal Data del Tesoro USA.
- **URL Base**: `https://api.fiscaldata.treasury.gov/services/api/fiscal_service`
- **Endpoint**: `/v1/accounting/dts/deposits_withdrawals_operating_cash`

### 2. Filtraggio e Pulizia
Per calcolare correttamente l'impulso fiscale, è necessario isolare la spesa reale dalle operazioni di gestione del debito.
- **Filtro Iniziale**: Si considerano solo le transazioni di tipo `Withdrawals` (Prelievi).
- **Esclusioni**: Vengono rimosse le categorie relative al rimborso del debito pubblico (es. "Public Debt Cash Redemp. (Table IIIB)") e i subtotali ("Sub-Total Withdrawals"), che gonfierebbero artificialmente i dati di spesa.

### 3. Metriche Calcolate
Lo script di analisi (`fiscal/fiscal_impulse.py`) calcola le seguenti metriche:
- **Total Impulse (Giornaliero)**: La somma giornaliera dei prelievi netti (escluso il rimborso del debito).
- **Media Mobile a 20 Giorni (MA_20)**: Una media mobile semplice su 20 giorni lavorativi (circa un mese di calendario) per smussare la volatilità giornaliera e identificare il trend sottostante.
- **Variazione Anno su Anno (YoY Change)**: La differenza tra l'impulso fiscale del giorno corrente e quello dello stesso giorno dell'anno precedente, per evidenziare l'accelerazione o la decelerazione della spesa.

## Istruzioni per l'Uso

### Prerequisiti
- Python 3.x
- Virtual environment (consigliato)

### Esecuzione
1.  Attivare l'ambiente virtuale:
    ```bash
    source venv/bin/activate
    ```
2.  Eseguire lo script di analisi:
    ```bash
    python fiscal/fiscal_impulse.py
    ```

Lo script scaricherà i dati storici (dal 2022 ad oggi) e mostrerà a video le metriche più recenti.
