"""
Page 2: Historical ONI Explorer
ONI timeline 1950-present, shaded phases, event annotations, comparison view.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from src.config import APP_TITLE, GHANA_EVENTS, MOCK_MODE
from src.data_loader import load_oni
from src.analysis import detect_events, SEASON_ORDER

st.set_page_config(
    page_title=f"Historical Explorer — {APP_TITLE}",
    page_icon="📜",
    layout="wide",
)

# Re-inject CSS
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .mock-badge {
        background: linear-gradient(90deg, #7B2D00, #C44B00);
        color: #FFD580; border-radius: 6px; padding: 4px 10px;
        font-size: 0.75rem; font-weight: 600; display: inline-block; margin-bottom: 8px;
    }
    </style>""",
    unsafe_allow_html=True,
)

mock = st.session_state.get("mock_mode", MOCK_MODE)

@st.cache_data(ttl=3600, show_spinner="Loading ONI data…")
def get_oni_data(mock_flag: bool):
    df = load_oni(mock=mock_flag)
    return detect_events(df)

df = get_oni_data(mock)

st.markdown('<h1 style="color:#F5A623;">📜 Historical ONI Explorer</h1>', unsafe_allow_html=True)

if mock:
    st.markdown('<div class="mock-badge">⚠️ SAMPLE DATA — not real observations</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab layout: Timeline | Event Comparison
# ---------------------------------------------------------------------------
tab_timeline, tab_compare = st.tabs(["📈 ONI Timeline (1950–Present)", "🔍 Event Comparison"])

# ---------------------------------------------------------------------------
# TAB 1: ONI TIMELINE
# ---------------------------------------------------------------------------
with tab_timeline:
    st.markdown(
        "Interactive ONI anomaly timeline. "
        "**Red** shading = El Niño, **Blue** = La Niña. "
        "Hover for details. Use the toolbar to zoom, pan, and download."
    )

    # Build a decimal year column for plotting
    season_to_month = {s: (i + 1) for i, s in enumerate(SEASON_ORDER)}
    df["decimal_year"] = df["YR"] + (df["SEAS"].map(season_to_month) - 1) / 12

    fig = go.Figure()

    # El Niño shading (fill under/over zero line)
    el_nino_mask = df["ANOM"] >= 0.5
    la_nina_mask = df["ANOM"] <= -0.5

    # Main ONI line
    fig.add_trace(go.Scatter(
        x=df["decimal_year"],
        y=df["ANOM"],
        mode="lines",
        name="ONI Anomaly",
        line=dict(color="#A8BDD0", width=1.0),
        hovertemplate=(
            "<b>%{customdata[0]} %{customdata[1]}</b><br>"
            "ONI: %{y:+.2f} °C<br>"
            "Phase: %{customdata[2]}<br>"
            "Event: %{customdata[3]}<extra></extra>"
        ),
        customdata=df[["SEAS", "YR", "phase", "event_id"]].values,
    ))

    # El Niño fill
    fig.add_trace(go.Scatter(
        x=df["decimal_year"],
        y=df["ANOM"].where(df["ANOM"] >= 0.5, 0.5).clip(lower=0.5),
        fill="tonexty",
        fillcolor="rgba(220, 50, 47, 0.3)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
        name="_el_fill_top",
    ))

    # Actually let's use proper shading with vrect for each event
    # Remove the fill traces above and use proper event shading
    fig.data = [fig.data[0]]  # keep only ONI line

    # Shade El Niño and La Niña event periods using shapes
    for _, row in df[df["in_event"]].groupby("event_id"):
        pass  # replaced by continuous colour below

    # Positive/negative filled areas
    df_pos = df.copy()
    df_pos.loc[df_pos["ANOM"] < 0.5, "ANOM"] = 0.5

    fig.add_trace(go.Scatter(
        x=pd.concat([df["decimal_year"], df["decimal_year"][::-1]]),
        y=pd.concat([
            df["ANOM"].clip(lower=0.5).where(df["ANOM"] >= 0.5, 0.5),
            pd.Series([0.5] * len(df)),
        ]),
        fill="toself",
        fillcolor="rgba(220, 50, 47, 0.25)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=True,
        name="El Niño",
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=pd.concat([df["decimal_year"], df["decimal_year"][::-1]]),
        y=pd.concat([
            df["ANOM"].clip(upper=-0.5).where(df["ANOM"] <= -0.5, -0.5),
            pd.Series([-0.5] * len(df)),
        ]),
        fill="toself",
        fillcolor="rgba(38, 139, 210, 0.25)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=True,
        name="La Niña",
        hoverinfo="skip",
    ))

    # Re-add ONI line on top
    fig.add_trace(go.Scatter(
        x=df["decimal_year"],
        y=df["ANOM"],
        mode="lines",
        name="ONI",
        line=dict(color="#E8EDF2", width=1.5),
        hovertemplate=(
            "<b>%{customdata[0]} %{customdata[1]}</b><br>"
            "ONI: %{y:+.2f} °C<br>"
            "Phase: %{customdata[2]}<br>"
            "%{customdata[3]}<extra></extra>"
        ),
        customdata=df[["SEAS", "YR", "phase", "event_id"]].values,
        showlegend=False,
    ))

    # Threshold lines
    fig.add_hline(y=0.5, line_dash="dash", line_color="rgba(220,50,47,0.6)", line_width=1)
    fig.add_hline(y=-0.5, line_dash="dash", line_color="rgba(38,139,210,0.6)", line_width=1)
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=0.5)

    # Annotate named Ghana events
    for event in GHANA_EVENTS:
        if event["peak_oni"] is not None:
            fig.add_annotation(
                x=event["start_year"] + 0.5,
                y=event["peak_oni"],
                text=f"🇬🇭 {event['start_year'][:4] if isinstance(event['start_year'], str) else event['start_year']}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#F5A623",
                font=dict(size=10, color="#F5A623"),
                bgcolor="rgba(13,27,42,0.8)",
                bordercolor="#F5A623",
                borderwidth=1,
                arrowsize=1.0,
                ax=0,
                ay=-35,
            )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.5)",
        height=450,
        margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(
            title="Year",
            color="#A8BDD0",
            gridcolor="rgba(255,255,255,0.05)",
            showgrid=True,
            tickformat=".0f",
            range=[1950, 2028],
        ),
        yaxis=dict(
            title="ONI Anomaly (°C)",
            color="#A8BDD0",
            gridcolor="rgba(255,255,255,0.05)",
            showgrid=True,
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.15)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#A8BDD0"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        font=dict(color="#E8EDF2"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Download
    csv = df[["SEAS", "YR", "ANOM", "phase", "in_event", "event_id", "strength"]].to_csv(index=False)
    st.download_button(
        "⬇️ Download ONI data (CSV)",
        data=csv,
        file_name="oni_data.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------
# TAB 2: EVENT COMPARISON
# ---------------------------------------------------------------------------
with tab_compare:
    st.markdown(
        "Compare ONI trajectories of past El Niño events on a shared month axis. "
        "Month 0 = June of the event start year."
    )

    event_labels = [e["label"] for e in GHANA_EVENTS if e["peak_oni"] is not None]
    selected_events = st.multiselect(
        "Select events to compare (1–4):",
        event_labels,
        default=event_labels[:3],
        max_selections=4,
    )

    if selected_events:
        fig_comp = go.Figure()
        palette = ["#F5A623", "#DC322F", "#268BD2", "#2AA578"]

        for i, event_label in enumerate(selected_events):
            event_meta = next(e for e in GHANA_EVENTS if e["label"] == event_label)
            start_yr = event_meta["start_year"]

            # Get 24 months from June of start year
            event_rows = []
            for month_offset in range(24):
                target_yr = start_yr + (month_offset // 12)
                target_seas_idx = (5 + month_offset) % 12  # June = index 5
                target_seas = SEASON_ORDER[target_seas_idx]
                match = df[(df["YR"] == target_yr) & (df["SEAS"] == target_seas)]
                if len(match):
                    event_rows.append({
                        "month_offset": month_offset,
                        "ANOM": float(match["ANOM"].iloc[0]),
                    })

            if event_rows:
                ev_df = pd.DataFrame(event_rows)
                fig_comp.add_trace(go.Scatter(
                    x=ev_df["month_offset"],
                    y=ev_df["ANOM"],
                    mode="lines+markers",
                    name=event_label,
                    line=dict(color=palette[i % len(palette)], width=2.5),
                    marker=dict(size=5),
                    hovertemplate=f"<b>{event_label}</b><br>Month +%{{x}}: %{{y:+.2f}} °C<extra></extra>",
                ))

        # Current event (2026)
        current_rows = []
        for m_off in range(24):
            yr = 2026 + (m_off // 12)
            seas_idx = (5 + m_off) % 12
            seas = SEASON_ORDER[seas_idx]
            match = df[(df["YR"] == yr) & (df["SEAS"] == seas)]
            if len(match):
                current_rows.append({"month_offset": m_off, "ANOM": float(match["ANOM"].iloc[0])})
        if current_rows:
            cur_df = pd.DataFrame(current_rows)
            fig_comp.add_trace(go.Scatter(
                x=cur_df["month_offset"],
                y=cur_df["ANOM"],
                mode="lines+markers",
                name="2026/27 (Current/Forecast)",
                line=dict(color="#FFD580", width=3, dash="dot"),
                marker=dict(size=6, symbol="star"),
                hovertemplate="<b>2026/27 (Current)</b><br>Month +%{x}: %{y:+.2f} °C<extra></extra>",
            ))

        fig_comp.add_hline(y=0.5, line_dash="dash", line_color="rgba(220,50,47,0.5)", line_width=1)
        fig_comp.add_hline(y=1.5, line_dash="dot", line_color="rgba(220,50,47,0.3)", line_width=1,
                           annotation_text="Strong threshold", annotation_position="top right",
                           annotation_font_color="#A8BDD0")

        # Month labels
        month_names = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan",
                       "Feb", "Mar", "Apr", "May"] * 2
        tickvals = list(range(0, 24, 2))
        ticktext = [month_names[v] for v in tickvals]

        fig_comp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,27,42,0.5)",
            height=420,
            margin=dict(l=10, r=10, t=20, b=40),
            xaxis=dict(
                title="Month from event onset (June = 0)",
                color="#A8BDD0",
                tickvals=tickvals,
                ticktext=ticktext,
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(
                title="ONI Anomaly (°C)",
                color="#A8BDD0",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            legend=dict(
                font=dict(color="#A8BDD0"),
                bgcolor="rgba(13,27,42,0.8)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
            ),
            hovermode="x unified",
            font=dict(color="#E8EDF2"),
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Select at least one event above to compare trajectories.")
