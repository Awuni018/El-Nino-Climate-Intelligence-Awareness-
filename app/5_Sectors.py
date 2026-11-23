"""
Page 5: Sector Impact Cards
Agriculture/cocoa, staple crops, hydropower, health/water.
Includes FAOSTAT crop yield context.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.config import APP_TITLE, MOCK_MODE
from src.data_loader import load_oni, load_faostat
from src.analysis import detect_events

st.set_page_config(
    page_title=f"Sector Impacts — {APP_TITLE}",
    page_icon="🏭",
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
    .sector-card {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        border-top: 3px solid #F5A623;
    }
    .risk-pill-high {
        background: rgba(220,50,47,0.2); border: 1px solid #DC322F;
        color: #FF6B68; border-radius: 20px; padding: 2px 10px;
        font-size: 0.8rem; font-weight: 600; display: inline-block;
    }
    .risk-pill-moderate {
        background: rgba(245,166,35,0.2); border: 1px solid #F5A623;
        color: #FFD580; border-radius: 20px; padding: 2px 10px;
        font-size: 0.8rem; font-weight: 600; display: inline-block;
    }
    .source-cite { font-size: 0.75rem; color: #6C8098; font-style: italic; margin-top: 8px; }
    </style>""",
    unsafe_allow_html=True,
)

mock = st.session_state.get("mock_mode", MOCK_MODE)

@st.cache_data(ttl=3600, show_spinner="Loading sector data…")
def get_data(mock_flag: bool):
    oni_raw = load_oni(mock=mock_flag)
    oni_events = detect_events(oni_raw)
    fao = load_faostat(mock=mock_flag)
    return oni_events, fao

oni_df, fao_df = get_data(mock)

el_nino_years = oni_df[oni_df["phase"] == "El Niño"]["YR"].unique().tolist()
ghana_events_years = [1983, 1998, 2016, 2024]

st.markdown('<h1 style="color:#F5A623;">🏭 Sector Impact Cards</h1>', unsafe_allow_html=True)

if mock:
    st.markdown('<div class="mock-badge">⚠️ SAMPLE DATA — not real observations</div>', unsafe_allow_html=True)

st.markdown(
    "Rule-based, informational cards on how El Niño affects key sectors in Ghana. "
    "Sources are cited on each card. No statistics are invented."
)

# ---------------------------------------------------------------------------
# Card 1: Agriculture & Cocoa
# ---------------------------------------------------------------------------
with st.expander("🍫 Agriculture & Cocoa — High Risk", expanded=True):
    st.markdown(
        """
        <div class="sector-card">
          <span class="risk-pill-high">High Risk</span>
          <h3 style="color:#F5A623; margin-top:12px;">What is at risk</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>Cocoa (flowering & pod development):</strong> Extended dry spells
              during the main flowering period (Oct–Jan) can cause severe flower drop
              and pod abortion. Irregular wet-dry cycles increase black pod disease
              (<em>Phytophthora megakarya</em>).</li>
            <li><strong>Cocoa yield:</strong> Ghana's cocoa production is concentrated
              in the forest belt where El Niño years are associated with below-normal
              rainfall in the minor season.</li>
            <li><strong>Maize (all zones):</strong> Water stress at flowering and grain fill
              causes the greatest yield losses — up to 70% under severe drought.
              Northern Ghana, with its single rainy season, faces the highest risk.</li>
          </ul>

          <h3 style="color:#F5A623;">What happened in past events</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>1982/83:</strong> Severe drought across the forest and northern zones.
              Widespread crop failure, particularly for maize and food crops.</li>
            <li><strong>1997/98:</strong> Cocoa production declined. Food insecurity in
              northern Ghana was reported.</li>
            <li><strong>2015/16:</strong> Cocoa yield declined; black pod disease pressure
              increased following the erratic wet-dry pattern. COCOBOD noted yield shortfalls.
              Source: COCOBOD Annual Report 2016.</li>
          </ul>

          <h3 style="color:#F5A623;">GMet preparedness tips</h3>
          <ul style="color:#E8EDF2;">
            <li>Use drought-tolerant maize and cocoa varieties (CSIR, CIMMYT, CRIG recommendations).</li>
            <li>Apply fungicides on cocoa according to the CRIG black pod calendar.</li>
            <li>Plant at onset of confirmed rains — do not plant on false onset.</li>
            <li>Practice water harvesting (tied ridges, half-moons) in northern Ghana.</li>
          </ul>
          <div class="source-cite">
            Sources: GMet El Niño preparedness advisory (2023); COCOBOD Annual Report 2016;
            CRIG crop management guidelines; CSIR-SARI Northern Ghana guidelines.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # FAOSTAT cocoa yield chart
    st.markdown("#### Cocoa & Maize Yield Trends with El Niño Years Highlighted")
    if mock:
        st.markdown('<div class="mock-badge">⚠️ Sample yield data</div>', unsafe_allow_html=True)

    for crop in ["Cocoa beans", "Maize"]:
        crop_df = fao_df[fao_df["crop"] == crop].copy()
        if crop_df.empty:
            continue

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=crop_df["year"],
            y=crop_df["yield_kg_ha"],
            mode="lines",
            name=crop,
            line=dict(color="#A8BDD0", width=1.5),
        ))

        # Highlight El Niño years
        for yr in ghana_events_years:
            match = crop_df[crop_df["year"] == yr]
            if len(match):
                fig.add_trace(go.Scatter(
                    x=[yr],
                    y=[float(match["yield_kg_ha"].iloc[0])],
                    mode="markers",
                    marker=dict(color="#DC322F", size=10, symbol="star"),
                    name=f"El Niño {yr}",
                    showlegend=(yr == ghana_events_years[0]),
                ))

        fig.add_vrect(
            x0=2024, x1=2027, fillcolor="rgba(220,50,47,0.1)",
            line_width=0, annotation_text="2026/27 Event",
            annotation_position="top left",
            annotation_font_color="#F5A623",
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,27,42,0.5)",
            height=280,
            margin=dict(l=10, r=10, t=10, b=40),
            xaxis=dict(title="Year", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title="Yield (kg/ha)", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(font=dict(color="#A8BDD0"), bgcolor="rgba(0,0,0,0)"),
            font=dict(color="#E8EDF2"),
            title=dict(text=f"{crop} — Ghana Yield (kg/ha)", font=dict(color="#F5A623", size=13)),
        )
        st.plotly_chart(fig, use_container_width=True)
        csv_data = crop_df.to_csv(index=False)
        st.download_button(f"⬇️ {crop} yield CSV", data=csv_data,
                           file_name=f"faostat_{crop.lower().replace(' ', '_')}.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# Card 2: Hydropower & Electricity
# ---------------------------------------------------------------------------
with st.expander("⚡ Hydropower & Electricity — High Risk (2–6 month lag)"):
    st.markdown(
        """
        <div class="sector-card">
          <span class="risk-pill-high">High Risk</span>
          <h3 style="color:#F5A623; margin-top:12px;">What is at risk</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>Volta River inflow:</strong> Ghana's major hydropower dams
              (Akosombo, Kpong, Bui) depend on Volta River inflows which are
              driven by rainfall in the upstream watershed spanning Ghana, Burkina Faso,
              and Mali. Rainfall deficits reach dams with a 2–6 month lag.</li>
            <li><strong>Electricity generation:</strong> Reduced reservoir levels
              force load-shedding (locally called "dumsor") and increased dependence
              on expensive thermal power, raising energy costs nationally.</li>
            <li><strong>Industrial and agricultural users:</strong> Irrigation
              pumps, cold storage, and agro-processing all depend on reliable electricity.</li>
          </ul>

          <h3 style="color:#F5A623;">What happened in past events</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>2015/16:</strong> The El Niño-linked drought reduced Volta inflows
              significantly, contributing to severe electricity rationing ("dumsor").
              Businesses and households faced 12–16 hours of daily power cuts.
              The economic cost was estimated at hundreds of millions of dollars.
              Source: Energy Commission of Ghana; World Bank Ghana Economic Update 2016.</li>
            <li><strong>1982/83 and 1997/98:</strong> Both strong El Niño events were
              associated with reduced Volta levels and electricity constraints.</li>
          </ul>

          <h3 style="color:#F5A623;">GMet & sector preparedness tips</h3>
          <ul style="color:#E8EDF2;">
            <li>VRA (Volta River Authority) should monitor upstream catchment rainfall
              forecasts closely and plan generation schedules accordingly.</li>
            <li>Businesses: assess backup power options and energy efficiency.</li>
            <li>Farmers with irrigation pumps: plan pumping schedule around grid availability
              and consider solar-powered pumps as a resilience measure.</li>
          </ul>
          <div class="source-cite">
            Sources: GMet El Niño preparedness advisory (2023); Energy Commission of Ghana;
            World Bank Ghana Economic Update 2016; Volta River Authority public reports.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Card 3: Heat & Health
# ---------------------------------------------------------------------------
with st.expander("🌡️ Heat & Health — Moderate to High Risk"):
    st.markdown(
        """
        <div class="sector-card">
          <span class="risk-pill-high">Moderate–High Risk</span>
          <h3 style="color:#F5A623; margin-top:12px;">What is at risk</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>Heat stress:</strong> El Niño years are associated with warmer
              temperatures across West Africa. GMet has specifically highlighted hotter
              dry seasons in the 2026 outlook. Heat stress increases mortality risk
              for the elderly, children under 5, outdoor workers, and people without
              access to cooling.</li>
            <li><strong>Meningitis:</strong> Northern Ghana's dry season ("harmattan")
              is already a risk season for meningococcal meningitis. Prolonged drought
              and dust conditions extend the high-risk period.</li>
            <li><strong>Malaria:</strong> The relationship between El Niño and malaria
              in Ghana is complex. Dry spells can reduce breeding sites but
              end-of-drought heavy rains can cause population surges.</li>
            <li><strong>Water supply and WASH:</strong> Below-normal rainfall stresses
              water supply systems, especially surface water sources used by rural communities.</li>
          </ul>

          <h3 style="color:#F5A623;">What happened in past events</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>2015/16:</strong> GMet reported above-normal temperatures.
              Health services in northern Ghana reported increased heat-related
              complaints. Source: GMet climate bulletin 2016.</li>
            <li><strong>1998:</strong> Meningitis outbreaks in the northern belt
              coincided with the El Niño-enhanced dry season. Source: WHO.</li>
          </ul>

          <h3 style="color:#F5A623;">Preparedness tips</h3>
          <ul style="color:#E8EDF2;">
            <li>GHS: Pre-position meningitis vaccines for northern Ghana.</li>
            <li>Communities: Identify and monitor vulnerable people (elderly, children)
              during heat peaks. Use natural ventilation, shade, and cool water access.</li>
            <li>Water utilities: Assess dry-season water availability and implement
              contingency rationing plans early.</li>
          </ul>
          <div class="source-cite">
            Sources: GMet El Niño preparedness advisory (2023); GMet climate bulletin 2016;
            Ghana Health Service; WHO meningitis belt data.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Card 4: Water Supply & Food Security
# ---------------------------------------------------------------------------
with st.expander("💧 Water Supply & Food Security — Moderate to High Risk"):
    st.markdown(
        """
        <div class="sector-card">
          <span class="risk-pill-moderate">Moderate Risk (South) · High Risk (North)</span>
          <h3 style="color:#F5A623; margin-top:12px;">What is at risk</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>Rural water supply:</strong> Communities depending on seasonal
              rivers, ponds, and hand-dug wells are most vulnerable to below-normal
              rainfall. The Northern zone is at highest risk.</li>
            <li><strong>Urban water:</strong> GWCL (Ghana Water Company Limited) systems
              drawing from rivers (e.g., the Densu, Pra) may face lower intake
              during prolonged dry periods in the southern zone.</li>
            <li><strong>Food security:</strong> Northern Ghana, with its single rainy season
              and high dependence on rain-fed agriculture, faces the greatest food
              insecurity risk. Market prices of staples typically rise in El Niño years
              with poor harvests. Source: FEWS NET Ghana food security outlook.</li>
          </ul>

          <h3 style="color:#F5A623;">What happened in past events</h3>
          <ul style="color:#E8EDF2;">
            <li><strong>1982/83:</strong> Water scarcity in northern Ghana. Emergency
              food aid was required in some districts.</li>
            <li><strong>2015/16:</strong> FEWS NET classified parts of northern Ghana
              as "stressed" food security phase (IPC Phase 2) during the lean season.
              Source: FEWS NET Ghana, 2016.</li>
          </ul>

          <h3 style="color:#F5A623;">Preparedness tips</h3>
          <ul style="color:#E8EDF2;">
            <li>CWSA, water utilities: conduct dry-season vulnerability assessments now.</li>
            <li>NADMO: Pre-position emergency food and water stocks for high-risk districts.</li>
            <li>Communities: Diversify water sources; maintain rainwater harvesting structures.
              Plant drought-tolerant crops (cassava, cowpea, sorghum) as a food security buffer.</li>
            <li>MOFA: Activate early warning food security monitoring in northern districts.</li>
          </ul>
          <div class="source-cite">
            Sources: GMet El Niño preparedness advisory (2023); FEWS NET Ghana food security
            outlook 2016; CWSA; NADMO; MOFA Ghana food security monitoring.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Cassava and Rice yield charts (from FAOSTAT)
st.divider()
st.markdown("### 📊 Cassava & Rice Yield Trends")
if mock:
    st.markdown('<div class="mock-badge">⚠️ Sample yield data</div>', unsafe_allow_html=True)

for crop in ["Cassava", "Rice, paddy"]:
    crop_df = fao_df[fao_df["crop"] == crop].copy()
    if crop_df.empty:
        continue
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=crop_df["year"], y=crop_df["yield_kg_ha"],
        mode="lines", line=dict(color="#A8BDD0", width=1.5), name=crop,
    ))
    for yr in ghana_events_years:
        m = crop_df[crop_df["year"] == yr]
        if len(m):
            fig.add_trace(go.Scatter(
                x=[yr], y=[float(m["yield_kg_ha"].iloc[0])],
                mode="markers", marker=dict(color="#DC322F", size=10, symbol="star"),
                name=f"El Niño {yr}", showlegend=(yr == ghana_events_years[0]),
            ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.5)",
        height=240, margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(title="Year", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="Yield (kg/ha)", color="#A8BDD0", gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(font=dict(color="#A8BDD0"), bgcolor="rgba(0,0,0,0)"),
        font=dict(color="#E8EDF2"),
        title=dict(text=f"{crop} — Ghana Yield (kg/ha)", font=dict(color="#F5A623", size=13)),
    )
    st.plotly_chart(fig, use_container_width=True)
