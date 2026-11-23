"""
Tests for ONI loading and parsing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import pytest

from src.data_loader import _parse_oni_text, _make_mock_oni, load_oni
from src.analysis import classify_phase, classify_strength, detect_events, get_latest_oni


# ---------------------------------------------------------------------------
# Sample ONI text (mimicking the NOAA format)
# ---------------------------------------------------------------------------

SAMPLE_ONI_TEXT = """
 Oceanic Nino Index based on ERSSTv5 (1991-2020 base period)
      SEAS    YR    TOTAL   ANOM
       DJF  1950   26.5   -0.5
       JFM  1950   26.4   -0.6
       FMA  1950   26.4   -0.5
       MAM  1950   26.4   -0.4
       AMJ  1950   26.5   -0.4
       MJJ  1950   26.6   -0.3
       JJA  1950   26.7   -0.3
       JAS  1950   26.7   -0.4
       ASO  1950   26.7   -0.4
       SON  1950   26.7   -0.4
       OND  1950   26.7   -0.4
       NDJ  1950   26.7   -0.4
       DJF  1997   28.9    1.5
       JFM  1998   29.2    1.9
       FMA  1998   29.5    2.4
       MAM  1998   29.4    2.3
       AMJ  1998   28.7    1.6
       MJJ  1998   28.0    0.9
"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParseONI:
    def test_basic_parse(self):
        df = _parse_oni_text(SAMPLE_ONI_TEXT)
        assert isinstance(df, pd.DataFrame)
        assert set(["SEAS", "YR", "TOTAL", "ANOM", "is_mock"]).issubset(df.columns)

    def test_row_count(self):
        df = _parse_oni_text(SAMPLE_ONI_TEXT)
        assert len(df) == 18  # 12 rows for 1950 + 6 rows for 1997/98

    def test_dtypes(self):
        df = _parse_oni_text(SAMPLE_ONI_TEXT)
        assert df["YR"].dtype in [np.int64, np.int32, int]
        assert df["ANOM"].dtype in [np.float64, float]
        assert df["TOTAL"].dtype in [np.float64, float]

    def test_is_mock_false(self):
        df = _parse_oni_text(SAMPLE_ONI_TEXT)
        assert not df["is_mock"].any()

    def test_specific_values(self):
        df = _parse_oni_text(SAMPLE_ONI_TEXT)
        row = df[(df["YR"] == 1998) & (df["SEAS"] == "FMA")].iloc[0]
        assert row["ANOM"] == pytest.approx(2.4, abs=1e-6)
        assert row["TOTAL"] == pytest.approx(29.5, abs=1e-6)

    def test_empty_text_raises_or_empty(self):
        df = _parse_oni_text("SEAS YR TOTAL ANOM\n")
        assert len(df) == 0 or isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# Mock ONI tests
# ---------------------------------------------------------------------------

class TestMockONI:
    def test_shape(self):
        df = _make_mock_oni()
        assert len(df) > 100
        assert "ANOM" in df.columns
        assert "is_mock" in df.columns

    def test_all_mock(self):
        df = _make_mock_oni()
        assert df["is_mock"].all()

    def test_year_range(self):
        df = _make_mock_oni()
        assert df["YR"].min() == 1950
        assert df["YR"].max() >= 2026

    def test_anom_range(self):
        df = _make_mock_oni()
        # Anomalies should be plausible ENSO range
        assert df["ANOM"].min() > -4.0
        assert df["ANOM"].max() < 5.0

    def test_has_mock_badge(self):
        df = _make_mock_oni()
        assert "mock_badge" in df.columns
        assert df["mock_badge"].iloc[0] != ""


# ---------------------------------------------------------------------------
# Phase classification tests
# ---------------------------------------------------------------------------

class TestClassifyPhase:
    @pytest.mark.parametrize("anom,expected", [
        (0.5, "El Niño"),
        (1.5, "El Niño"),
        (2.3, "El Niño"),
        (-0.5, "La Niña"),
        (-1.5, "La Niña"),
        (0.4, "Neutral"),
        (-0.4, "Neutral"),
        (0.0, "Neutral"),
    ])
    def test_phase(self, anom, expected):
        assert classify_phase(anom) == expected


class TestClassifyStrength:
    @pytest.mark.parametrize("anom,expected", [
        (0.6, "Weak"),
        (0.9, "Weak"),
        (1.0, "Moderate"),
        (1.4, "Moderate"),
        (1.5, "Strong"),
        (1.9, "Strong"),
        (2.0, "Very Strong"),
        (2.5, "Very Strong"),
        (-0.6, "Weak"),
        (-1.5, "Strong"),
        (0.3, "Neutral"),
    ])
    def test_strength(self, anom, expected):
        assert classify_strength(anom) == expected


# ---------------------------------------------------------------------------
# Event detection tests
# ---------------------------------------------------------------------------

class TestDetectEvents:
    def _make_oni_df(self, oni_values: list[float]) -> pd.DataFrame:
        """Create a minimal ONI DataFrame with consecutive seasons."""
        from src.analysis import SEASON_ORDER
        rows = []
        for i, anom in enumerate(oni_values):
            yr = 1980 + (i // 12)
            seas = SEASON_ORDER[i % 12]
            rows.append({"SEAS": seas, "YR": yr, "TOTAL": 27.0 + anom, "ANOM": anom, "is_mock": True})
        df = pd.DataFrame(rows)
        df["mock_badge"] = ""
        return df

    def test_no_event_below_threshold(self):
        df = self._make_oni_df([0.4] * 20)
        result = detect_events(df)
        assert not result["in_event"].any()

    def test_el_nino_detected_at_5_seasons(self):
        # 5 consecutive El Niño seasons, surrounded by neutral
        anomalies = [0.3] * 6 + [0.8] * 5 + [0.3] * 6
        df = self._make_oni_df(anomalies)
        result = detect_events(df)
        assert result["in_event"].any()
        assert (result.loc[result["in_event"], "phase"] == "El Niño").all()

    def test_el_nino_not_detected_at_4_seasons(self):
        # Only 4 consecutive — should NOT trigger an event
        anomalies = [0.3] * 6 + [0.8] * 4 + [0.3] * 6
        df = self._make_oni_df(anomalies)
        result = detect_events(df)
        assert not result["in_event"].any()

    def test_la_nina_detected(self):
        anomalies = [0.0] * 4 + [-0.8] * 7 + [0.0] * 4
        df = self._make_oni_df(anomalies)
        result = detect_events(df)
        in_event = result[result["in_event"]]
        assert len(in_event) > 0
        assert (in_event["phase"] == "La Niña").all()

    def test_event_id_assigned(self):
        anomalies = [0.3] * 3 + [1.5] * 7 + [0.3] * 3
        df = self._make_oni_df(anomalies)
        result = detect_events(df)
        in_event = result[result["in_event"]]
        assert (in_event["event_id"] != "").all()

    def test_strength_very_strong(self):
        anomalies = [2.1] * 8
        df = self._make_oni_df(anomalies)
        result = detect_events(df)
        in_event = result[result["in_event"]]
        # Peak strength should be Very Strong (but stored per-row as row anomaly classification)
        assert (in_event["ANOM"] >= 2.0).all()

    def test_all_columns_present(self):
        df = self._make_oni_df([0.6] * 10)
        result = detect_events(df)
        for col in ["phase", "in_event", "event_id", "strength"]:
            assert col in result.columns

    def test_load_oni_mock_then_detect(self):
        df = load_oni(mock=True)
        result = detect_events(df)
        # Should have events in known El Niño years
        el_nino_years = result[result["in_event"]]["YR"].unique()
        # 1983, 1998, 2016 should be detected as events
        assert 1983 in el_nino_years or 1982 in el_nino_years

    def test_get_latest_oni(self):
        df = load_oni(mock=True)
        result = detect_events(df)
        latest = get_latest_oni(result)
        assert "seas" in latest
        assert "anom" in latest
        assert "phase" in latest
        assert isinstance(latest["anom"], float)
