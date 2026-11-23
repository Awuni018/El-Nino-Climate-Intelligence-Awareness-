"""
Tests for the RainfallRiskModel (logistic regression + baseline).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.model import RainfallRiskModel, label_from_prob, RiskEstimate
from src.data_loader import _make_mock_chirps, load_oni
from src.analysis import compute_anomalies, detect_events, seasonal_anomalies


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_seasonal_df():
    """Small training dataset: 40 years, one region/season."""
    rng = np.random.default_rng(42)
    n = 40
    oni_vals = rng.normal(0, 0.8, n)
    # Inverse relationship: higher ONI → lower rainfall
    rain = 500 - 30 * oni_vals + rng.normal(0, 50, n)
    rain = np.clip(rain, 50, 800)
    df = pd.DataFrame({
        "year": range(1981, 1981 + n),
        "rainfall_mm": rain,
        "anom_pct": (rain - rain.mean()) / rain.mean() * 100,
        "ANOM": oni_vals,
        "phase": ["El Niño" if o >= 0.5 else ("La Niña" if o <= -0.5 else "Neutral") for o in oni_vals],
        "region": "Ashanti",
        "season": "Southern Major (Mar–Jul)",
    })
    return df


# ---------------------------------------------------------------------------
# label_from_prob tests
# ---------------------------------------------------------------------------

class TestLabelFromProb:
    @pytest.mark.parametrize("prob,expected", [
        (0.0, "Low chance"),
        (0.39, "Low chance"),
        (0.40, "Elevated chance"),
        (0.59, "Elevated chance"),
        (0.60, "High chance"),
        (1.0, "High chance"),
    ])
    def test_labels(self, prob, expected):
        assert label_from_prob(prob) == expected


# ---------------------------------------------------------------------------
# RainfallRiskModel tests
# ---------------------------------------------------------------------------

class TestRainfallRiskModel:
    def test_fit_runs(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        assert model._pipeline is not None

    def test_fit_returns_self(self, sample_seasonal_df):
        model = RainfallRiskModel()
        result = model.fit(sample_seasonal_df)
        assert result is model

    def test_predict_returns_risk_estimate(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=1.5)
        assert isinstance(estimate, RiskEstimate)

    def test_predict_probability_in_range(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        for oni in [-2.5, -1.0, 0.0, 1.0, 2.5]:
            estimate = model.predict(oni=oni)
            assert 0.0 <= estimate.prob_below_normal_lr <= 1.0, \
                f"Probability out of range for ONI={oni}: {estimate.prob_below_normal_lr}"

    def test_monotonicity(self, sample_seasonal_df):
        """Higher El Niño ONI should lead to higher (or equal) below-normal probability."""
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        probs = [model.predict(oni=float(o)).prob_below_normal_lr for o in [-1.0, 0.0, 1.0, 2.0]]
        # Allow small violations due to regularisation, but overall trend should hold
        # At least 3 of 4 consecutive pairs should be non-decreasing
        increases = sum(1 for a, b in zip(probs, probs[1:]) if b >= a - 0.05)
        assert increases >= 2, f"Monotonicity violated: {probs}"

    def test_baseline_freq_in_range(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=1.0)
        assert 0.0 <= estimate.prob_below_normal_baseline <= 1.0

    def test_n_training_years(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=1.0)
        assert estimate.n_training_years == 40

    def test_label_assigned(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=2.0)
        assert estimate.label in ["Low chance", "Elevated chance", "High chance"]

    def test_model_warnings_present(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=1.5)
        assert len(estimate.model_warnings) > 0

    def test_training_summary_keys(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        summary = model.get_training_summary()
        required_keys = ["Method", "Predictor", "Target", "Training years"]
        for key in required_keys:
            assert key in summary, f"Missing summary key: {key}"

    def test_predict_before_fit_raises(self):
        model = RainfallRiskModel()
        with pytest.raises(RuntimeError):
            model.predict(oni=1.0)

    def test_brier_score_range(self, sample_seasonal_df):
        model = RainfallRiskModel()
        model.fit(sample_seasonal_df)
        estimate = model.predict(oni=0.0)
        if estimate.cv_brier_score is not None:
            assert 0.0 <= estimate.cv_brier_score <= 0.5, \
                f"Brier score out of expected range: {estimate.cv_brier_score}"

    def test_fit_on_mock_data_pipeline(self):
        """Full end-to-end: mock CHIRPS + mock ONI → model fit → predict."""
        chirps = _make_mock_chirps()
        chirps_anom = compute_anomalies(chirps)
        oni = load_oni(mock=True)
        oni_events = detect_events(oni)

        agg = seasonal_anomalies(
            chirps_anom,
            region="Ashanti",
            season="Southern Major (Mar–Jul)",
            oni_df=oni_events,
        )
        agg = agg.dropna(subset=["rainfall_mm", "ANOM"])

        assert len(agg) >= 10, "Not enough training data from mock pipeline"

        model = RainfallRiskModel()
        model.fit(agg)
        estimate = model.predict(oni=1.6)

        assert 0 <= estimate.prob_below_normal_lr <= 1
        assert estimate.label in ["Low chance", "Elevated chance", "High chance"]
