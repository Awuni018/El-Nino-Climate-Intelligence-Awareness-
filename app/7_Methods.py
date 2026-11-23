"""
Page 7: Methods & Sources
Data sources, methods, baseline, model description, limitations, credits.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from src.config import (
    APP_TITLE, APP_VERSION, BASELINE_END, BASELINE_START,
    CHIRPS_END_YEAR, CHIRPS_START_YEAR, GMETA_URL, MOCK_MODE, NOAA_URL,
)

st.set_page_config(
    page_title=f"Methods & Sources — {APP_TITLE}",
    page_icon="📖",
    layout="wide",
)

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .info-card {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border-left: 4px solid #F5A623; border-radius: 8px; padding: 16px 20px; margin: 8px 0;
    }
    </style>""",
    unsafe_allow_html=True,
)

st.markdown('<h1 style="color:#F5A623;">📖 Methods & Sources</h1>', unsafe_allow_html=True)
st.markdown(
    "Full transparency on data sources, methods, limitations, and credits. "
    "Always use [GMet]({}) and [NOAA]({}) for official guidance.".format(GMETA_URL, NOAA_URL)
)

st.divider()

# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------
st.markdown("## 📦 Data Sources")

sources = [
    {
        "name": "NOAA Oceanic Niño Index (ONI)",
        "url": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "description": (
            "Monthly 3-month overlapping sea surface temperature (SST) anomalies "
            "in the Niño 3.4 region (5°N–5°S, 120°–170°W), based on the "
            "1991–2020 baseline climatology. Published by NOAA Climate Prediction Center (CPC). "
            "Used to classify ENSO phases and detect events."
        ),
        "update": "Monthly",
        "licence": "Public domain (US Government)",
    },
    {
        "name": "CHIRPS v2.0 Monthly Rainfall",
        "url": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/",
        "description": (
            "Climate Hazards Group InfraRed Precipitation with Station data (CHIRPS). "
            "0.05° resolution monthly rainfall estimates for Africa, 1981–present. "
            "Clipped to Ghana bounding box (lon: –3.3 to 1.3, lat: 4.7 to 11.2) "
            "and aggregated to the 16 official administrative regions using "
            "Ghana's ADM1 boundaries. Anomalies computed against the "
            f"{BASELINE_START}–{BASELINE_END} baseline."
        ),
        "update": "Monthly (with ~6 week lag)",
        "licence": "Creative Commons Attribution 3.0",
    },
    {
        "name": "Ghana Administrative Boundaries (ADM1)",
        "url": "https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM1/",
        "description": (
            "16 official Ghana administrative region boundaries in GeoJSON format, "
            "sourced from the geoBoundaries open database. Used for the choropleth map."
        ),
        "update": "As needed (boundaries are stable)",
        "licence": "Open (CC BY 4.0)",
    },
    {
        "name": "FAOSTAT Crop Yield Data",
        "url": "https://www.fao.org/faostat/en/#data/QCL",
        "description": (
            "Ghana crop yield data (kg/ha) for cocoa, maize, cassava, and rice, "
            "sourced from the FAO FAOSTAT Production database. "
            "Used in the Sector Impacts page to show historical yield trends. "
            "In mock mode, synthetic data with plausible trends is shown."
        ),
        "update": "Annual",
        "licence": "CC BY-NC-SA 3.0 IGO",
    },
]

for src in sources:
    with st.expander(f"📄 {src['name']}"):
        st.markdown(
            f"""
            <div class="info-card">
              <div style="font-size:0.85rem; color:#A8BDD0; margin-bottom:4px;">
                Update schedule: {src['update']} · Licence: {src['licence']}
              </div>
              <div style="margin-bottom:8px;">
                <a href="{src['url']}" target="_blank" style="color:#F5A623;">{src['url']}</a>
              </div>
              <div style="color:#E8EDF2; font-size:0.9rem;">{src['description']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------
st.markdown("## 🔬 Methods")

st.markdown("### ENSO Phase Classification")
st.markdown(
    f"""
    The Oceanic Niño Index (ONI) is used to classify ENSO phases:
    - **El Niño:** ONI ≥ +0.5 °C for 5 or more consecutive overlapping 3-month seasons
    - **La Niña:** ONI ≤ –0.5 °C for 5 or more consecutive overlapping 3-month seasons
    - **Neutral:** Otherwise

    Strength categories follow NOAA CPC convention:
    | Category | ONI Range |
    |----------|-----------|
    | Weak | 0.5 – 0.9 °C |
    | Moderate | 1.0 – 1.4 °C |
    | Strong | 1.5 – 1.9 °C |
    | Very Strong | ≥ 2.0 °C |
    """
)

st.markdown("### Rainfall Anomaly Calculation")
st.markdown(
    f"""
    Monthly rainfall anomalies are computed against the **{BASELINE_START}–{BASELINE_END}
    climatological baseline** (the standard WMO baseline period):

    - **Anomaly (mm):** `rainfall_mm − baseline_mean_mm`
    - **Anomaly (%):** `(anomaly_mm / baseline_mean_mm) × 100`

    Seasonal aggregation uses simple unweighted means across the season's months.
    Region-level aggregation averages across all grid cells within each
    administrative region (via the geoBoundaries polygons).
    """
)

st.markdown("### Risk Estimator Model")
st.markdown(
    """
    **Method:** Logistic Regression (scikit-learn, L2 regularisation, C=0.5)

    **Target variable:** Binary — 1 if seasonal rainfall falls below the
    lowest tercile of the {baseline_start}–{baseline_end} baseline for that region/season
    combination ("below-normal"), 0 otherwise.

    **Predictor:** NOAA ONI anomaly (°C) for the season's representative window
    (ASO for northern season; MJJ for southern seasons).

    **Training data:** All years with both CHIRPS and ONI data available
    (approximately 1981–{chirps_end}).

    **Cross-validation:** Leave-One-Out (LOO). The Brier score (lower = better;
    perfect = 0, climatological = 0.22) is shown in the app.

    **Baseline comparison:** Historical frequency of below-normal rainfall
    specifically in El Niño years (ONI ≥ 0.5), shown alongside LR probability
    for context.

    **Known limitations:**
    - Very small sample (~40 El Niño-year seasons)
    - ONI is only one driver — tropical Atlantic SST is also important for Ghana
      (GMet highlights this explicitly)
    - No spatial heterogeneity within regions
    - No lagged predictors
    - Model fit shown to be illustrative only; not a calibrated operational forecast
    """.format(
        baseline_start=BASELINE_START,
        baseline_end=BASELINE_END,
        chirps_end=CHIRPS_END_YEAR,
    )
)

st.markdown("### Farmer Advisory Rules")
st.markdown(
    """
    All farmer advisory content is stored in `src/advisory_rules.yaml` — a plain-text
    YAML file that any extension officer can read and edit without coding knowledge.

    Rules are structured by: **crop → zone → planting stage → risk level + advice text**.

    Translation stubs for Twi (Asante), Ga, Ewe, and Hausa are scaffolded in the YAML
    with empty strings. When translations are added, they appear immediately in the app.

    All advice text is sourced from published guidelines (COCOBOD, CRIG, CIMMYT,
    AfricaRice, CSIR, MOFA Ghana, GMet, IFAD). No statistics are invented.
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Known Limitations
# ---------------------------------------------------------------------------
st.markdown("## ⚠️ Known Limitations")
st.markdown(
    """
    1. **Small El Niño sample:** Only ~8–12 El Niño events are in the CHIRPS record.
       Statistical estimates carry wide uncertainty.
    2. **ONI is not the only driver:** Ghana's rainfall is also strongly influenced
       by tropical Atlantic SST anomalies (the Atlantic Meridional Mode, AMM).
       GMet emphasises this. The Risk Estimator uses ONI only.
    3. **Regional heterogeneity:** Even within a single administrative region,
       rainfall can vary significantly. The 16-region aggregation smooths this out.
    4. **Mock data in default mode:** The app ships with mock mode ON.
       Real data requires running `python -m src.update_data` and toggling Mock Mode OFF.
    5. **CHIRPS is estimated rainfall:** CHIRPS is a satellite+station blended product,
       not station observations. It has known biases in complex terrain.
    6. **No Atlantic SST term in the model:** Future versions should include
       tropical Atlantic index as a second predictor.
    7. **No sub-seasonal forecasting:** The app shows seasonal probabilities only.
       Dry spell timing within a season is not modelled.
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Update Schedule
# ---------------------------------------------------------------------------
st.markdown("## 🔄 Update Schedule")
st.markdown(
    """
    | Data source | Update schedule | How to update |
    |-------------|-----------------|---------------|
    | NOAA ONI | Monthly | `python -m src.update_data --source oni` |
    | CHIRPS monthly | Monthly (~6 week lag) | `python -m src.update_data --source chirps` |
    | Ghana boundaries | As needed | `python -m src.update_data --source boundaries` |
    | FAOSTAT | Annual | `python -m src.update_data --source faostat` |
    | Forecast panel | Manual | Edit `FORECAST_CONFIG` in `src/config.py` |

    After running `update_data.py`, the Streamlit cache will refresh on next page load
    (or use `st.cache_data.clear()` from the terminal).
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------
st.markdown("## 🙏 Credits & Official Links")
st.markdown(
    f"""
    - **Ghana Meteorological Agency (GMet):** [meteo.gov.gh]({GMETA_URL}) — Follow for official forecasts and advisories
    - **NOAA Climate Prediction Center (CPC):** [cpc.ncep.noaa.gov]({NOAA_URL}) — Official ENSO outlook
    - **Climate Hazards Center, UCSB:** [chc.ucsb.edu](https://www.chc.ucsb.edu/) — CHIRPS data
    - **geoBoundaries:** [geoboundaries.org](https://www.geoboundaries.org/) — Ghana ADM1 boundaries
    - **FAOSTAT:** [fao.org/faostat](https://www.fao.org/faostat/) — Crop yield data
    - **COCOBOD / CRIG:** Ghana cocoa industry guidelines
    - **CSIR, CIMMYT, AfricaRice, IFAD:** Agricultural guidelines cited in advisory rules

    ---
    **App version:** {APP_VERSION}
    **Baseline period:** {BASELINE_START}–{BASELINE_END} (WMO standard)
    **Data range:** CHIRPS {CHIRPS_START_YEAR}–{CHIRPS_END_YEAR}

    > ⚠️ This tool is for education and awareness. It is NOT an official forecast.
    > Always follow GMet official bulletins for operational decisions.
    """
)
