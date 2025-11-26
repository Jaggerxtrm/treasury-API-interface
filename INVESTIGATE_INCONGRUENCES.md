# INVESTIGATE_INCONGRUENCES.md
**Obiettivo:** indagare e correggere tutte le incongruenze, i bug numerici e le ambiguità riportate nel "TREASURY LIQUIDITY DESK REPORT" (Report Date: 2025-11-26) in modo che il prodotto finale sia desk-grade e riproducibile.

---

## 1) Problemi da investigare (priorità alta)
Per ogni voce: descrizione problema, come riprodurlo, dove guardare nel repo, ipotesi causa e test/patch suggeriti.

---

### 1.1 Household Share negativa (-45.7%) mentre Household Impulse è positiva ($7,121M)
- **Descrizione:** il report riporta `Household Impulse: 7,121M` ma `Household Share: -45.7%`. Una percentuale negativa è logicamente inconsistente con un valore positivo.
- **Come riprodurre:** eseguire lo script `fiscal/fiscal_analysis.py` con lo stesso input e stampare:
  - `total_spending`, `total_taxes`, `net_impulse`, `household_impulse`, `household_share`
- **Dove controllare nel repo:**
  - `fiscal/fiscal_analysis.py` (calcolo household, funzione `compute_household_share` o simili)
  - eventuale `config` o `category_map` che definisce cosa appartiene a "household"
- **Ipotesi cause:**
  - divisione sbagliata: `household_impulse / net_impulse` usata invece di `household_outlays / total_outlays`, o viceversa
  - segno errato applicato altrove (es. `net_impulse` negativo e share = household / net)
  - data-type bug (negativi convertiti male)
- **Test suggeriti:**
  - ricalcolare `household_share = household_outlays / total_outlays` e `household_net_share = household_net / net_impulse` e confrontare.
  - stampare sample rows per debug (raw descriptions + mapped category amounts).
- **Fix proposto:**
  - definire esplicitamente in codice la formula desiderata (documentare in README), e applicare solo quella.
  - aggiungere assert: `-1 <= household_share <= 1` (o `0 <= household_share <= 1` se usiamo outlays).
- **Output atteso dopo fix:** `household_share` in [0%,100%] se calcolato su outlays; se percentuale su net_impulse, gestire segno e documentarlo.

---

### 1.2 Net Liquidity mismatch (diff ~314M)
- **Descrizione:** Net Liquidity calcolata (5,646,422M) non corrisponde esattamente a `FedAssets - RRP - TGA` (≈ 5,646,736M). Delta ≈ 314M.
- **Riproduzione:** eseguire script che calcola Net Liquidity e confrontare componenti:
  - `fed_assets`, `rrp_balance`, `tga_balance`, `other_adjustments` (se presenti)
- **Dove guardare:**
  - `fed/fed_liquidity.py` o `fed/liquidity_composite_index.py` (calcolo net liquidity)
  - funzioni che aggregano H.4.1 + DTS (attenzione a unità: M vs B)
- **Ipotesi cause:**
  - arrotondamenti diversi (es. arrotondo prima di sommare)
  - elementi aggiuntivi (es. SOMA Treasury holdings usati, o MBS esclusi)
  - errori di unità (milioni vs migliaia)
  - uso di MA/rolling smoothing prima di sottrarre
- **Test suggeriti:**
  - log grezzo con 1) raw fed assets, 2) raw rrp, 3) raw tga, 4) net_calc = fed - rrp - tga; assert(net_calc == reported_net ± tol)
  - definire `tol = 1_000_000` (1M) o adeguare in base all'unità (milioni).
- **Fix proposto:**
  - standardizzare le unità (tutto in Millions USD) in ingest pipeline.
  - esplicitare eventuali "other adjustments" con nome e commento nel CSV di output.
  - aggiungere test unitario di riconciliazione.

---

### 1.3 Definizione e calcolo di "Weekly Impulse % GDP" vs target 0.64%
- **Descrizione:** Non è chiaro se 0.19% è weekly, annualized, o MA20-based; il target 0.64% proviene da Fiscal Week ma va riconciliato alla definizione usata.
- **Riproduzione:** verificare come è calcolato `weekly_impulse_pct_gdp` in script (file: `fiscal/fiscal_analysis.py`).
- **Dove guardare:**
  - funzione che calcola `*_pct_gdp`, `NOMINAL_GDP` config
- **Ipotesi cause:**
  - confusione fra:
    - `MA20 * 252 / GDP` (annualized)
    - `(weekly_impulse) / (GDP/52)` (simple weekly)
    - `(ma_4w * 252) / GDP` (4-week average annualized)
- **Test suggeriti:**
  - calcolare tutte le varianti e stampare: `daily_pct`, `weekly_pct`, `ma20_pct`, `ma4w_annualized_pct` per confronto.
- **Fix proposto:**
  - stabilire e documentare la formula (consiglio: usare `ma4w_annualized_pct_gdp = ma_4w * 252 / GDP` per confronto con Fiscal Week).
  - includere entrambe le metriche nel report: `Weekly %GDP (weekly)` e `Annualized %GDP (ma4w annualized)`.

---

### 1.4 RRP % MTD e calcolo delle percentuali
- **Descrizione:** Percentuale MTD (-90.3%) non coerente con i delta numerici stampati (-21B MTD). Il calcolo percentuale dovrebbe essere `(delta / start_of_month_value)`.
- **Riproduzione:** log MTD start, end RRP; ricomputare `% = delta / start`.
- **Dove guardare:** `fed/fed_liquidity.py`, routine MTD
- **Ipotesi cause:**
  - uso di denominatore sbagliato (end anziché start)
  - unità mismatch (B vs M)
- **Test suggeriti:**
  - print `rrp_start_month`, `rrp_end_month`, `delta`, `%calc = delta/rrp_start_month`
  - assert denominatori non zero prima di dividere
- **Fix proposto:** usare start-of-period come denominatore; se start ~0 gestire con fallback (abs delta).

---

### 1.5 Disallineamento fra "Weekly %GDP" e "Net weekly liquidity -69.4B"
- **Descrizione:** numeri non coerenti tra loro: la %GDP della componente fiscale e il valore netto di drain settimanale non dialogano chiaro.
- **Azione:** ricostruire la tabella di contabilità settimanale completa:
  - voci: fiscal_spending, fiscal_taxes, net_impulse, tga_change, rrp_change, fed_assets_change, other_ops → somma = net_liquidity_change
- **Dove guardare:** `fiscal/*` + `fed/*` scripts, composizione integrata in `fed/liquidity_composite_index.py`
- **Test:**
  - generare reconciled weekly table; assert `net_liq_change ≈ tga_change + fiscal_net_change + fed_ops_change + rrp_change`
- **Fix:** documentare la contabilità e usala per popolare la sezione Integrated View.

---

### 1.6 NaN in "RRP Drawdown +nanB/week"
- **Descrizione:** appare `+nanB/week` nella tabella integrated view.
- **Causa probabile:** divisione per zero o valore mancante in data pipeline (es. historic baseline missing).
- **Dove guardare:** funzione che calcola `rpp_flow_weekly` o `rpp_weekly_change`.
- **Test:** isna checks su RRP series; sostituire NA con 0 o impute (ma loggare)
- **Fix proposto:** gestire NaN con fallback e stampare avviso: `if pd.isna(val): val = 0; log('RRP weekly nan -> set 0')`.

---

## 2) Migliorie e suggerimenti tecnici (priorità media/alta)
Queste non sono bug, ma miglioramenti necessari per robustezza e trasparenza.

### 2.1 Standardizzare unità e naming
- Forzare *Millions USD* come unità interna.
- Ingest pipeline: convertire tutte le series (FRED, DTS, H4.1) a Millions con metadati.
- Aggiornare CSV headers con `unit=M` o `unit=USD_million`.

### 2.2 Audit trail & logging
- Ogni export CSV deve includere:
  - `generation_timestamp`, `data_sources` (endpoint + last_fetch), `NOMINAL_GDP_used`, `week_definition = 'WED-WED'`.
- Log dettagliato per ogni trasformazione critica (e.g., category mapping hits/misses).

### 2.3 Tests automatici e regressione
- Unit tests:
  - `test_household_share_bounds`
  - `test_net_liquidity_reconciliation` (tolerance configurable)
  - `test_pct_gdp_definitions` (compare formulas)
- Include snapshot tests con sample data (month-end and shutdown scenarios).

### 2.4 Category mapping QA
- Stampare top-20 descriptions mappati ad `Other`. Se `Other` > 25% total_spending, creare ticket per riclassificazione.
- Suggerimento: regex map su keywords: `INTEREST`, `MEDICARE`, `SOCIAL SECURITY`, `VA`, `REFUND`, `PAYROLL`.

### 2.5 Documentare tutte le formule
- Ogni metrica nel report deve avere nota con formula esatta (es. `%GDP_ma20 = ma20 * 252 / NOMINAL_GDP`).

---

## 3) Test/Checklist che l'agente deve eseguire (con snippet)
Esegui questi comandi / snippet (pandas) durante l'investigazione:

```python
# 1. Recompute household share candidate formulas
df = pd.read_csv('outputs/fiscal/fiscal_analysis_full.csv', parse_dates=['record_date']).set_index('record_date')
total_outlays = df['total_spending']
household_outlays = df['household_outlays']  # o 'household_impulse' raw
net_impulse = df['net_impulse']

# two definitions
share_a = household_outlays / total_outlays
share_b = household_outlays / net_impulse

print(share_a.tail())
print(share_b.tail())

# 2. Recompute net liquidity raw
fed_assets = get_fed_assets()  # ingest function
rrp = get_rrp()
tga = get_tga()
net_calc = fed_assets - rrp - tga
print(net_calc.tail())
print(df[['net_liquidity_reported','net_calc']].tail())

# 3. Recompute pct_gdp variants
GDP = 31_700_000  # Millions USD
ma20 = df['ma20']
ma4w = df['ma4w']
weekly_impulse = df['weekly_net_impulse']

print("ma20_pct_gdp", (ma20*252)/GDP)
print("ma4w_annualized_pct_gdp", (ma4w*252)/GDP)
print("weekly_pct_gdp", weekly_impulse/(GDP/52))
```

---

## 4) Documentare risultati e produrre deliverable

L'agente deve produrre **un PR report** contenente:

1. Lista dei bug corretti (file/linea/commit suggerito).
2. Patch o diff `.patch` / `.diff` pronto da applicare.
3. Nuovi unit tests aggiunti.
4. Report reconciliation aggiornato (CSV + breve nota).
5. Verifica numerica: tabella "before / after" con i numeri chiave (Net Liquidity, RRP%, Household share, Weekly %GDP, cum4w) per una data di esempio (2025-11-26).

---

## 5) Soglie / tolleranze consigliate

* **Net liquidity reconcil. tolerance:** 0.05% o 5M (in Millions) — whichever larger.
* **cum4w vs sum4weeks block delta tolerance:** 1% o 10,000M (10B) — log warning above.
* **RRP percent change:** calcolare su denominatore start-of-period; se start < 1B usa absolute threshold.
* **Household share bounds:** if computing on outlays: 0–100%; if on net: allow negative but document.

---

## 6) Reporting finale richiesto dall'agente

Quando hai finito, fornisci:

1. `INVESTIGATION_RESULT.md` con breve executive summary (1–2 pagine).
2. Patch `.diff` e comando `git apply` da eseguire.
3. Output CSV aggiornati (`fiscal_analysis_full.csv`, `fiscal_analysis_weekly.csv`, `fed_liquidity_full.csv`).
4. Un file `TESTS.md` che elenca tutti i test eseguiti e i loro risultati.

---

## 7) Contatti e permessi

* Usa la branch `investigate/incongruences_<yourname>` e apri un PR verso `main` con descrizione dettagliata.
* In PR: includi screenshot delle tabelle before/after e i risultati dei test.

---

### NOTE FINALI (priorità)

* Risolvi prima **Household Share** e **NaN RRP** (critici).
* Poi allinea le metriche %GDP e Net Liquidity.
* Infine aggiungi test e documentazione.

Se servono sample raw CSV (DTS / H4.1 / FRED extracts) da usare per i test, chiedi e te li fornisco.

Grazie — lavorare su questi punti porterà il report a livello desk-grade e risolverà le incongruenze numeriche critiche.
