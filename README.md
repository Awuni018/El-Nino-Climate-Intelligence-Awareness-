# 🌊 El Niño Watch Ghana

**A data dashboard and advisory tool showing how El Niño affects rainfall in Ghana — and what the 2026/27 event could mean.**

> ⚠️ **Disclaimer:** This tool shows probabilities based on historical data. It is **not** an official forecast. Always follow [Ghana Meteorological Agency (GMet)](https://www.meteo.gov.gh) for official guidance.

---

## Overview

A very strong El Niño is developing for November 2026 to January 2027. NOAA confirmed El Niño conditions in June 2026, and GMet has urged national preparedness. This app helps students, the public, farmers, and local institutions understand what this means — using historical data, probabilistic risk estimation, and plain-language farmer advisories.

**Key principle (from GMet):** El Niño does *not* give uniform effects across Ghana. The tropical Atlantic also matters. This tool shows probabilities and uncertainty — never certainties.

---

## Features

| Page | Description |
|------|-------------|
| 🏠 Home | Current ENSO status, ONI gauge, forecast panel, disclaimer |
| 📜 Historical Explorer | ONI timeline 1950–present, event comparison view |
| 🌧️ Rainfall Impact | Regional anomaly charts, choropleth map of Ghana |
| 🎲 Risk Estimator | Logistic regression probability model with ONI slider |
| 🏭 Sector Impacts | Agriculture, hydropower, health, water — with FAOSTAT yields |
| 🌱 Farmer Advisory | Rule-based crop advice per region/stage, WhatsApp-shareable |
| 📖 Methods & Sources | Full transparency on data, methods, limitations, credits |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/el-nino-watch-ghana.git
cd el-nino-watch-ghana
pip install -r requirements.txt
```

### 2. Run in mock mode (default — no download needed)

```bash
streamlit run Main.py
```

The app starts in **mock mode** — all charts show clearly labelled synthetic data. This works immediately without any data download.

### 3. Load real data (optional)

```bash
# Download all data sources
python -m src.update_data --source all

# Or individually:
python -m src.update_data --source oni
python -m src.update_data --source boundaries
python -m src.update_data --source chirps    # ~GB of data, slow!
python -m src.update_data --source faostat
```

Then toggle **Mock Mode OFF** in the sidebar.

> ⚠️ CHIRPS full archive (1981–present) is large. The first run downloads GeoTIFFs and clips to Ghana — allow several hours on a slow connection.

### 4. Run tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
El-Nino/
├── Main.py                    ← Streamlit entry point (sidebar, landing page)
├── requirements.txt
├── .streamlit/
│   └── config.toml            ← Deep blue / amber theme
├── app/
│   ├── 1_Home.py              ← Current El Niño status
│   ├── 2_History.py           ← Historical ONI explorer
│   ├── 3_Rainfall_Impact.py   ← Regional rainfall anomalies + map
│   ├── 4_Risk_Estimator.py    ← Probabilistic risk model
│   ├── 5_Sectors.py           ← Sector impact cards
│   ├── 6_Farmer_Advisory.py   ← Farmer advisory generator
│   └── 7_Methods.py           ← Methods, sources, credits
├── src/
│   ├── config.py              ← All constants, URLs, toggles (edit here)
│   ├── data_loader.py         ← ONI, CHIRPS, boundaries, FAOSTAT loaders
│   ├── analysis.py            ← Event detection, anomaly calculation
│   ├── model.py               ← Logistic regression risk model
│   ├── advisory_rules.yaml    ← Farmer advice rules (editable by non-coders)
│   └── update_data.py         ← CLI data refresh script
├── data/
│   ├── raw/                   ← Downloaded raw files
│   └── processed/             ← Cached parquet/GeoJSON
└── tests/
    ├── test_oni.py
    ├── test_analysis.py
    └── test_model.py
```

---

## Data Sources

| Source | URL | Licence |
|--------|-----|---------|
| NOAA ONI | [cpc.ncep.noaa.gov](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | Public domain |
| CHIRPS v2.0 | [chc.ucsb.edu](https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/) | CC BY 3.0 |
| Ghana ADM1 | [geoboundaries.org](https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM1/) | CC BY 4.0 |
| FAOSTAT | [fao.org/faostat](https://www.fao.org/faostat/en/#data/QCL) | CC BY-NC-SA 3.0 IGO |

---

## Methods

### ENSO Event Detection
- El Niño: ONI ≥ +0.5 °C for **5 or more consecutive** overlapping 3-month seasons
- Strength: Weak (0.5–0.9), Moderate (1.0–1.4), Strong (1.5–1.9), Very Strong (≥ 2.0)
- Baseline: **1991–2020** (WMO standard period)

### Rainfall Anomaly
- Monthly CHIRPS clipped to Ghana, aggregated to 16 administrative regions
- Anomaly (%) = `(rainfall − baseline_mean) / baseline_mean × 100`
- Seasonal aggregation over season-specific months

### Risk Estimator
- **Model:** Logistic Regression (scikit-learn, L2, C=0.5)
- **Target:** P(rainfall < lowest tercile of 1991–2020 baseline)
- **Predictor:** ONI anomaly (°C) for the season's representative window
- **Validation:** Leave-One-Out cross-validation, Brier score
- **Baseline:** Historical frequency in El Niño years (for comparison)

### Farmer Advisory
- All advice in `src/advisory_rules.yaml` — editable plain text
- Structured: `crop → zone → stage → risk_level + advice + source`
- i18n stubs for Twi, Ga, Ewe, Hausa (English first)

---

## Known Limitations

1. **Small sample:** Only ~8–12 El Niño events in the CHIRPS record
2. **ONI only:** Atlantic SST (AMM) is also a key driver for Ghana — not yet in the model
3. **Synthetic data default:** Real data requires running `update_data.py`
4. **CHIRPS is estimated:** Not station observations; biases in complex terrain
5. **No sub-seasonal forecasting:** Seasonal probabilities only

---

## Deployment (Streamlit Community Cloud)

1. Push to GitHub
2. At [share.streamlit.io](https://share.streamlit.io), connect your repo
3. Set Main file: `Main.py`
4. Set secrets/environment variable: `MOCK_MODE=true` (for initial deploy)
5. For real data: add processed parquet files to the repo or use a data mount

```toml
# .streamlit/secrets.toml (do NOT commit this)
MOCK_MODE = "true"
```

---

## Configuration

Edit `src/config.py` to update:
- `FORECAST_CONFIG`: forecast panel values and "last updated" dates
- `MOCK_MODE`: default mode (overridden by `.env` or sidebar toggle)
- `CHIRPS_END_YEAR`: current year for data download range
- `GHANA_EVENTS`: add new events as they occur

---

## Nice-to-Haves (Post-MVP)

- 🗺️ Live CPC/IRI seasonal forecast overlay
- 🌐 Full Twi/Ga/Ewe/Hausa translations
- 📱 Offline PWA mode (service worker)
- 📊 Atlantic SST (AMM) as second predictor in risk model
- 🔔 Push notification when new ONI data is released
- ⚡ 16-region sub-regional CHIRPS analysis (currently zone-aggregated in some views)
- 🌾 FAOSTAT real data integration (currently mock in default mode)
- 🏗️ FastAPI endpoint for advisory rules (for integration with extension service apps)

---

## Credits

Built as an open-source, educational tool. Official sources:

- **[Ghana Meteorological Agency (GMet)](https://www.meteo.gov.gh)** — Official forecasts and advisories
- **[NOAA CPC](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/)** — ENSO outlook
- **COCOBOD/CRIG** — Cocoa management guidelines
- **CSIR, CIMMYT, AfricaRice, IFAD** — Agricultural guidelines

> This tool is for education and awareness only. It is not affiliated with or endorsed by GMet, NOAA, or any official agency.
