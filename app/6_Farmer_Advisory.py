"""
Page 6: Farmer Advisory Generator
Rule-based advice from advisory_rules.yaml. WhatsApp share button.
i18n ready (English first, stubs for Twi/Ga/Ewe/Hausa).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import yaml
from pathlib import Path as PPath

from src.config import APP_TITLE, GHANA_REGIONS, GHANA_ZONES, MOCK_MODE

RULES_PATH = PPath(__file__).parent.parent / "src" / "advisory_rules.yaml"

LANGUAGE_LABELS = {
    "en": "English",
    "tw": "Twi (Asante)",
    "ga": "Ga",
    "ee": "Ewe",
    "ha": "Hausa",
}

STAGE_LABELS = {
    "pre_planting": "Pre-Planting / Preparation",
    "planting": "Planting",
    "vegetative": "Vegetative Growth",
    "flowering": "Flowering / Pod Development",
    "grain_fill": "Grain Fill / Root Bulking",
    "harvest": "Harvest",
    "post_harvest": "Post-Harvest / Storage",
}

RISK_COLOURS = {
    "low": "#2AA578",
    "moderate": "#F5A623",
    "high": "#DC322F",
    "very_high": "#8B0000",
}

st.set_page_config(
    page_title=f"Farmer Advisory — {APP_TITLE}",
    page_icon="🌱",
    layout="wide",
)

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .advice-card {
        background: linear-gradient(135deg, #1A2E45, #0D1B2A);
        border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
    }
    .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 0.9rem; }
    </style>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load rules
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

try:
    rules = load_rules()
    rules_ok = True
except Exception as e:
    st.error(f"Could not load advisory rules: {e}")
    rules_ok = False
    rules = {}

st.markdown('<h1 style="color:#F5A623;">🌱 Farmer Advisory Generator</h1>', unsafe_allow_html=True)
st.markdown(
    "Get plain-language, El Niño-aware advice for your crop, region, and planting stage. "
    "Advice comes from a transparent rules file — no AI-generated text."
)

if not rules_ok:
    st.stop()

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
crop_options = {k: v["display_name"] for k, v in rules.get("crops", {}).items()}
zone_options = list(GHANA_ZONES.keys())

col1, col2, col3, col4 = st.columns(4)

with col1:
    crop_key = st.selectbox(
        "🌾 Crop",
        list(crop_options.keys()),
        format_func=lambda k: f"{rules['crops'][k]['emoji']} {crop_options[k]}",
    )

with col2:
    region_sel = st.selectbox(
        "🗺️ Region / Zone",
        zone_options + GHANA_REGIONS,
        help="Select your zone (Coastal, Forest, Northern) or specific region.",
    )
    # Resolve zone
    if region_sel in GHANA_ZONES:
        effective_zone = region_sel
    else:
        effective_zone = None
        for zone, regs in GHANA_ZONES.items():
            if region_sel in regs:
                effective_zone = zone
                break

with col3:
    stage_key = st.selectbox(
        "🌱 Planting Stage",
        list(STAGE_LABELS.keys()),
        format_func=lambda k: STAGE_LABELS[k],
    )

with col4:
    lang = st.selectbox(
        "🌐 Language",
        list(LANGUAGE_LABELS.keys()),
        format_func=lambda k: LANGUAGE_LABELS[k],
    )

st.divider()

# ---------------------------------------------------------------------------
# Look up advice
# ---------------------------------------------------------------------------
crop_data = rules.get("crops", {}).get(crop_key, {})
crop_regions = crop_data.get("regions", {})

# Try specific zone, then fallback to nearest zone
zone_data = None
if effective_zone and effective_zone in crop_regions:
    zone_data = crop_regions[effective_zone]
else:
    # Try any available zone as fallback
    for available_zone in crop_regions:
        zone_data = crop_regions[available_zone]
        st.info(
            f"ℹ️ No specific rules for **{effective_zone or region_sel}**. "
            f"Showing advice for **{available_zone}** as the nearest zone."
        )
        break

if zone_data is None:
    st.warning("No advisory rules found for this crop/region combination.")
    st.stop()

stage_data = zone_data.get("stages", {}).get(stage_key, {})
if not stage_data:
    st.warning(f"No rules found for stage: {STAGE_LABELS.get(stage_key, stage_key)}")
    st.stop()

risk_level = stage_data.get("risk_level", "moderate")
advice_dict = stage_data.get("advice", {})
advice_text = advice_dict.get(lang, "")
source = stage_data.get("source", "")

# Fallback to English if translation stub is empty
if not advice_text and lang != "en":
    advice_text = advice_dict.get("en", "")
    if advice_text:
        st.info(
            f"ℹ️ Translation for **{LANGUAGE_LABELS[lang]}** is not yet available. "
            "Showing English."
        )

# General El Niño context
general_advice = rules.get("general_el_nino", {}).get(lang, "") or rules.get("general_el_nino", {}).get("en", "")

# ---------------------------------------------------------------------------
# Display advice
# ---------------------------------------------------------------------------
risk_colour = RISK_COLOURS.get(risk_level, "#F5A623")
risk_label = risk_level.replace("_", " ").title()

crop_emoji = crop_data.get("emoji", "🌾")
crop_display = crop_data.get("display_name", crop_key)

st.markdown(
    f"""
    <div class="advice-card" style="border-top: 3px solid {risk_colour};">
      <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <span style="font-size:2rem;">{crop_emoji}</span>
        <div>
          <div style="font-size:1.1rem; font-weight:700; color:#F5A623;">
            {crop_display} · {region_sel} · {STAGE_LABELS[stage_key]}
          </div>
          <div style="font-size:0.8rem; color:#A8BDD0;">
            Language: {LANGUAGE_LABELS[lang]}
          </div>
        </div>
        <div style="margin-left:auto;">
          <span style="
              background: {risk_colour}33;
              border: 1px solid {risk_colour};
              color: {risk_colour};
              border-radius: 20px; padding: 4px 14px;
              font-size: 0.85rem; font-weight: 600;
          ">⚠️ {risk_label} Risk</span>
        </div>
      </div>
      <div style="color:#E8EDF2; line-height:1.7; font-size:0.95rem;">
        {advice_text or '<em style="color:#6C8098;">No advice text available.</em>'}
      </div>
      {"<div style='font-size:0.75rem; color:#6C8098; margin-top:12px;'>Source: " + source + "</div>" if source else ""}
    </div>
    """,
    unsafe_allow_html=True,
)

# General El Niño context
with st.expander("🌊 General El Niño Context (2026/27 Event)"):
    st.markdown(
        f'<div style="color:#E8EDF2; line-height:1.7;">{general_advice}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Source: NOAA CPC ENSO outlook (October 2026); "
        "Ghana Meteorological Agency (GMet) preparedness advisory (2023)."
    )

st.divider()

# ---------------------------------------------------------------------------
# Share summary (WhatsApp-friendly plain text)
# ---------------------------------------------------------------------------
st.markdown("### 📲 Share Advisory")
meta = rules.get("meta", {})

share_text = (
    f"🌾 El Niño Watch Ghana — Farmer Advisory\n"
    f"{'=' * 40}\n"
    f"Crop: {crop_display}\n"
    f"Region: {region_sel}\n"
    f"Stage: {STAGE_LABELS[stage_key]}\n"
    f"Risk level: {risk_label}\n\n"
    f"ADVICE:\n{advice_text}\n\n"
    f"Source: {source}\n\n"
    f"{'=' * 40}\n"
    f"⚠️ DISCLAIMER: This advice is based on historical patterns of El Niño effects.\n"
    f"It is NOT an official forecast. Follow GMet (meteo.gov.gh) for official guidance.\n\n"
    f"Generated by El Niño Watch Ghana (MVP {meta.get('version', '1.0')})\n"
    f"Event: {meta.get('el_nino_event', '2026/27 El Niño')}"
)

st.text_area(
    "Copy text below and paste into WhatsApp, SMS, or radio script:",
    value=share_text,
    height=280,
    key="share_text_area",
)

col_dl, col_copy = st.columns(2)
with col_dl:
    st.download_button(
        "⬇️ Download advisory (.txt)",
        data=share_text,
        file_name=f"advisory_{crop_key}_{region_sel.lower().replace(' ', '_')}_{stage_key}.txt",
        mime="text/plain",
    )

# ---------------------------------------------------------------------------
# i18n status notice
# ---------------------------------------------------------------------------
st.divider()
st.markdown("#### 🌐 Translation Status")
lang_status = []
for lang_code, lang_name in LANGUAGE_LABELS.items():
    text = advice_dict.get(lang_code, "")
    status = "✅ Available" if text and text.strip() else "🔲 Stub (English fallback)"
    lang_status.append({"Language": lang_name, "Code": lang_code, "Status": status})

import pandas as pd
st.dataframe(pd.DataFrame(lang_status), use_container_width=True, hide_index=True)
st.caption(
    "Translation stubs are ready in `src/advisory_rules.yaml`. "
    "Add translations under each language key (tw, ga, ee, ha) to enable them."
)

# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
from src.config import APP_DISCLAIMER
st.markdown(
    f'<div style="background:rgba(220,50,47,0.1);border:1px solid rgba(220,50,47,0.4);'
    f'border-radius:8px;padding:12px 16px;font-size:0.85rem;margin-top:16px;">'
    f'{APP_DISCLAIMER}</div>',
    unsafe_allow_html=True,
)
