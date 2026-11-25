"""
El Niño Watch Ghana — Main Entry Point
Run with: streamlit run Main.py
"""

import streamlit as st
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.config import (
    APP_DISCLAIMER,
    APP_SUBTITLE,
    APP_TITLE,
    APP_VERSION,
    GMETA_URL,
    MOCK_MODE,
    NOAA_URL,
)

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": NOAA_URL,
        "About": f"**{APP_TITLE}** {APP_VERSION} — {APP_SUBTITLE}",
    },
)

# ---------------------------------------------------------------------------
# Inject global CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      /* Import Google Font */
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

      html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
      }

      /* Metric cards */
      div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border: 1px solid #2A4060;
        border-radius: 12px;
        padding: 16px;
      }

      /* Primary buttons */
      .stButton > button {
        background: linear-gradient(135deg, #F5A623, #E8891A);
        color: #0D1B2A;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }
      .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(245, 166, 35, 0.4);
      }

      /* Sidebar styling */
      section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1B2A 0%, #0A1520 100%);
      }

      /* Mock badge */
      .mock-badge {
        background: linear-gradient(90deg, #7B2D00, #C44B00);
        color: #FFD580;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
      }

      /* Info cards */
      .info-card {
        background: linear-gradient(135deg, #1A2E45, #152638);
        border-left: 4px solid #F5A623;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
      }

      /* Phase label chips */
      .el-nino-chip {
        background: rgba(220, 50, 47, 0.2);
        border: 1px solid #DC322F;
        color: #FF6B68;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: 600;
      }
      .neutral-chip {
        background: rgba(42, 165, 120, 0.15);
        border: 1px solid #2AA578;
        color: #3FCFA0;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: 600;
      }
      .la-nina-chip {
        background: rgba(38, 139, 210, 0.2);
        border: 1px solid #268BD2;
        color: #5DADE2;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: 600;
      }

      /* Responsive chart container */
      .chart-container {
        width: 100%;
        overflow-x: auto;
      }

      /* Disclaimer box */
      .disclaimer-box {
        background: rgba(220, 50, 47, 0.1);
        border: 1px solid rgba(220, 50, 47, 0.4);
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.85rem;
        margin-top: 16px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<h1 style='color:#F5A623; font-size:1.4rem; margin-bottom:4px;'>🌊 {APP_TITLE}</h1>",
        unsafe_allow_html=True,
    )
    st.caption(APP_SUBTITLE)
    st.divider()

    # Mock mode toggle
    mock_on = st.toggle(
        "🧪 Mock / Sample Data Mode",
        value=MOCK_MODE,
        help=(
            "When ON, all charts use clearly labelled synthetic data. "
            "Turn OFF (and run update_data.py first) to use real data."
        ),
    )
    # Store in session state so all pages can read it
    st.session_state["mock_mode"] = mock_on

    if mock_on:
        st.markdown(
            '<div class="mock-badge">⚠️ SAMPLE DATA MODE</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "All visualisations show synthetic data for demonstration. "
            "Values are NOT real observations."
        )

    st.divider()

    st.markdown("**Navigation**")
    st.page_link("pages/1_Home.py", label="📊 Current Status", icon=None)
    st.page_link("pages/2_History.py", label="📜 Historical Explorer", icon=None)
    st.page_link("pages/3_Rainfall_Impact.py", label="🌧️ Rainfall Impact", icon=None)
    st.page_link("pages/4_Risk_Estimator.py", label="🎲 Risk Estimator", icon=None)
    st.page_link("pages/5_Sectors.py", label="🏭 Sector Impacts", icon=None)
    st.page_link("pages/6_Farmer_Advisory.py", label="🌱 Farmer Advisory", icon=None)
    st.page_link("pages/7_Methods.py", label="📖 Methods & Sources", icon=None)

    st.divider()
    st.caption(
        f"v{APP_VERSION} · "
        f"[GMet]({GMETA_URL}) · "
        f"[NOAA]({NOAA_URL})"
    )

# ---------------------------------------------------------------------------
# Main landing content
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="text-align:center; padding: 2rem 0 1rem 0;">
      <h1 style="color:#F5A623; font-size:2.5rem; font-weight:700; margin-bottom:0.25rem;">
        🌊 {APP_TITLE}
      </h1>
      <p style="color:#A8BDD0; font-size:1.1rem; max-width:600px; margin:0 auto;">
        {APP_SUBTITLE}
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Hero stat row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("🌡️ Current ENSO Phase", "El Niño", delta="Developing")
with c2:
    st.metric("📈 Latest ONI", "+1.6 °C", delta="Strong")
with c3:
    st.metric("📅 Event Since", "Jun 2026", delta=None)
with c4:
    st.metric("⚠️ GMet Alert", "Active", delta="Preparedness urged")

st.divider()

# Quick navigation cards
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        """
        <div class="info-card">
          <h3 style="color:#F5A623; margin-top:0;">📊 Current Status</h3>
          <p style="color:#A8BDD0; font-size:0.9rem;">
            Live ONI status, forecast panel, and plain-language summary
            of what the 2026/27 El Niño means for Ghana.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        """
        <div class="info-card">
          <h3 style="color:#F5A623; margin-top:0;">🌧️ Rainfall Impact</h3>
          <p style="color:#A8BDD0; font-size:0.9rem;">
            Regional rainfall anomalies, seasonal comparisons, and
            a choropleth map of Ghana showing historical El Niño effects.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        """
        <div class="info-card">
          <h3 style="color:#F5A623; margin-top:0;">🌱 Farmer Advisory</h3>
          <p style="color:#A8BDD0; font-size:0.9rem;">
            Personalised, plain-language crop advice for your region
            and planting stage — shareable via WhatsApp.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Disclaimer
st.markdown(
    f'<div class="disclaimer-box">{APP_DISCLAIMER}</div>',
    unsafe_allow_html=True,
)
