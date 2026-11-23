"""
Page 3: Regional Rainfall Impact
Region/season selectors, anomaly charts, choropleth map of Ghana.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json

from src.config import APP_TITLE, GHANA_REGIONS, GHANA_ZONES, MOCK_MODE, SEASONS
from src.data_loader import load_oni, load_chirps, load_ghana_boundaries
from src.analysis import compute_anomalies, detect_events, seasonal_anomalies

st.set_page_config(
    page_title=f"Rainfall Impact — {APP_TITLE}",
    page_icon="🌧️",
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
    .sample-note {
        font-size: 0.75rem; color: #C44B00; font-style: italic;
    }
    </style>""",
    unsafe_allow_html=True,
)

mock = st.session_state.get("mock_mode", MOCK_MODE)

@st.cache_data(ttl=3600, show_spinner="Loading rainfall data…")
def get_data(mock_flag: bool):
    chirps = load_chirps(mock=mock_flag)
    chirps_anom = compute_anomalies(chirps)
    oni_raw = load_oni(mock=mock_flag)
    oni_events = detect_events(oni_raw)
    boundaries = load_ghana_boundaries(mock=mock_flag)
    return chirps_anom, oni_events, boundaries

chirps_df, oni_df, boundaries = get_data(mock)

st.markdown('<h1 style="color:#F5A623;">🌧️ Regional Rainfall Impact</h1>', unsafe_allow_html=True)

if mock:
    st.markdown('<div class="mock-badge">⚠️ SAMPLE DATA — not real observations</div>', unsafe_allow_html=True)

st.markdown(
    "Explore how El Niño years have historically affected rainfall across Ghana's regions. "
    "Anomalies are computed against the **1991–2020 climatological baseline**."
)

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------
sel_col1, sel_col2 = st.columns(2)

with sel_col1:
    zone_options = list(GHANA_ZONES.keys())
    all_regions = ["All Regions"] + GHANA_REGIONS
    region_option = st.selectbox(
        "🗺️ Select Region",
        all_regions + zone_options,
        index=0,
        help="Choose a specific region or a zone (aggregated).",
    )

with sel_col2:
    season = st.selectbox(
        "📅 Select Season",
        list(SEASONS.keys()),
        help="Aggregation season for the analysis.",
    )

# Resolve region
if region_option == "All Regions":
    regions_to_show = GHANA_REGIONS
    display_region = "All Regions"
elif region_option in GHANA_ZONES:
    regions_to_show = GHANA_ZONES[region_option]
    display_region = region_option
else:
    regions_to_show = [region_option]
    display_region = region_option

# ---------------------------------------------------------------------------
# Compute seasonal anomalies
# ---------------------------------------------------------------------------
season_months = SEASONS[season]["months"]
season_mask = (
    chirps_df["region"].isin(regions_to_show)
    & chirps_df["month"].isin(season_months)
)
sub = chirps_df[season_mask].copy()
agg = (
    sub.groupby("year")[["rainfall_mm", "anom_mm", "anom_pct"]]
    .mean()
    .reset_index()
)
agg["region"] = display_region
agg["season"] = season

# Join ONI phase info
oni_annual = (
    oni_df[oni_df["SEAS"] == "ASO"]
    .rename(columns={"YR": "year"})
    [["year", "ANOM", "phase", "in_event", "event_id", "strength"]]
)
agg = agg.merge(oni_annual, on="year", how="left")
agg["phase"] = agg["phase"].fillna("Neutral")
agg["in_event"] = agg["in_event"].fillna(False)

n_el_nino = (agg["phase"] == "El Niño").sum()
n_la_nina = (agg["phase"] == "La Niña").sum()
n_neutral = (agg["phase"] == "Neutral").sum()

st.caption(
    f"Showing {len(agg)} years | "
    f"El Niño: {n_el_nino} yrs | La Niña: {n_la_nina} yrs | Neutral: {n_neutral} yrs"
)
if n_el_nino < 10:
    st.warning(
        f"⚠️ Only {n_el_nino} El Niño years in this sample. "
        "Treat comparisons with caution — small samples are sensitive to individual years."
    )

st.divider()

# ---------------------------------------------------------------------------
# Tabs: Bar chart | Box plot | Choropleth
# ---------------------------------------------------------------------------
tab_bar, tab_box, tab_map = st.tabs(
    ["📊 Anomaly by Year", "📦 El Niño vs Neutral vs La Niña", "🗺️ Choropleth Map"]
)

# Phase colour map
phase_colors = {
    "El Niño": "#DC322F",
    "Neutral": "#2AA578",
    "La Niña": "#268BD2",
}

# ---------------------------------------------------------------------------
# TAB 1: Anomaly bar chart
# ---------------------------------------------------------------------------
with tab_bar:
    fig_bar = go.Figure()

    for phase, color in phase_colors.items():
        mask = agg["phase"] == phase
        fig_bar.add_trace(go.Bar(
            x=agg.loc[mask, "year"],
            y=agg.loc[mask, "anom_pct"],
            name=phase,
            marker_color=color,
            opacity=0.85,
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"Phase: {phase}<br>"
                "Anomaly: %{y:.1f}% of normal<extra></extra>"
            ),
        ))

    fig_bar.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)

    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.5)",
        height=400,
        barmode="overlay",
        margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(title="Year", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(
            title="Rainfall Anomaly (% of 1991–2020 normal)",
            color="#A8BDD0",
            gridcolor="rgba(255,255,255,0.05)",
        ),
        legend=dict(font=dict(color="#A8BDD0"), bgcolor="rgba(0,0,0,0)"),
        font=dict(color="#E8EDF2"),
        title=dict(
            text=f"Seasonal Rainfall Anomaly — {display_region} · {season}",
            font=dict(color="#F5A623", size=14),
        ),
    )

    st.plotly_chart(fig_bar, use_container_width=True)
    if mock:
        st.markdown('<span class="sample-note">⚠️ Sample data shown</span>', unsafe_allow_html=True)

    csv_bar = agg.to_csv(index=False)
    st.download_button("⬇️ Download data (CSV)", data=csv_bar, file_name="anomaly_by_year.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# TAB 2: Box plot
# ---------------------------------------------------------------------------
with tab_box:
    fig_box = go.Figure()

    for phase, color in phase_colors.items():
        vals = agg.loc[agg["phase"] == phase, "anom_pct"].dropna()
        n = len(vals)
        fig_box.add_trace(go.Box(
            y=vals,
            name=f"{phase}<br>(n={n})",
            marker_color=color,
            line_color=color,
            fillcolor=color.replace(")", ", 0.2)").replace("rgb", "rgba") if color.startswith("rgb") else color + "33",
            boxmean=True,
            hovertemplate=f"<b>{phase}</b><br>%{{y:.1f}}%<extra></extra>",
        ))

    fig_box.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)

    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.5)",
        height=400,
        margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(color="#A8BDD0"),
        yaxis=dict(
            title="Rainfall Anomaly (% of 1991–2020 normal)",
            color="#A8BDD0",
            gridcolor="rgba(255,255,255,0.05)",
        ),
        font=dict(color="#E8EDF2"),
        title=dict(
            text=f"Anomaly Distribution by ENSO Phase — {display_region} · {season}",
            font=dict(color="#F5A623", size=14),
        ),
        showlegend=False,
    )

    st.plotly_chart(fig_box, use_container_width=True)
    st.caption(
        "⚠️ Sample sizes (n) are shown per phase. "
        "Box shows median, IQR, whiskers to 1.5×IQR. Diamond = mean."
    )
    if mock:
        st.markdown('<span class="sample-note">⚠️ Sample data shown</span>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 3: Choropleth map
# ---------------------------------------------------------------------------
with tab_map:
    st.markdown(
        f"Average rainfall anomaly during **El Niño years** by region, "
        f"season: **{season}**."
    )

    # Compute El Niño average anomaly per region
    el_nino_years = oni_df[oni_df["phase"] == "El Niño"]["YR"].unique()
    region_anom_rows = []
    for reg in GHANA_REGIONS:
        reg_mask = (
            chirps_df["region"] == reg
            & chirps_df["month"].isin(season_months)
            & chirps_df["year"].isin(el_nino_years)
        )
        vals = chirps_df[reg_mask]["anom_pct"]
        region_anom_rows.append({
            "region": reg,
            "mean_anom_pct": float(vals.mean()) if len(vals) else 0.0,
            "n_years": int(vals.count()),
        })
    region_anom_df = pd.DataFrame(region_anom_rows)

    if boundaries and boundaries.get("features"):
        # Augment GeoJSON features with anomaly data
        for feature in boundaries["features"]:
            rname = feature["properties"].get("shapeName", "")
            match = region_anom_df[region_anom_df["region"] == rname]
            if len(match):
                feature["properties"]["mean_anom_pct"] = float(match["mean_anom_pct"].iloc[0])
                feature["properties"]["n_years"] = int(match["n_years"].iloc[0])
            else:
                feature["properties"]["mean_anom_pct"] = None
                feature["properties"]["n_years"] = 0

        fig_map = px.choropleth_map(
            region_anom_df,
            geojson=boundaries,
            locations="region",
            featureidkey="properties.shapeName",
            color="mean_anom_pct",
            color_continuous_scale=[
                [0.0, "#8B2000"],    # strongly negative
                [0.3, "#DC322F"],    # moderate negative
                [0.5, "#2A2A2A"],    # near normal
                [0.7, "#268BD2"],    # moderate positive
                [1.0, "#0A3D6E"],    # strongly positive
            ],
            range_color=[-30, 30],
            zoom=5.5,
            center={"lat": 7.9, "lon": -1.0},
            opacity=0.75,
            labels={"mean_anom_pct": "Anomaly (%)"},
            hover_data={"n_years": True},
            title=f"Mean El Niño Rainfall Anomaly (%) — {season}",
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=500,
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(
                title="% of normal",
                tickfont=dict(color="#A8BDD0"),
                titlefont=dict(color="#A8BDD0"),
            ),
            font=dict(color="#E8EDF2"),
            map_style="carto-darkmatter",
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning(
            "Ghana boundary GeoJSON could not be loaded. "
            "Showing data table instead."
        )
        st.dataframe(region_anom_df, use_container_width=True, hide_index=True)

    if mock:
        st.markdown('<span class="sample-note">⚠️ Sample data shown</span>', unsafe_allow_html=True)

    st.caption(
        "Red = below-normal rainfall; Blue = above-normal. "
        f"Averaged over all El Niño years in the dataset ({n_el_nino} years)."
    )
