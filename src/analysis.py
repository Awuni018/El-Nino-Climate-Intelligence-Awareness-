"""
El Niño Watch Ghana — Analysis Module
=======================================
Functions for:
  - ONI event detection (5-consecutive-season rule)
  - Strength categorisation
  - Rainfall anomaly calculation vs 1991–2020 baseline
  - Phase/season classification helpers
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    BASELINE_END,
    BASELINE_START,
    GHANA_ZONES,
    ONI_CONSECUTIVE_SEASONS,
    ONI_EL_NINO_THRESHOLD,
    ONI_LA_NINA_THRESHOLD,
    ONI_STRENGTH,
    SEASONS,
)

logger = logging.getLogger(__name__)

# Ordered list of overlapping 3-month seasons
SEASON_ORDER = [
    "DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
    "JJA", "JAS", "ASO", "SON", "OND", "NDJ",
]


# ---------------------------------------------------------------------------
# ONI Helpers
# ---------------------------------------------------------------------------

def classify_phase(anom: float) -> str:
    """Return 'El Niño', 'La Niña', or 'Neutral' for a given ONI anomaly."""
    if anom >= ONI_EL_NINO_THRESHOLD:
        return "El Niño"
    if anom <= ONI_LA_NINA_THRESHOLD:
        return "La Niña"
    return "Neutral"


def classify_strength(anom: float) -> str:
    """Return ONI strength category string for El Niño / La Niña values."""
    abs_anom = abs(anom)
    for label, (lo, hi) in ONI_STRENGTH.items():
        if lo <= abs_anom <= hi:
            return label
    if abs_anom < 0.5:
        return "Neutral"
    return "Very Strong"  # fallback for > 2.0 caught by last range


def detect_events(oni_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect El Niño and La Niña events using the 5-consecutive-season rule.

    An event is defined as ONI at or above (El Niño) / at or below (La Niña)
    the threshold for at least 5 consecutive overlapping 3-month seasons.

    Parameters
    ----------
    oni_df : pd.DataFrame
        Output of load_oni(). Must have columns: SEAS, YR, ANOM.

    Returns
    -------
    pd.DataFrame
        Input df with additional columns:
          - phase: 'El Niño' | 'La Niña' | 'Neutral'
          - in_event: bool (True if part of a declared ENSO event)
          - event_id: str label for the event (or empty string)
          - strength: 'Weak' | 'Moderate' | 'Strong' | 'Very Strong' | 'Neutral'
    """
    df = oni_df.copy().sort_values(["YR", "SEAS"]).reset_index(drop=True)

    # Build a sortable numeric index for each season row
    season_num = {s: i for i, s in enumerate(SEASON_ORDER)}
    df["_season_num"] = df["SEAS"].map(season_num)
    df["_abs_index"] = df["YR"] * 12 + df["_season_num"]

    # Classify phase per row
    df["phase"] = df["ANOM"].apply(classify_phase)
    df["strength"] = df["ANOM"].apply(classify_strength)

    # Detect consecutive runs for El Niño
    df["in_event"] = False
    df["event_id"] = ""

    for phase_name, threshold, sign in [
        ("El Niño", ONI_EL_NINO_THRESHOLD, 1),
        ("La Niña", ONI_LA_NINA_THRESHOLD, -1),
    ]:
        mask = (df["phase"] == phase_name)
        idx = df.index[mask].tolist()

        # Find runs of consecutive rows (by _abs_index) of length >= 5
        if not idx:
            continue

        runs: list[list[int]] = []
        current_run = [idx[0]]
        for i in range(1, len(idx)):
            prev_abs = df.at[idx[i - 1], "_abs_index"]
            curr_abs = df.at[idx[i], "_abs_index"]
            if curr_abs == prev_abs + 1:
                current_run.append(idx[i])
            else:
                runs.append(current_run)
                current_run = [idx[i]]
        runs.append(current_run)

        for run in runs:
            if len(run) >= ONI_CONSECUTIVE_SEASONS:
                start_yr = int(df.at[run[0], "YR"])
                end_yr = int(df.at[run[-1], "YR"])
                peak_anom = df.loc[run, "ANOM"].apply(abs).max()
                strength = classify_strength(peak_anom * sign)
                label = (
                    f"{phase_name} {start_yr}"
                    if start_yr == end_yr
                    else f"{phase_name} {start_yr}/{str(end_yr)[-2:]}"
                )
                df.loc[run, "in_event"] = True
                df.loc[run, "event_id"] = label

    df.drop(columns=["_season_num", "_abs_index"], inplace=True)
    return df


def get_latest_oni(oni_df: pd.DataFrame) -> dict:
    """
    Return a dict with the latest ONI row's season, year, anomaly, phase,
    and strength.
    """
    latest = oni_df.iloc[-1]
    return {
        "seas": latest["SEAS"],
        "year": int(latest["YR"]),
        "anom": float(latest["ANOM"]),
        "phase": classify_phase(float(latest["ANOM"])),
        "strength": classify_strength(float(latest["ANOM"])),
        "is_mock": bool(latest.get("is_mock", False)),
    }


# ---------------------------------------------------------------------------
# Rainfall Anomaly Calculation
# ---------------------------------------------------------------------------

def compute_anomalies(
    chirps_df: pd.DataFrame,
    baseline_start: int = BASELINE_START,
    baseline_end: int = BASELINE_END,
) -> pd.DataFrame:
    """
    Compute rainfall anomalies (% of normal and mm deviation) against
    the 1991–2020 climatological baseline.

    Parameters
    ----------
    chirps_df : pd.DataFrame
        Output of load_chirps(). Must have columns: year, month, region, rainfall_mm.
    baseline_start : int
        Start year of the climatological baseline (default 1991).
    baseline_end : int
        End year of the climatological baseline (default 2020).

    Returns
    -------
    pd.DataFrame
        Input df plus:
          - baseline_mm: mean rainfall for the baseline period (by region+month)
          - anom_mm: anomaly in mm (rainfall_mm - baseline_mm)
          - anom_pct: anomaly as % of baseline (may differ from input anom_pct)
          - season_label: which season label this month falls into
    """
    df = chirps_df.copy()

    # Compute climatological baseline
    baseline_mask = (df["year"] >= baseline_start) & (df["year"] <= baseline_end)
    baseline = (
        df[baseline_mask]
        .groupby(["region", "month"])["rainfall_mm"]
        .mean()
        .rename("baseline_mm")
        .reset_index()
    )

    df = df.merge(baseline, on=["region", "month"], how="left")
    df["anom_mm"] = df["rainfall_mm"] - df["baseline_mm"]
    df["anom_pct"] = np.where(
        df["baseline_mm"] > 0,
        (df["anom_mm"] / df["baseline_mm"]) * 100,
        np.nan,
    )

    # Tag season
    def _tag_season(month: int) -> str:
        if month in [3, 4, 5, 6, 7]:
            return "Southern Major (Mar–Jul)"
        if month in [9, 10, 11]:
            return "Southern Minor (Sep–Nov)"
        if month in [5, 6, 7, 8, 9, 10]:
            return "Northern Season (May–Oct)"
        return "Other"

    df["season_label"] = df["month"].apply(_tag_season)
    return df


def seasonal_anomalies(
    chirps_df: pd.DataFrame,
    region: str,
    season: str,
    oni_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Aggregate monthly anomalies to seasonal averages for a single region/season.
    Optionally joins ONI event metadata.

    Parameters
    ----------
    chirps_df : pd.DataFrame
        Anomaly-enhanced CHIRPS data (output of compute_anomalies).
    region : str
        One of the 16 official region names or a zone name.
    season : str
        One of the SEASONS keys.
    oni_df : pd.DataFrame, optional
        ONI data with event detection columns (for joining).

    Returns
    -------
    pd.DataFrame
        Columns: year, region, season, rainfall_mm, anom_pct, anom_mm,
        and optionally: phase, in_event, event_id
    """
    season_months = SEASONS[season]["months"]

    if region in GHANA_ZONES:
        region_list = GHANA_ZONES[region]
        mask = (
            chirps_df["region"].isin(region_list)
            & chirps_df["month"].isin(season_months)
        )
    else:
        mask = (
            (chirps_df["region"] == region)
            & chirps_df["month"].isin(season_months)
        )

    sub = chirps_df[mask].copy()
    agg = (
        sub.groupby("year")[["rainfall_mm", "anom_mm", "anom_pct"]]
        .mean()
        .reset_index()
    )
    agg["region"] = region
    agg["season"] = season

    # Join ONI event metadata (by dominant season year)
    if oni_df is not None and "in_event" in oni_df.columns:
        # Use ASO/SON window to represent ENSO state during the season
        enso_window_seas = "ASO" if "Northern" in season else "MJJ"
        oni_annual = (
            oni_df[oni_df["SEAS"] == enso_window_seas]
            .rename(columns={"YR": "year"})
            [["year", "ANOM", "phase", "in_event", "event_id", "strength"]]
        )
        agg = agg.merge(oni_annual, on="year", how="left")

    return agg


def get_zone_for_region(region: str) -> str:
    """Return the zone name for a given region."""
    for zone, regions in GHANA_ZONES.items():
        if region in regions:
            return zone
    return "Unknown"
