"""
Page 1: Current El Niño Status
Headline card, ONI value, forecast panel, plain-language summary, disclaimer.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.config import (
    APP_DISCLAIMER, APP_TITLE, FORECAST_CONFIG,
    GHANA_EVENTS, GMETA_URL, MOCK_MODE, NOAA_URL,
)
from src.data_loader import load_oni
from src.analysis import detect_events, get_latest_oni

st.set_page_config(
    page_title=f"Current Status — {APP_TITLE}",
    page_icon="📊",
    layout="wide",
)

# Global CSS (re-inject for multipage)
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border: 1px solid #2A4060; border-radius: 12px; padding: 16px;
    }
    .mock-badge {
        background: linear-gradient(90deg, #7B2D00, #C44B00);
        color: #FFD580; border-radius: 6px; padding: 4px 10px;
        font-size: 0.75rem; font-weight: 600; display: inline-block; margin-bottom: 8px;
    }
    .info-card {
        background: linear-gradient(135deg, #1A2E45, #152638);
        border-left: 4px solid #F5A623; border-radius: 8px; padding: 16px 20px; margin: 8px 0;
    }
    .disclaimer-box {
        background: rgba(220, 50, 47, 0.1); border: 1px solid rgba(220, 50, 47, 0.4);
        border-radius: 8px; padding: 12px 16px; font-size: 0.85rem; margin-top: 16px;
    }
    </style>""",
    unsafe_allow_html=True,
)

mock = st.session_state.get("mock_mode", MOCK_MODE)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Loading ONI data…")
def get_data(mock_flag: bool):
    df = load_oni(mock=mock_flag)
    df_events = detect_events(df)
    latest = get_latest_oni(df_events)
    return df_events, latest

df_events, latest = get_data(mock)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    '<h1 style="color:#F5A623;">📊 Current El Niño Status</h1>',
    unsafe_allow_html=True,
)

if mock:
    st.markdown('<div class="mock-badge">⚠️ SAMPLE DATA — not real observations</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Headline card
# ---------------------------------------------------------------------------
phase_colours = {"El Niño": "#DC322F", "La Niña": "#268BD2", "Neutral": "#2AA578"}
phase_colour = phase_colours.get(latest["phase"], "#F5A623")

strength_map = {
    "Weak": "🟡", "Moderate": "🟠", "Strong": "🔴", "Very Strong": "🚨", "Neutral": "🟢"
}
strength_icon = strength_map.get(latest["strength"], "")

col_main, col_gauge = st.columns([3, 2])

with col_main:
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1A2E45, #0D1B2A);
            border: 2px solid {phase_colour};
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 16px;
        ">
          <div style="font-size:0.85rem; color:#A8BDD0; margin-bottom:4px;">
            ENSO Phase · Season {latest['seas']} {latest['year']}
          </div>
          <div style="font-size:2rem; font-weight:700; color:{phase_colour};">
            {latest['phase']}
          </div>
          <div style="font-size:1.1rem; color:#E8EDF2; margin-top:4px;">
            {strength_icon} <strong>{latest['strength']}</strong> &nbsp;·&nbsp;
            ONI Anomaly: <strong style="color:{phase_colour};">{latest['anom']:+.2f} °C</strong>
          </div>
          <div style="font-size:0.8rem; color:#6C8098; margin-top:8px;">
            Source: NOAA CPC Oceanic Niño Index
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Plain-language summary
    st.markdown("### 📝 Plain-Language Summary")
    if latest["phase"] == "El Niño" and latest["strength"] in ["Strong", "Very Strong"]:
        summary = (
            f"A **{latest['strength'].lower()} El Niño** is currently active (ONI = {latest['anom']:+.2f} °C "
            f"as of {latest['seas']} {latest['year']}). "
            "NOAA confirmed El Niño conditions in June 2026, with a forecast for a very strong "
            "event peaking in November 2026 to January 2027. "
            "Ghana Meteorological Agency (GMet) has urged national preparedness: "
            "expect hotter and drier conditions in many areas, particularly in the north "
            "and central belt, with below-normal rainfall likely in several regions. "
            "Effects are **not uniform** across Ghana — the tropical Atlantic also plays "
            "an important role, and local variability is high."
        )
    else:
        summary = (
            f"The current ENSO phase is **{latest['phase']}** (ONI = {latest['anom']:+.2f} °C). "
            "Monitor the forecast panel below and follow GMet official bulletins for updates."
        )
    st.info(summary)

with col_gauge:
    # ONI gauge chart
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=latest["anom"],
        delta={"reference": 0, "valueformat": ".2f"},
        title={"text": "ONI Anomaly (°C)", "font": {"size": 14, "color": "#A8BDD0"}},
        number={"font": {"size": 36, "color": "#E8EDF2"}, "suffix": " °C"},
        gauge={
            "axis": {"range": [-3, 3], "tickcolor": "#A8BDD0", "tickfont": {"color": "#A8BDD0"}},
            "bar": {"color": phase_colour, "thickness": 0.3},
            "bgcolor": "#1A2E45",
            "borderwidth": 0,
            "steps": [
                {"range": [-3, -2.0], "color": "#0A2A4A"},
                {"range": [-2.0, -1.5], "color": "#0D3B6E"},
                {"range": [-1.5, -0.5], "color": "#1A5276"},
                {"range": [-0.5, 0.5], "color": "#1E3A2F"},
                {"range": [0.5, 1.0], "color": "#4A2800"},
                {"range": [1.0, 1.5], "color": "#6B3200"},
                {"range": [1.5, 2.0], "color": "#8B2000"},
                {"range": [2.0, 3.0], "color": "#A00000"},
            ],
            "threshold": {
                "line": {"color": "#F5A623", "width": 3},
                "thickness": 0.75,
                "value": latest["anom"],
            },
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=20, r=20, t=20, b=10),
        font={"color": "#E8EDF2"},
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Strength legend
    st.markdown(
        """
        <div style="font-size:0.75rem; color:#A8BDD0; text-align:center; line-height:1.8;">
          🟡 Weak: 0.5–0.9 &nbsp;|&nbsp; 🟠 Moderate: 1.0–1.4<br>
          🔴 Strong: 1.5–1.9 &nbsp;|&nbsp; 🚨 Very Strong: ≥ 2.0
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Forecast Panel
# ---------------------------------------------------------------------------
st.markdown("### 🔭 Forecast & Outlook Panel")
st.caption(
    "Values below are sourced from official agencies. "
    "Edit `src/config.py` → `FORECAST_CONFIG` to update when new information is available."
)

fc = FORECAST_CONFIG
fc_cols = st.columns(len(fc))
for i, (key, cfg) in enumerate(fc.items()):
    with fc_cols[i]:
        st.markdown(
            f"""
            <div class="info-card">
              <div style="font-size:0.75rem; color:#6C8098;">{cfg['source']} · Updated {cfg['last_updated']}</div>
              <div style="font-size:0.85rem; font-weight:600; color:#F5A623; margin:6px 0 4px 0;">{cfg['label']}</div>
              <div style="font-size:1.0rem; color:#E8EDF2;">
                {'<strong>{:.0f}%</strong>'.format(cfg['value'] * 100) if cfg['unit'] == 'probability' else
                 '<strong>{:+.1f} {}</strong>'.format(cfg['value'], cfg['unit']) if cfg['unit'] == '°C' else
                 '<span style="font-size:0.85rem;">' + str(cfg['value']) + '</span>'}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ---------------------------------------------------------------------------
# Named Ghana Events Reference
# ---------------------------------------------------------------------------
st.markdown("### 📋 Named Ghana El Niño Events")
events_df = pd.DataFrame(GHANA_EVENTS)
events_df["peak_oni"] = events_df["peak_oni"].apply(
    lambda x: f"+{x} °C" if x is not None else "Developing"
)
events_df.columns = ["Event", "Start Year", "End Year", "Peak ONI", "Notes"]
st.dataframe(
    events_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Event": st.column_config.TextColumn("Event", width="medium"),
        "Peak ONI": st.column_config.TextColumn("Peak ONI", width="small"),
        "Notes": st.column_config.TextColumn("Notes", width="large"),
    },
)

st.divider()

# Disclaimer
st.markdown(
    f'<div class="disclaimer-box">{APP_DISCLAIMER}</div>',
    unsafe_allow_html=True,
)
