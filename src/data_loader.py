"""
El Niño Watch Ghana — Data Loaders
===================================
Provides loaders for:
  - NOAA Oceanic Niño Index (ONI)
  - CHIRPS v2 monthly rainfall (clipped to Ghana)
  - Ghana administrative boundaries (GeoJSON)
  - FAOSTAT crop yields (optional)

Each loader has a MOCK_MODE fallback that returns clearly labelled synthetic
data, so the app works end-to-end before real data is connected.

All loaders are designed to be called with @st.cache_data where possible.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

from src.config import (
    CHIRPS_END_YEAR,
    CHIRPS_START_YEAR,
    DATA_PROCESSED,
    DATA_RAW,
    GHANA_BBOX,
    GHANA_REGIONS,
    GEOBOUNDARIES_GHA_ADM1_URL,
    MOCK_MODE,
    ONI_URL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_BADGE = "⚠️ Sample data — not real observations"

REQUEST_TIMEOUT = 20  # seconds


def _safe_get(url: str, **kwargs) -> Optional[requests.Response]:
    """HTTP GET with timeout and error handling; returns None on failure."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        logger.warning("HTTP request failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# ONI Loader
# ---------------------------------------------------------------------------

ONI_COLUMNS = ["SEAS", "YR", "TOTAL", "ANOM"]


def _make_mock_oni() -> pd.DataFrame:
    """
    Generate synthetic ONI data (1950–2027) for mock mode.
    Uses a realistic-looking sinusoidal pattern plus noise.
    Clearly labelled as synthetic.
    """
    rng = np.random.default_rng(42)
    seasons_3letter = [
        "DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
        "JJA", "JAS", "ASO", "SON", "OND", "NDJ",
    ]
    rows = []
    for yr in range(1950, 2028):
        for month_idx, seas in enumerate(seasons_3letter):
            # Plausible ENSO-like signal
            t = (yr - 1950) * 12 + month_idx
            signal = (
                0.6 * np.sin(2 * np.pi * t / 48)      # ~4-year ENSO cycle
                + 0.3 * np.sin(2 * np.pi * t / 84)    # ~7-year modulation
                + rng.normal(0, 0.25)
            )
            # Hard-code approximate peaks for the named Ghana events
            if yr == 1983 and month_idx in range(0, 4):
                signal = max(signal, 2.0 + rng.normal(0, 0.1))
            elif yr == 1998 and month_idx in range(0, 3):
                signal = max(signal, 2.3 + rng.normal(0, 0.1))
            elif yr == 2016 and month_idx in range(0, 3):
                signal = max(signal, 2.2 + rng.normal(0, 0.1))
            elif yr == 2024 and month_idx in range(0, 4):
                signal = max(signal, 1.5 + rng.normal(0, 0.1))
            elif yr == 2026 and month_idx >= 6:
                signal = 1.6 + rng.normal(0, 0.1)  # current developing event
            elif yr == 2027 and month_idx < 3:
                signal = 1.8 + rng.normal(0, 0.1)
            rows.append(
                {
                    "SEAS": seas,
                    "YR": yr,
                    "TOTAL": round(float(signal + 27.0), 2),  # fake SST total
                    "ANOM": round(float(signal), 2),
                    "is_mock": True,
                }
            )
    df = pd.DataFrame(rows)
    df["mock_badge"] = MOCK_BADGE
    return df


def _parse_oni_text(text: str) -> pd.DataFrame:
    """
    Parse NOAA ONI ASCII text file into a DataFrame.

    Expected format (space-separated):
        SEAS  YR  TOTAL  ANOM
        DJF  1950  26.6  -0.5
        ...
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Find the header line
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.startswith("SEAS")
    )
    rows = []
    for ln in lines[header_idx + 1:]:
        parts = ln.split()
        if len(parts) >= 4:
            try:
                rows.append(
                    {
                        "SEAS": parts[0],
                        "YR": int(parts[1]),
                        "TOTAL": float(parts[2]),
                        "ANOM": float(parts[3]),
                        "is_mock": False,
                    }
                )
            except ValueError:
                continue
    df = pd.DataFrame(rows, columns=["SEAS", "YR", "TOTAL", "ANOM", "is_mock"])
    df["mock_badge"] = ""
    return df


def load_oni(mock: bool = MOCK_MODE) -> pd.DataFrame:
    """
    Load NOAA Oceanic Niño Index data.

    Parameters
    ----------
    mock : bool
        If True, return synthetic data with 'is_mock=True' column.

    Returns
    -------
    pd.DataFrame
        Columns: SEAS, YR, TOTAL, ANOM, is_mock, mock_badge
        SEAS is the 3-letter overlapping season (e.g. 'DJF').
        ANOM is the SST anomaly (°C) relative to 1991–2020 baseline.
    """
    cache_path = DATA_PROCESSED / "oni.parquet"

    if mock:
        logger.info("ONI: mock mode — returning synthetic data")
        return _make_mock_oni()

    # Try cache first
    if cache_path.exists():
        logger.info("ONI: loading from cache %s", cache_path)
        return pd.read_parquet(cache_path)

    # Fetch from NOAA
    logger.info("ONI: fetching from %s", ONI_URL)
    resp = _safe_get(ONI_URL)
    if resp is None:
        logger.warning("ONI: fetch failed — falling back to mock data")
        df = _make_mock_oni()
        df["mock_badge"] = "⚠️ NOAA fetch failed — showing synthetic data"
        return df

    df = _parse_oni_text(resp.text)
    df.to_parquet(cache_path, index=False)
    logger.info("ONI: saved %d rows to cache", len(df))
    return df


# ---------------------------------------------------------------------------
# Ghana Boundaries Loader
# ---------------------------------------------------------------------------

def _make_mock_boundaries() -> dict:
    """
    Return a minimal GeoJSON FeatureCollection with 3 zone polygons
    (not the real 16-region shapes) for mock/fallback mode.
    """
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"shapeName": "Coastal/South", "is_mock": True},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-3.3, 4.7], [1.3, 4.7], [1.3, 7.0],
                        [-3.3, 7.0], [-3.3, 4.7],
                    ]],
                },
            },
            {
                "type": "Feature",
                "properties": {"shapeName": "Forest/Middle Belt", "is_mock": True},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-3.3, 7.0], [1.3, 7.0], [1.3, 9.0],
                        [-3.3, 9.0], [-3.3, 7.0],
                    ]],
                },
            },
            {
                "type": "Feature",
                "properties": {"shapeName": "Northern", "is_mock": True},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-3.3, 9.0], [1.3, 9.0], [1.3, 11.2],
                        [-3.3, 11.2], [-3.3, 9.0],
                    ]],
                },
            },
        ],
    }


def load_ghana_boundaries(mock: bool = MOCK_MODE) -> dict:
    """
    Load Ghana ADM1 boundaries as a GeoJSON FeatureCollection.

    Parameters
    ----------
    mock : bool
        If True, return 3-zone simplified mock polygons.

    Returns
    -------
    dict
        GeoJSON FeatureCollection.
    """
    cache_path = DATA_PROCESSED / "ghana_adm1.geojson"

    if mock:
        logger.info("Boundaries: mock mode — returning 3-zone polygons")
        return _make_mock_boundaries()

    if cache_path.exists():
        import json
        return json.loads(cache_path.read_text(encoding="utf-8"))

    logger.info("Boundaries: fetching from geoBoundaries API")
    resp = _safe_get(GEOBOUNDARIES_GHA_ADM1_URL)
    if resp is None:
        logger.warning("Boundaries: fetch failed — using mock polygons")
        return _make_mock_boundaries()

    meta = resp.json()
    geojson_url = meta.get("gjDownloadURL", "")
    if not geojson_url:
        logger.warning("Boundaries: no gjDownloadURL in response — using mock")
        return _make_mock_boundaries()

    resp2 = _safe_get(geojson_url)
    if resp2 is None:
        return _make_mock_boundaries()

    import json
    geojson = resp2.json()
    cache_path.write_text(json.dumps(geojson), encoding="utf-8")
    return geojson


# ---------------------------------------------------------------------------
# CHIRPS Loader
# ---------------------------------------------------------------------------

def _make_mock_chirps() -> pd.DataFrame:
    """
    Generate synthetic monthly rainfall anomalies for all 16 Ghana regions
    covering 1981–2025 for mock mode.
    """
    rng = np.random.default_rng(99)
    rows = []
    for yr in range(CHIRPS_START_YEAR, CHIRPS_END_YEAR + 1):
        for month in range(1, 13):
            for region in GHANA_REGIONS:
                # Base climatology (mm/month) varies by region/month
                base = 80 + 60 * np.sin(np.pi * (month - 4) / 6)
                if "Northern" in region or "Upper" in region or "Savannah" in region:
                    base *= 0.85
                elif "Coastal" in region or "Greater Accra" in region:
                    base *= 0.75
                anom_pct = rng.normal(0, 15)  # % anomaly
                # Add El Niño signal in known event years
                if yr in {1983, 1998, 2016, 2024, 2026, 2027}:
                    anom_pct -= rng.uniform(10, 25)
                rainfall_mm = base * (1 + anom_pct / 100)
                rows.append(
                    {
                        "year": yr,
                        "month": month,
                        "region": region,
                        "rainfall_mm": max(0.0, round(float(rainfall_mm), 1)),
                        "anom_pct": round(float(anom_pct), 1),
                        "is_mock": True,
                    }
                )
    df = pd.DataFrame(rows)
    df["mock_badge"] = MOCK_BADGE
    return df


def load_chirps(mock: bool = MOCK_MODE) -> pd.DataFrame:
    """
    Load CHIRPS v2 monthly rainfall data clipped to Ghana.

    In real mode, downloads GeoTIFFs from CHC UCSB, clips to Ghana bbox,
    and aggregates by region. This is slow (~GB of data); cache is used
    after the first run.

    Parameters
    ----------
    mock : bool
        If True, return synthetic monthly rainfall DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: year, month, region, rainfall_mm, anom_pct, is_mock, mock_badge
    """
    cache_path = DATA_PROCESSED / "chirps_ghana.parquet"

    if mock:
        logger.info("CHIRPS: mock mode — returning synthetic data")
        return _make_mock_chirps()

    if cache_path.exists():
        logger.info("CHIRPS: loading from parquet cache")
        return pd.read_parquet(cache_path)

    logger.info(
        "CHIRPS: real download mode — this will take several minutes "
        "for the full 1981–%d archive. Consider running "
        "'python -m src.update_data' first.",
        CHIRPS_END_YEAR,
    )
    # Real download is handled by src/update_data.py which downloads
    # GeoTIFFs, clips to Ghana, and writes the parquet cache.
    # At runtime, fall back to mock if cache doesn't exist yet.
    logger.warning("CHIRPS: cache not found — falling back to mock data")
    df = _make_mock_chirps()
    df["mock_badge"] = "⚠️ CHIRPS cache not found — run 'python -m src.update_data' first. Showing synthetic data."
    return df


# ---------------------------------------------------------------------------
# FAOSTAT Crop Yields Loader
# ---------------------------------------------------------------------------

FAOSTAT_CROPS = ["Cocoa beans", "Maize", "Cassava", "Rice, paddy"]
FAOSTAT_ITEM_CODES = {
    "Cocoa beans": 661,
    "Maize": 56,
    "Cassava": 125,
    "Rice, paddy": 27,
}


def _make_mock_faostat() -> pd.DataFrame:
    """Return synthetic Ghana crop yield data 1961–2023."""
    rng = np.random.default_rng(7)
    rows = []
    base_yields = {
        "Cocoa beans": 350,    # kg/ha
        "Maize": 1700,
        "Cassava": 14000,
        "Rice, paddy": 2500,
    }
    for yr in range(1961, 2024):
        for crop, base in base_yields.items():
            trend = 1 + (yr - 1961) * 0.008  # slow yield improvement
            el_nino_shock = -0.08 if yr in {1983, 1998, 2016, 2024} else 0.0
            yield_val = base * trend * (1 + el_nino_shock + rng.normal(0, 0.05))
            rows.append(
                {
                    "year": yr,
                    "crop": crop,
                    "yield_kg_ha": round(max(0.0, yield_val), 0),
                    "country": "Ghana",
                    "is_mock": True,
                }
            )
    df = pd.DataFrame(rows)
    df["mock_badge"] = MOCK_BADGE
    return df


def load_faostat(mock: bool = MOCK_MODE) -> pd.DataFrame:
    """
    Load FAOSTAT crop yield data for Ghana.

    Parameters
    ----------
    mock : bool
        If True, return synthetic yield DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: year, crop, yield_kg_ha, country, is_mock, mock_badge
    """
    cache_path = DATA_PROCESSED / "faostat_ghana.parquet"

    if mock:
        return _make_mock_faostat()

    if cache_path.exists():
        return pd.read_parquet(cache_path)

    # Real FAOSTAT download (zip file, large) — handled by update_data.py
    logger.warning("FAOSTAT: cache not found — falling back to mock data")
    df = _make_mock_faostat()
    df["mock_badge"] = "⚠️ FAOSTAT cache missing — run update_data.py. Showing synthetic data."
    return df
