"""
Tests for rainfall anomaly computation and seasonal aggregation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.data_loader import _make_mock_chirps
from src.analysis import compute_anomalies, seasonal_anomalies
from src.config import BASELINE_END, BASELINE_START, SEASONS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_chirps():
    """Small synthetic CHIRPS DataFrame for fast tests."""
    rng = np.random.default_rng(1234)
    rows = []
    regions = ["Greater Accra", "Ashanti", "Northern"]
    for yr in range(BASELINE_START - 5, BASELINE_END + 5):
        for month in range(1, 13):
            for region in regions:
                base = 80.0 + 40.0 * np.sin(np.pi * (month - 4) / 6)
                rain = base + rng.normal(0, 15)
                rows.append({
                    "year": yr,
                    "month": month,
                    "region": region,
                    "rainfall_mm": max(0.0, rain),
                    "anom_pct": 0.0,
                    "is_mock": True,
                    "mock_badge": "test",
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# compute_anomalies tests
# ---------------------------------------------------------------------------

class TestComputeAnomalies:
    def test_output_has_required_columns(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        for col in ["baseline_mm", "anom_mm", "anom_pct", "season_label"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_baseline_mean_in_baseline_period(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        # For baseline period, mean anomaly should be near 0
        bl_mask = (result["year"] >= BASELINE_START) & (result["year"] <= BASELINE_END)
        mean_anom = result.loc[bl_mask, "anom_pct"].mean()
        assert abs(mean_anom) < 5.0, f"Mean anomaly in baseline period too large: {mean_anom:.2f}%"

    def test_no_negative_rainfall_in_baseline(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        assert (result["rainfall_mm"] >= 0).all()

    def test_anom_pct_calculation(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        # For a row where baseline_mm > 0:
        sub = result[(result["baseline_mm"] > 0)].iloc[0]
        expected_pct = (sub["anom_mm"] / sub["baseline_mm"]) * 100
        assert abs(sub["anom_pct"] - expected_pct) < 1e-6

    def test_season_labels_assigned(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        # March should be Southern Major
        march_rows = result[result["month"] == 3]
        assert (march_rows["season_label"] == "Southern Major (Mar–Jul)").all()

        # October should be Southern Minor
        oct_rows = result[result["month"] == 10]
        assert (oct_rows["season_label"] == "Southern Minor (Sep–Nov)").all()

    def test_all_regions_present(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        assert set(result["region"].unique()) == {"Greater Accra", "Ashanti", "Northern"}

    def test_no_nan_in_baseline_period(self, mock_chirps):
        result = compute_anomalies(mock_chirps)
        bl = result[(result["year"] >= BASELINE_START) & (result["year"] <= BASELINE_END)]
        # anom_mm should not be NaN in baseline period
        assert not bl["anom_mm"].isna().any()

    def test_custom_baseline_period(self, mock_chirps):
        result = compute_anomalies(mock_chirps, baseline_start=1995, baseline_end=2000)
        bl_mask = (result["year"] >= 1995) & (result["year"] <= 2000)
        mean_anom = result.loc[bl_mask, "anom_pct"].mean()
        assert abs(mean_anom) < 5.0

    def test_mock_chirps_full_shape(self):
        """Full mock CHIRPS from data_loader should have expected dimensions."""
        df = _make_mock_chirps()
        # 45 years × 12 months × 16 regions
        from src.config import CHIRPS_END_YEAR, CHIRPS_START_YEAR, GHANA_REGIONS
        expected_rows = (CHIRPS_END_YEAR - CHIRPS_START_YEAR + 1) * 12 * len(GHANA_REGIONS)
        assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"


# ---------------------------------------------------------------------------
# seasonal_anomalies tests
# ---------------------------------------------------------------------------

class TestSeasonalAnomalies:
    def test_output_shape(self, mock_chirps):
        result_anom = compute_anomalies(mock_chirps)
        agg = seasonal_anomalies(result_anom, region="Ashanti", season="Southern Major (Mar–Jul)")
        assert len(agg) > 0
        assert "rainfall_mm" in agg.columns
        assert "region" in agg.columns
        assert "season" in agg.columns

    def test_one_row_per_year(self, mock_chirps):
        result_anom = compute_anomalies(mock_chirps)
        agg = seasonal_anomalies(result_anom, region="Ashanti", season="Southern Major (Mar–Jul)")
        assert len(agg) == agg["year"].nunique()

    def test_region_label_correct(self, mock_chirps):
        result_anom = compute_anomalies(mock_chirps)
        agg = seasonal_anomalies(result_anom, region="Northern", season="Northern Season (May–Oct)")
        assert (agg["region"] == "Northern").all()

    def test_season_months_filtered(self, mock_chirps):
        """Verify only the correct months are included in the season aggregation."""
        result_anom = compute_anomalies(mock_chirps)
        # We can verify indirectly: mean rainfall should differ between seasons
        agg_south = seasonal_anomalies(result_anom, "Ashanti", "Southern Major (Mar–Jul)")
        agg_minor = seasonal_anomalies(result_anom, "Ashanti", "Southern Minor (Sep–Nov)")
        # They shouldn't be identical
        assert not np.allclose(
            agg_south["rainfall_mm"].values,
            agg_minor.set_index("year").reindex(agg_south["year"])["rainfall_mm"].values,
            equal_nan=True,
        )
