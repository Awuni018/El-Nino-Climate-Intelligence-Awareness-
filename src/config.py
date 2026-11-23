"""
El Niño Watch Ghana — Central Configuration
All constants, paths, toggles, and thresholds live here.
Edit this file (or .env) to update data sources, baselines, or mock mode.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
SRC_DIR = ROOT_DIR / "src"
APP_DIR = ROOT_DIR / "app"

DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Mock Mode
# ---------------------------------------------------------------------------
# Set MOCK_MODE=False in .env to enable real data download
MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() not in {"false", "0", "no"}

# ---------------------------------------------------------------------------
# Data Source URLs
# ---------------------------------------------------------------------------
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

CHIRPS_BASE_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
)

GEOBOUNDARIES_GHA_ADM1_URL = (
    "https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM1/"
)

FAOSTAT_CROPS_URL = (
    "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
)

# ---------------------------------------------------------------------------
# Ghana Bounding Box (lon_min, lat_min, lon_max, lat_max)
# ---------------------------------------------------------------------------
GHANA_BBOX = (-3.3, 4.7, 1.3, 11.2)

# ---------------------------------------------------------------------------
# Climate Baseline Period
# ---------------------------------------------------------------------------
BASELINE_START = 1991
BASELINE_END = 2020

# ---------------------------------------------------------------------------
# CHIRPS Data Range
# ---------------------------------------------------------------------------
CHIRPS_START_YEAR = 1981
CHIRPS_END_YEAR = 2025  # update annually

# ---------------------------------------------------------------------------
# ONI Thresholds & Event Classification
# ---------------------------------------------------------------------------
ONI_EL_NINO_THRESHOLD = 0.5
ONI_LA_NINA_THRESHOLD = -0.5
ONI_CONSECUTIVE_SEASONS = 5  # number of overlapping seasons required

ONI_STRENGTH: dict[str, tuple[float, float]] = {
    "Weak": (0.5, 0.9),
    "Moderate": (1.0, 1.4),
    "Strong": (1.5, 1.9),
    "Very Strong": (2.0, float("inf")),
}

# ---------------------------------------------------------------------------
# Named Ghana El Niño Events (for annotation)
# ---------------------------------------------------------------------------
GHANA_EVENTS: list[dict] = [
    {
        "label": "1982/83 (Strong)",
        "start_year": 1982,
        "end_year": 1983,
        "peak_oni": 2.1,
        "notes": "Severe drought in northern Ghana, crop failures",
    },
    {
        "label": "1997/98 (Very Strong)",
        "start_year": 1997,
        "end_year": 1998,
        "peak_oni": 2.4,
        "notes": "Major rainfall deficit, Volta River low, hydropower crisis",
    },
    {
        "label": "2015/16 (Strong)",
        "start_year": 2015,
        "end_year": 2016,
        "peak_oni": 2.3,
        "notes": "Electricity rationing (dumsor), cocoa yield decline",
    },
    {
        "label": "2023/24 (Moderate)",
        "start_year": 2023,
        "end_year": 2024,
        "peak_oni": 1.9,
        "notes": "Below-normal rains in southern Ghana, food security concerns",
    },
    {
        "label": "2026/27 (Forecast: Very Strong)",
        "start_year": 2026,
        "end_year": 2027,
        "peak_oni": None,  # forecast, not yet realised
        "notes": "NOAA confirmed El Niño conditions June 2026; GMet urges preparedness",
    },
]

# ---------------------------------------------------------------------------
# Geographic Zones (3-zone aggregation; 16-region detail via GeoJSON)
# ---------------------------------------------------------------------------
GHANA_ZONES: dict[str, list[str]] = {
    "Coastal/South": [
        "Greater Accra",
        "Central",
        "Western",
        "Western North",
        "Volta",
        "Oti",
    ],
    "Forest/Middle Belt": [
        "Eastern",
        "Ashanti",
        "Bono",
        "Bono East",
        "Ahafo",
    ],
    "Northern": [
        "Northern",
        "North East",
        "Savannah",
        "Upper East",
        "Upper West",
    ],
}

GHANA_REGIONS: list[str] = [r for zone in GHANA_ZONES.values() for r in zone]

# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------
SEASONS: dict[str, dict] = {
    "Southern Major (Mar–Jul)": {
        "months": [3, 4, 5, 6, 7],
        "zones": ["Coastal/South", "Forest/Middle Belt"],
        "description": "Main agricultural season for southern Ghana",
    },
    "Southern Minor (Sep–Nov)": {
        "months": [9, 10, 11],
        "zones": ["Coastal/South", "Forest/Middle Belt"],
        "description": "Second rainy season in the south",
    },
    "Northern Season (May–Oct)": {
        "months": [5, 6, 7, 8, 9, 10],
        "zones": ["Northern"],
        "description": "Single rainy season for northern Ghana",
    },
}

# ---------------------------------------------------------------------------
# Forecast Panel Config (editable; source-cited)
# ---------------------------------------------------------------------------
FORECAST_CONFIG: dict[str, dict] = {
    "noaa_oni_probability": {
        "label": "NOAA probability of Very Strong event (NDJ 2026/27)",
        "value": 0.65,  # 65 % — update as NOAA releases new outlooks
        "source": "NOAA CPC",
        "last_updated": "2026-10-01",
        "unit": "probability",
    },
    "gmet_outlook_summary": {
        "label": "GMet seasonal outlook summary",
        "value": (
            "Hotter and drier dry season expected; below-normal rainfall "
            "likely in many areas for the rest of 2026, particularly in "
            "northern and central Ghana. El Niño effects compound existing "
            "heat stress. Official guidance available at GMet website."
        ),
        "source": "Ghana Meteorological Agency (GMet)",
        "last_updated": "2026-09-15",
        "unit": "text",
    },
    "current_oni": {
        "label": "Latest NOAA ONI value",
        "value": 1.6,  # will be overwritten by live ONI loader
        "source": "NOAA CPC",
        "last_updated": "2026-10-01",
        "unit": "°C",
    },
}

# ---------------------------------------------------------------------------
# App Metadata
# ---------------------------------------------------------------------------
APP_TITLE = "El Niño Watch Ghana"
APP_SUBTITLE = "Understanding El Niño impacts on Ghana's rainfall and livelihoods"
APP_VERSION = "0.1.0-MVP"
APP_DISCLAIMER = (
    "⚠️ **Disclaimer:** This tool shows probabilities based on historical data and "
    "past events. It is **not** an official forecast. Always follow "
    "[Ghana Meteorological Agency (GMet)](https://www.meteo.gov.gh) "
    "for official guidance."
)
GMETA_URL = "https://www.meteo.gov.gh"
NOAA_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/"
