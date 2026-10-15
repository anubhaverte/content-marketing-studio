"""Card Studio — Streamlit Web Application.
Interactive ID Card generation app for Streamlit Community Cloud deployment.
"""
from __future__ import annotations

import base64
import io
import json
import sys
import os
from pathlib import Path
from typing import Any

import streamlit as st
import pandas as pd

# Setup repository paths
REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Propagate Streamlit secrets to environment variables if available
try:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    pass

# Backend modules
from app.brief.extract import extract_brief
from app.brief.missing_info import find_missing
from app.brief.questions import build_questions
from app.brief.schema import Brief
from app.data.csv_loader import load_people_csv
from app.data.validator import validate_people
from app.generator.drafts import generate_drafts
from app.spec.schema import Person, DesignSpec
from export.batch import export_batch, export_batch_pdf
from export.settings import ExportSettings
from qa.checks import run_qa
from qa.report import issues_to_dict
from render import spec_adapter
from render.loaders import load_layout
from render.renderer import _render
from app.api.routes_render import _adapt_spec, _adapt_theme_dict, _adapt_person

# Page configuration
st.set_page_config(
    page_title="Card Studio | ACM NIT Surat",
    page_icon="🪪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #64748B;
        font-size: 1.0rem;
        margin-bottom: 1.5rem;
    }
    .badge-card {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        background-color: #F8FAFC;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Title Banner
st.markdown('<div class="main-title">🪪 Card Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">ACM NIT Surat Hackathon ID Badge Studio — Code-built SVG badges with deterministic layout and print-ready export.</div>', unsafe_allow_html=True)

# Session State Initialization
if "brief" not in st.session_state:
    st.session_state.brief = None
if "is_mock_brief" not in st.session_state:
    st.session_state.is_mock_brief = True
if "people" not in st.session_state:
    st.session_state.people = []
if "drafts" not in st.session_state:
    st.session_state.drafts = []
if "selected_draft_idx" not in st.session_state:
    st.session_state.selected_draft_idx = 0

# Sidebar Navigation / Progress
st.sidebar.title("Navigation")
step = st.sidebar.radio(
    "Go to Step:",
    ["1. Event Brief", "2. Attendee Data", "3. Design Drafts", "4. Badge Preview", "5. Batch Export"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Engine Info**")
st.sidebar.caption("• Resolution: 300 DPI Vector/Raster\n• Canvas: 60 × 92 mm (3mm bleed)\n• Trim: 54 × 86 mm (ID-1)\n• Renderer: Deterministic SVG + OpenCV")

# ==========================================
# STEP 1: EVENT BRIEF
# ==========================================
if step == "1. Event Brief":
    st.header("Step 1: Event Brief & Requirements")
    st.write("Describe your event in plain English. The AI extractor extracts dates, venue, roles, and missing information.")

    default_prompt = (
        "SVNIT ACM Hackathon 2026. Dates: 10-12 October 2026. Venue: SVNIT Campus, Surat. "
        "Tagline: Code the Future. Roles: Participant, Organizer, Mentor."
    )
    brief_input = st.text_area("Event Description", value=default_prompt, height=120)

    col1, col2 = st.columns([1, 4])
    with col1:
        extract_clicked = st.button("Extract Brief ✨", type="primary")

    if extract_clicked or st.session_state.brief is not None:
        if extract_clicked:
            with st.spinner("Analyzing event brief..."):
                brief_obj, is_mock = extract_brief(brief_input)
                st.session_state.brief = brief_obj
                st.session_state.is_mock_brief = is_mock

        brief_obj = st.session_state.brief
        is_mock = st.session_state.is_mock_brief

        st.success("Brief Extracted Successfully!")
        status_col, mode_col = st.columns([2, 2])
        with status_col:
            st.metric("Event Name", brief_obj.event_name or "Not Specified")
        with mode_col:
            mode_label = "Offline Fallback Mode" if is_mock else "AI Extracted (Gemini)"
            st.metric("Extraction Engine", mode_label)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"**Dates:** {brief_obj.dates or '—'}")
        with c2:
            st.write(f"**Venue:** {brief_obj.venue or '—'}")
        with c3:
            st.write(f"**Tagline:** {brief_obj.tagline or '—'}")

        st.write(f"**Roles:** {', '.join(brief_obj.roles) if brief_obj.roles else 'participant, organizer, mentor'}")

        # Follow-up missing info
        missing = find_missing(brief_obj)
        if missing:
            st.info(f"Missing Details Detected: {', '.join(missing)}")
            questions = build_questions(missing)
            with st.expander("Answer Clarification Questions", expanded=False):
                for q in questions:
                    field = q["field"]
                    val = st.text_input(q["text"], value=str(q.get("default") or ""), key=f"q_{field}")
                    if val:
                        setattr(brief_obj, field, val)

# ==========================================
# STEP 2: ATTENDEE DATA
# ==========================================
elif step == "2. Attendee Data":
    st.header("Step 2: Attendee Roster Upload")
    st.write("Upload a CSV file of attendees or load sample fixtures. Automatically validates missing names, duplicate IDs, and unknown roles.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload CSV Roster", type=["csv"])
    with col2:
        st.write("Quick start:")
        if st.button("Load Sample Data (4 Attendees)"):
            st.session_state.people = [
                {"name": "Aarav Sharma", "role": "organizer", "id": "ORG-001", "team": "Core Exec", "photo": "photos/wide.png"},
                {"name": "Dr. Venkata Ramanathan Subramaniam", "role": "participant", "id": "PART-101", "team": "Algorithms", "photo": "photos/tall.png"},
                {"name": "Élodie Müller-François", "role": "mentor", "id": "MEN-050", "team": "AI Track", "photo": None},
                {"name": "Siddharth Das", "role": "volunteer", "id": "VOL-012", "team": "Logistics", "photo": None},
            ]
            st.success("Loaded 4 sample attendees!")

    if uploaded_file is not None:
        bytes_data = uploaded_file.read()
        load_result = load_people_csv(bytes_data)
        validation = validate_people(load_result.raw_rows)

        # Store valid people
        st.session_state.people = [p.model_dump() for p in validation.valid_people]

        # Display Validation Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Loaded Attendees", len(validation.valid_people))
        m2.metric("Missing Names", validation.issues.get("missing_names", 0))
        m3.metric("Unknown Roles", validation.issues.get("unknown_roles", 0))
        m4.metric("Duplicate IDs", validation.issues.get("duplicate_ids", 0))

        if validation.warnings:
            st.warning("**Validation Warnings:**\n" + "\n".join(f"- {w}" for w in validation.warnings[:5]))

    if st.session_state.people:
        st.subheader("Roster Preview")
        df = pd.DataFrame(st.session_state.people)
        st.dataframe(df, use_container_width=True)

# ==========================================
# STEP 3: DESIGN DRAFTS
# ==========================================
elif step == "3. Design Drafts":
    st.header("Step 3: Available Design Drafts")
    st.write("Select a design candidate generated deterministically from the catalog. Layout elements strictly use theme token colors.")

    if st.button("Generate Drafts", type="primary") or not st.session_state.drafts:
        brief_to_use = st.session_state.brief or Brief(event_name="SVNIT ACM Hackathon 2026")
        drafts_list, is_mock_d = generate_drafts(brief_to_use, count=3, allow_theme_variations=True)
        st.session_state.drafts = drafts_list

    drafts = st.session_state.drafts
    cols = st.columns(len(drafts))

    for idx, (col, draft) in enumerate(zip(cols, drafts)):
        with col:
            is_sel = st.session_state.selected_draft_idx == idx
            st.markdown(f"### Draft #{idx+1} {'(Selected)' if is_sel else ''}")
            st.write(f"**Layout:** `{draft.layout_name}`")
            st.write(f"**Theme:** `{draft.theme_name}`")
            st.write(f"**Primary Color:** `{draft.theme.colors.primary}`")

            # Swatches
            colors = draft.theme.colors.model_dump()
            swatch_html = "".join(
                f'<span style="display:inline-block;width:24px;height:24px;background-color:{v};border-radius:4px;margin-right:4px;border:1px solid #ccc;"></span>'
                for v in list(colors.values())[:5]
            )
            st.markdown(swatch_html, unsafe_allow_html=True)

            if st.button(f"Select Draft #{idx+1}", key=f"sel_draft_{idx}"):
                st.session_state.selected_draft_idx = idx
                st.rerun()

# ==========================================
# STEP 4: BADGE PREVIEW
# ==========================================
elif step == "4. Badge Preview":
    st.header("Step 4: Live Badge Preview")
    st.write("Deterministic SVG rendering directly from the backend engine. OpenCV face-aware crop and automated QA checks.")

    if not st.session_state.drafts:
        brief_to_use = st.session_state.brief or Brief(event_name="SVNIT ACM Hackathon 2026")
        st.session_state.drafts, _ = generate_drafts(brief_to_use, count=3, allow_theme_variations=True)

    people = st.session_state.people or [
        {"name": "Aarav Sharma", "role": "organizer", "id": "ORG-001", "team": "Core Exec", "photo": "photos/wide.png"}
    ]

    top_c1, top_c2 = st.columns([2, 1])
    with top_c1:
        attendee_names = [f"{p.get('name')} [{p.get('role', 'participant')}]" for p in people]
        selected_person_idx = st.selectbox("Select Attendee to Preview:", range(len(people)), format_func=lambda i: attendee_names[i])
    with top_c2:
        show_guides = st.checkbox("Show Print Guides (Bleed/Trim/Safe)", value=False)

    spec = st.session_state.drafts[st.session_state.selected_draft_idx]
    person_dict = people[selected_person_idx]
    person_obj = _adapt_person(Person(**person_dict))
    spec_adapted = _adapt_spec(spec)
    theme_dict = _adapt_theme_dict(spec)
    layout_dict = load_layout(spec.layout_name.lower())

    # Render SVG
    svg = _render(spec_adapted, person_obj, layout_dict, theme_dict)

    if show_guides:
        width, height, trim_x, trim_y, trim_width, trim_height = spec_adapter.canvas_geometry(spec_adapted)
        safe = spec_adapter.safe_inset(spec_adapted)
        guides = (
            f'<g id="debug-guides" stroke-dasharray="1 1" fill="none">\n'
            f'  <rect id="guide-bleed" x="0" y="0" width="{width:g}" height="{height:g}" stroke="#E11D48" stroke-width="0.3"/>\n'
            f'  <rect id="guide-trim" x="{trim_x:g}" y="{trim_y:g}" width="{trim_width:g}" height="{trim_height:g}" stroke="#10B981" stroke-width="0.3"/>\n'
            f'  <rect id="guide-safe" x="{trim_x + safe:g}" y="{trim_y + safe:g}" width="{trim_width - 2 * safe:g}" height="{trim_height - 2 * safe:g}" stroke="#3B82F6" stroke-width="0.3"/>\n'
            f'</g>'
        )
        if "</svg>" in svg:
            svg = svg.replace("</svg>", f"{guides}\n</svg>")

    # QA Checks
    issues = issues_to_dict(run_qa(spec_adapted, person_obj, svg, layout_dict, theme_dict))

    col_svg, col_qa = st.columns([3, 2])
    with col_svg:
        # Wrap SVG in container
        st.markdown(
            f'<div style="max-width:380px;margin:auto;box-shadow:0 10px 25px -5px rgba(0,0,0,0.1);border-radius:4px;overflow:hidden;background:white;">{svg}</div>',
            unsafe_allow_html=True,
        )
    with col_qa:
        st.subheader("Automated QA Diagnostics")
        if not issues:
            st.success("✓ All QA checks passed cleanly!")
        else:
            for iss in issues:
                sev = iss.get("severity")
                msg = f"**{iss.get('check')}**: {iss.get('message')}"
                if sev == "error":
                    st.error(msg)
                elif sev == "warning":
                    st.warning(msg)
                else:
                    st.info(msg)

        st.markdown("---")
        st.caption("**Print Specs:**\n• Canvas: 60 × 92 mm\n• Finished Trim: 54 × 86 mm (ID-1)\n• Safe Margin: 4 mm inset")

# ==========================================
# STEP 5: BATCH EXPORT
# ==========================================
elif step == "5. Batch Export":
    st.header("Step 5: Batch Render & Export")
    st.write("Generate high-resolution, print-ready files for all attendees in your roster.")

    if not st.session_state.drafts:
        brief_to_use = st.session_state.brief or Brief(event_name="SVNIT ACM Hackathon 2026")
        st.session_state.drafts, _ = generate_drafts(brief_to_use, count=3, allow_theme_variations=True)

    people = st.session_state.people or [
        {"name": "Aarav Sharma", "role": "organizer", "id": "ORG-001", "team": "Core Exec", "photo": "photos/wide.png"},
        {"name": "Dr. Venkata Ramanathan Subramaniam", "role": "participant", "id": "PART-101", "team": "Algorithms", "photo": "photos/tall.png"},
    ]

    spec = st.session_state.drafts[st.session_state.selected_draft_idx]
    people_adapted = [_adapt_person(Person(**p)) for p in people]
    spec_adapted = _adapt_spec(spec)
    theme_dict = _adapt_theme_dict(spec)
    layout_dict = load_layout(spec.layout_name.lower())

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        export_format = st.selectbox("Export Format", ["pdf", "png", "svg"], index=0)
    with exp_col2:
        export_dpi = st.selectbox("Resolution (DPI)", [300, 150], index=0)

    collate_pdf = False
    if export_format == "pdf":
        collate_pdf = st.checkbox("Collate into single multi-page PDF (1 page per attendee)", value=True)

    include_bleed = st.checkbox("Include 3mm print bleed (60 × 92 mm canvas)", value=True)

    settings = ExportSettings(
        format=export_format,
        dpi=export_dpi,
        orientation="portrait",
        bleed=include_bleed,
    )

    st.write(f"**Batch Overview:** {len(people)} attendees • Layout: `{spec.layout_name}` • Theme: `{spec.theme_name}`")

    if collate_pdf and export_format == "pdf":
        with st.spinner("Generating collated multi-page PDF..."):
            pdf_bytes = export_batch_pdf(spec_adapted, people_adapted, settings, layout=layout_dict, theme=theme_dict)
            st.download_button(
                label=f"📥 Download Collated PDF ({len(people)} Cards)",
                data=pdf_bytes,
                file_name="cards.pdf",
                mime="application/pdf",
                type="primary",
            )
    else:
        with st.spinner(f"Rendering batch and packing ZIP archive ({export_format.upper()})..."):
            zip_bytes = export_batch(spec_adapted, people_adapted, settings, layout=layout_dict, theme=theme_dict)
            st.download_button(
                label=f"📥 Download ZIP Archive ({export_format.upper()} Cards + Report)",
                data=zip_bytes,
                file_name=f"cards_{export_format}.zip",
                mime="application/zip",
                type="primary",
            )
