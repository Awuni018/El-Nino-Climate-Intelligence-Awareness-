"""
El Niño Watch Ghana — Risk Estimator Model
===========================================
Logistic regression estimating P(below-normal rainfall | region, season, ONI).
"Below normal" = lowest tercile of seasonal rainfall for the baseline period.

Also includes a simple baseline model (historical frequency of below-normal
in El Niño years) for comparison.

Design constraints:
  - Small dataset (~40 training years) → regularised LR + LOO cross-validation
  - ONI is the only predictor in the MVP (Atlantic SST not yet included)
  - Model limits are communicated explicitly to users
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import brier_score_loss

from src.config import BASELINE_END, BASELINE_START, ONI_EL_NINO_THRESHOLD

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model output dataclass
# ---------------------------------------------------------------------------

@dataclass
class RiskEstimate:
    """Output of the risk estimator."""
    region: str
    season: str
    oni_input: float
    prob_below_normal_lr: float          # logistic regression
    prob_below_normal_baseline: float    # historical frequency
    label: str                           # Low / Elevated / High
    n_training_years: int
    cv_brier_score: Optional[float]
    model_warnings: list[str]


def label_from_prob(prob: float) -> str:
    """Convert probability to plain-language label."""
    if prob < 0.40:
        return "Low chance"
    if prob < 0.60:
        return "Elevated chance"
    return "High chance"


# ---------------------------------------------------------------------------
# Main model class
# ---------------------------------------------------------------------------

class RainfallRiskModel:
    """
    Logistic regression model for P(below-normal rainfall).

    Usage
    -----
    model = RainfallRiskModel()
    model.fit(seasonal_df)          # seasonal_df from analysis.seasonal_anomalies
    estimate = model.predict(oni=1.6, region="Ashanti", season="...")
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Pipeline] = None
        self._training_data: Optional[pd.DataFrame] = None
        self._tercile_threshold: Optional[float] = None
        self._n_training: int = 0
        self._cv_brier: Optional[float] = None
        self._baseline_freq: Optional[float] = None
        self._region: str = ""
        self._season: str = ""

    def fit(self, seasonal_df: pd.DataFrame) -> "RainfallRiskModel":
        """
        Fit the model from seasonal anomaly data.

        Parameters
        ----------
        seasonal_df : pd.DataFrame
            Output of analysis.seasonal_anomalies(), must include
            columns: year, rainfall_mm, ANOM (ONI anomaly).

        Returns
        -------
        self
        """
        df = seasonal_df.dropna(subset=["rainfall_mm", "ANOM"]).copy()

        # Use baseline period for tercile computation
        baseline_mask = (
            (df["year"] >= BASELINE_START) & (df["year"] <= BASELINE_END)
        )
        baseline_rain = df.loc[baseline_mask, "rainfall_mm"]
        if len(baseline_rain) < 5:
            baseline_rain = df["rainfall_mm"]  # fallback if too few baseline rows

        self._tercile_threshold = float(baseline_rain.quantile(1 / 3))

        # Binary target: 1 = below normal (lowest tercile)
        df["below_normal"] = (df["rainfall_mm"] < self._tercile_threshold).astype(int)

        X = df[["ANOM"]].values
        y = df["below_normal"].values
        self._n_training = len(df)

        # Baseline: frequency in El Niño years
        el_nino_mask = df["ANOM"] >= ONI_EL_NINO_THRESHOLD
        if el_nino_mask.sum() > 0:
            self._baseline_freq = float(df.loc[el_nino_mask, "below_normal"].mean())
        else:
            self._baseline_freq = 1 / 3  # fallback to climatological tercile

        # Fit logistic regression pipeline with L2 regularisation
        self._pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(C=0.5, max_iter=1000, random_state=42)),
        ])
        self._pipeline.fit(X, y)

        self._region = str(df["region"].iloc[0]) if "region" in df.columns else ""
        self._season = str(df["season"].iloc[0]) if "season" in df.columns else ""
        self._training_data = df

        # Leave-One-Out cross-validation for Brier score
        self._cv_brier = self._compute_loo_brier(X, y)

        logger.info(
            "RainfallRiskModel fitted: n=%d, tercile=%.1f mm, LOO Brier=%.3f",
            self._n_training,
            self._tercile_threshold,
            self._cv_brier or -1,
        )
        return self

    def _compute_loo_brier(self, X: np.ndarray, y: np.ndarray) -> Optional[float]:
        """Compute Leave-One-Out Brier score."""
        if len(y) < ONI_EL_NINO_THRESHOLD + 2:
            return None
        loo = LeaveOneOut()
        probs = []
        for train_idx, test_idx in loo.split(X):
            pipe = Pipeline([
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(C=0.5, max_iter=1000, random_state=42)),
            ])
            try:
                pipe.fit(X[train_idx], y[train_idx])
                p = pipe.predict_proba(X[test_idx])[0, 1]
            except Exception:
                p = 1 / 3
            probs.append(p)
        try:
            return float(brier_score_loss(y, probs))
        except Exception:
            return None

    def predict(self, oni: float) -> RiskEstimate:
        """
        Predict P(below-normal rainfall) for a given ONI value.

        Parameters
        ----------
        oni : float
            ONI anomaly value (°C).

        Returns
        -------
        RiskEstimate
        """
        if self._pipeline is None:
            raise RuntimeError("Model has not been fitted. Call .fit() first.")

        X_pred = np.array([[oni]])
        prob_lr = float(self._pipeline.predict_proba(X_pred)[0, 1])
        prob_base = self._baseline_freq if self._baseline_freq is not None else 1 / 3

        warnings: list[str] = []
        if self._n_training < 20:
            warnings.append(
                f"⚠️ Small sample size ({self._n_training} years). "
                "Estimates are uncertain."
            )
        warnings.append(
            "ℹ️ ONI is only one driver of Ghana rainfall. "
            "Atlantic SST and local factors also matter (GMet)."
        )
        warnings.append("ℹ️ This is not an official forecast.")

        return RiskEstimate(
            region=self._region,
            season=self._season,
            oni_input=oni,
            prob_below_normal_lr=prob_lr,
            prob_below_normal_baseline=prob_base,
            label=label_from_prob(prob_lr),
            n_training_years=self._n_training,
            cv_brier_score=self._cv_brier,
            model_warnings=warnings,
        )

    def get_training_summary(self) -> dict:
        """Return a human-readable summary of the model for the expander."""
        if self._training_data is None:
            return {}
        df = self._training_data
        return {
            "Method": "Logistic Regression (L2 regularisation, C=0.5)",
            "Predictor": "NOAA ONI anomaly (°C)",
            "Target": "P(seasonal rainfall < lowest tercile of 1991–2020 baseline)",
            "Training years": self._n_training,
            "Year range": f"{int(df['year'].min())}–{int(df['year'].max())}",
            "Tercile threshold": f"{self._tercile_threshold:.1f} mm",
            "Cross-validation": "Leave-One-Out",
            "LOO Brier score": (
                f"{self._cv_brier:.3f}" if self._cv_brier is not None else "N/A"
            ),
            "Limitations": (
                "Small sample (~40 years), ONI is not the only predictor, "
                "no Atlantic SST term, no spatial heterogeneity within region."
            ),
        }
