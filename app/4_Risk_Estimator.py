"""
Page 4: Risk Estimator
Logistic regression + baseline model, ONI slider, probability gauge.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from src.config import APP_TITLE, FORECAST_CONFIG, GHANA_REGIONS, GHANA_ZONES, MOCK_MODE, SEASONS
from src.data_loader import load_oni, load_chirps
from src.analysis import compute_anomalies, detect_events, seasonal_anomalies
from src.model import RainfallRiskModel

st.set_page_config(
    page_title=f"Risk Estimator — {APP_TITLE}",
    page_icon="🎲",
    layout="wide",
)

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .mock-badge {
        background: linear-gradient(90deg, #7B2D00, #C44B00);
        color: #FFD580; border-radius: 6px; padding: 4px 10px;
        font-size: 0.75rem; font-weight: 600; display: inline-block; margin-bottom: 8px;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border: 1px solid #2A4060; border-radius: 12px; padding: 16px;
    }
    </style>""",
    unsafe_allow_html=True,
)

mock = st.session_state.get("mock_mode", MOCK_MODE)

@st.cache_data(ttl=3600, show_spinner="Loading data for risk model…")
def get_data(mock_flag: bool):
    chirps = load_chirps(mock=mock_flag)
    chirps_anom = compute_anomalies(chirps)
    oni_raw = load_oni(mock=mock_flag)
    oni_events = detect_events(oni_raw)
    return chirps_anom, oni_events

chirps_df, oni_df = get_data(mock)

st.markdown('<h1 style="color:#F5A623;">🎲 Rainfall Risk Estimator</h1>', unsafe_allow_html=True)

if mock:
    st.markdown('<div class="mock-badge">⚠️ SAMPLE DATA — not real observations</div>', unsafe_allow_html=True)

st.markdown(
    "Estimate the probability of **below-normal seasonal rainfall** "
    "(lowest tercile vs 1991–2020 baseline) for a given region, season, and ONI value. "
    "Uses logistic regression trained on historical data."
)
st.warning(
    "⚠️ **Important:** This is a probabilistic estimate based on historical patterns, "
    "not an official forecast. ONI is only one driver of Ghana rainfall — "
    "the tropical Atlantic and local factors also matter. "
    "Always follow GMet official advisories."
)

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
st.divider()
col_in1, col_in2, col_in3 = st.columns(3)

zone_options = list(GHANA_ZONES.keys())
all_region_options = zone_options + GHANA_REGIONS

with col_in1:
    region_sel = st.selectbox(
        "🗺️ Region",
        all_region_options,
        index=0,
        help="Select a zone or specific region.",
    )

with col_in2:
    season_sel = st.selectbox(
        "📅 Season",
        list(SEASONS.keys()),
        help="Agricultural season to estimate risk for.",
    )

with col_in3:
    default_oni = float(FORECAST_CONFIG["current_oni"]["value"])
    oni_input = st.slider(
        "🌡️ ONI Value (°C)",
        min_value=-3.0,
        max_value=3.0,
        value=default_oni,
        step=0.1,
        help="Set to the current or forecast ONI anomaly. Default = latest NOAA value.",
        format="%.1f °C",
    )

# ---------------------------------------------------------------------------
# Fit model on the fly
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Training risk model…")
def fit_model(mock_flag: bool, region: str, season: str):
    chirps = load_chirps(mock=mock_flag)
    chirps_anom = compute_anomalies(chirps)
    oni_raw = load_oni(mock=mock_flag)
    oni_events = detect_events(oni_raw)

    # Resolve region to list
    if region in GHANA_ZONES:
        region_list = GHANA_ZONES[region]
    else:
        region_list = [region]

    # Average across selected regions
    season_months = SEASONS[season]["months"]
    sub = chirps_anom[
        chirps_anom["region"].isin(region_list)
        & chirps_anom["month"].isin(season_months)
    ]
    agg = sub.groupby("year")[["rainfall_mm", "anom_pct"]].mean().reset_index()
    agg["region"] = region
    agg["season"] = season

    # Join ONI
    oni_seasonal = oni_events[oni_events["SEAS"] == "ASO"].rename(columns={"YR": "year"})[
        ["year", "ANOM", "phase", "in_event", "event_id", "strength"]
    ]
    agg = agg.merge(oni_seasonal, on="year", how="inner")
    agg = agg.dropna(subset=["rainfall_mm", "ANOM"])

    if len(agg) < 5:
        return None, None

    model = RainfallRiskModel()
    model.fit(agg)
    return model, agg

model, train_df = fit_model(mock, region_sel, season_sel)

st.divider()

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
if model is None:
    st.error("Not enough data to fit the model for this region/season combination. Try a different selection.")
else:
    estimate = model.predict(oni=oni_input)

    col_gauge, col_results = st.columns([1, 2])

    with col_gauge:
        prob_pct = estimate.prob_below_normal_lr * 100
        gauge_color = (
            "#DC322F" if prob_pct >= 60
            else "#F5A623" if prob_pct >= 40
            else "#2AA578"
        )

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob_pct,
            number={"suffix": "%", "font": {"size": 42, "color": "#E8EDF2"}},
            title={
                "text": "P(Below-Normal Rainfall)",
                "font": {"size": 13, "color": "#A8BDD0"},
            },
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#A8BDD0", "tickfont": {"color": "#A8BDD0"}},
                "bar": {"color": gauge_color, "thickness": 0.3},
                "bgcolor": "#1A2E45",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "#1A3B2A"},
                    {"range": [40, 60], "color": "#3B2800"},
                    {"range": [60, 100], "color": "#3B0A0A"},
                ],
                "threshold": {
                    "line": {"color": "#F5A623", "width": 3},
                    "thickness": 0.75,
                    "value": prob_pct,
                },
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=280,
            margin=dict(l=20, r=20, t=20, b=10),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_results:
        st.markdown(f"### {estimate.label}")

        label_colors = {
            "Low chance": "#2AA578",
            "Elevated chance": "#F5A623",
            "High chance": "#DC322F",
        }
        label_color = label_colors.get(estimate.label, "#F5A623")

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #1A2E45, #0D1B2A);
                border: 2px solid {label_color};
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 12px;
            ">
              <div style="font-size:1.5rem; font-weight:700; color:{label_color};">
                {estimate.label}
              </div>
              <div style="margin-top:12px; color:#E8EDF2;">
                <strong>Logistic Regression:</strong>
                <span style="color:{label_color}; font-size:1.2rem; font-weight:600;">
                  {estimate.prob_below_normal_lr:.0%}
                </span>
                probability of below-normal rainfall
              </div>
              <div style="margin-top:8px; color:#A8BDD0;">
                <strong>Historical baseline (El Niño years):</strong>
                {estimate.prob_below_normal_baseline:.0%}
              </div>
              <div style="margin-top:8px; font-size:0.8rem; color:#6C8098;">
                Region: {estimate.region} · Season: {estimate.season} · ONI: {estimate.oni_input:+.1f} °C
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Metric comparison
        m1, m2, m3 = st.columns(3)
        m1.metric("LR Probability", f"{estimate.prob_below_normal_lr:.0%}")
        m2.metric("Baseline Frequency", f"{estimate.prob_below_normal_baseline:.0%}")
        m3.metric("Training Years", estimate.n_training_years)

        # Warnings
        for w in estimate.model_warnings:
            st.caption(w)

    # Probability vs ONI curve
    st.divider()
    st.markdown("#### Probability curve vs ONI")
    oni_range = np.linspace(-2.5, 2.5, 100)
    prob_curve = [model.predict(oni=float(o)).prob_below_normal_lr for o in oni_range]

    fig_curve = go.Figure()
    fig_curve.add_trace(go.Scatter(
        x=oni_range,
        y=[p * 100 for p in prob_curve],
        mode="lines",
        name="Logistic Regression",
        line=dict(color="#F5A623", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(245, 166, 35, 0.1)",
    ))
    fig_curve.add_vline(
        x=oni_input,
        line_dash="dash",
        line_color="#FFD580",
        annotation_text=f"ONI = {oni_input:+.1f}",
        annotation_font_color="#FFD580",
    )
    fig_curve.add_hline(y=33.3, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                        annotation_text="Climatological tercile (33%)",
                        annotation_font_color="#A8BDD0")
    fig_curve.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.5)",
        height=300,
        margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(title="ONI Anomaly (°C)", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="P(below-normal) %", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)", range=[0, 100]),
        font=dict(color="#E8EDF2"),
        showlegend=False,
    )
    st.plotly_chart(fig_curve, use_container_width=True)

    # How was this calculated?
    with st.expander("🔍 How was this calculated?"):
        summary = model.get_training_summary()
        for key, val in summary.items():
            st.markdown(f"**{key}:** {val}")
        if train_df is not None and len(train_df):
            st.markdown("**Training data preview:**")
            st.dataframe(
                train_df[["year", "rainfall_mm", "ANOM", "phase"]].rename(
                    columns={"ANOM": "ONI", "rainfall_mm": "Rainfall (mm)"}
                ).head(20),
                use_container_width=True,
                hide_index=True,
            )
