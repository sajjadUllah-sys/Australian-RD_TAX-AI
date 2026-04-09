"""
app.py — RDTI Compliance Review Agent
Streamlit frontend with two modes:
  1. Upload Document — AI extracts, fills gaps, scores, generates PDF
  2. Fill In Manually — AI chat interview, then generates PDF

Changes:
- Company info collected before project basics
- New/Continuing project toggle
- FY dropdown (not free text)
- Industry dropdown (mapped to ANZSIC internally)
- ABN validation with optional ABR lookup
- Session persistence via localStorage
- Session keep-alive to prevent timeouts
"""

import streamlit as st
import os
import json
import tempfile
import time
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="RDTI Compliance Review",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styling ────────────────────────────────────────────────────────────────────
_theme_base = st.get_option("theme.base")
_is_dark = (_theme_base == "dark") if _theme_base else True

_c = {
    "bg":               "#0e1117"              if _is_dark else "#f7f9fc",
    "card_bg":          "#1e2130"              if _is_dark else "#ffffff",
    "card_border":      "#2d3348"              if _is_dark else "#e0e8f5",
    "card_hover":       "rgba(78,139,230,0.2)" if _is_dark else "rgba(46,111,204,0.12)",
    "card_selected_bg": "#1c2a4a"              if _is_dark else "#eef4fd",
    "text_primary":     "#c5d5ea"              if _is_dark else "#1a3c6e",
    "text_secondary":   "#9ca3af"              if _is_dark else "#666666",
    "text_body":        "#e0e0e0"              if _is_dark else "#333333",
    "navbar_bg":        "#14243d"              if _is_dark else "#1a3c6e",
    "navbar_sub":       "#8ab0e0"              if _is_dark else "#8ab0e0",
    "pill_bg":          "#1c2a4a"              if _is_dark else "#eef4fd",
    "pill_text":        "#6ea8fe"              if _is_dark else "#2e6fcc",
    "progress_track":   "#2d3348"              if _is_dark else "#e0e8f5",
    "progress_fill":    "#4e8be6"              if _is_dark else "#2e6fcc",
    "chat_ai_bg":       "#1e2130"              if _is_dark else "#ffffff",
    "chat_ai_border":   "#2d3348"              if _is_dark else "#e0e8f5",
    "chat_ai_text":     "#e0e0e0"              if _is_dark else "#333333",
    "chat_user_bg":     "#1a3766"              if _is_dark else "#1a3c6e",
    "result_bg":        "#1e2130"              if _is_dark else "#ffffff",
    "result_border":    "#2d3348"              if _is_dark else "#e0e8f5",
    "bar_label":        "#b0b8c8"              if _is_dark else "#444444",
}

st.markdown(f"""
<style>
/* Page background */
[data-testid="stAppViewContainer"] {{ background: {_c['bg']}; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* Hide streamlit branding */
#MainMenu, footer {{ visibility: hidden; }}

/* Top nav bar */
.rdti-navbar {{
    background: {_c['navbar_bg']};
    padding: 14px 28px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.rdti-navbar h1 {{
    color: white;
    font-size: 20px;
    margin: 0;
    font-weight: 600;
}}
.rdti-navbar span {{
    color: {_c['navbar_sub']};
    font-size: 13px;
}}

/* Mode cards */
.mode-card {{
    background: {_c['card_bg']};
    border: 2px solid {_c['card_border']};
    border-radius: 12px;
    padding: 28px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}
.mode-card:hover {{
    border-color: {_c['progress_fill']};
    box-shadow: 0 4px 16px {_c['card_hover']};
}}
.mode-card.selected {{
    border-color: {_c['progress_fill']};
    background: {_c['card_selected_bg']};
}}
.mode-icon {{ font-size: 36px; margin-bottom: 10px; }}
.mode-title {{
    font-size: 16px;
    font-weight: 600;
    color: {_c['text_primary']};
    margin-bottom: 6px;
}}
.mode-desc {{
    font-size: 13px;
    color: {_c['text_secondary']};
}}

/* Score badge */
.score-badge {{
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 8px;
}}
.score-strong {{ background: #d4f0e0; color: #1a7a4a; }}
.score-likely {{ background: #dbeafe; color: #1a3c6e; }}
.score-risk {{ background: #fef3cd; color: #856404; }}
.score-unlikely {{ background: #fde8e8; color: #c0392b; }}

/* Chat bubbles */
.chat-user {{
    background: {_c['chat_user_bg']};
    color: white;
    padding: 10px 16px;
    border-radius: 16px 16px 4px 16px;
    margin: 6px 0 6px 60px;
    font-size: 14px;
    line-height: 1.5;
}}
.chat-ai {{
    background: {_c['chat_ai_bg']};
    color: {_c['chat_ai_text']};
    padding: 10px 16px;
    border-radius: 16px 16px 16px 4px;
    margin: 6px 60px 6px 0;
    font-size: 14px;
    line-height: 1.5;
    border: 1px solid {_c['chat_ai_border']};
}}
.stage-pill {{
    background: {_c['pill_bg']};
    color: {_c['pill_text']};
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 10px;
}}
.progress-bar-wrap {{
    background: {_c['progress_track']};
    border-radius: 8px;
    height: 8px;
    margin: 8px 0 16px;
}}
.progress-bar-fill {{
    background: {_c['progress_fill']};
    border-radius: 8px;
    height: 8px;
    transition: width 0.4s;
}}

/* Result card */
.rdti-result-card {{
    background: {_c['result_bg']};
    border-radius: 12px;
    padding: 24px;
    border: 1px solid {_c['result_border']};
    margin: 16px 0;
}}
.rdti-result-card h3 {{
    color: {_c['text_primary']};
    margin-top: 0;
}}
.rdti-bar-label {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: {_c['bar_label']};
    margin-bottom: 3px;
}}
.rdti-bar-label span:last-child {{
    font-weight: 600;
}}

/* ABN warning banner */
.abn-warning {{
    background: #fef3cd;
    border: 1px solid #ffc107;
    border-radius: 8px;
    padding: 12px 16px;
    color: #856404;
    font-size: 14px;
    margin: 8px 0;
}}
.abn-success {{
    background: #d4f0e0;
    border: 1px solid #1a7a4a;
    border-radius: 8px;
    padding: 12px 16px;
    color: #1a7a4a;
    font-size: 14px;
    margin: 8px 0;
}}

/* Session restore banner */
.session-restore-banner {{
    background: {_c['pill_bg']};
    border: 1px solid {_c['progress_fill']};
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
    color: {_c['text_primary']};
    font-size: 14px;
}}
</style>
""", unsafe_allow_html=True)


# ── Session persistence helpers ────────────────────────────────────────────────

def _inject_keep_alive_and_persistence():
    """Inject JS for session keep-alive pings and localStorage persistence."""
    import streamlit.components.v1 as components
    components.html("""
    <script>
    // ── Keep-alive: ping Streamlit every 60s to prevent WebSocket timeout ──
    (function() {
        if (window._rdtiKeepAlive) return;
        window._rdtiKeepAlive = true;
        setInterval(function() {
            // Touch the Streamlit connection to keep it alive
            try {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/_stcore/health', true);
                xhr.send();
            } catch(e) {}
        }, 60000);
    })();

    // ── Session timeout warning ──
    (function() {
        if (window._rdtiTimeoutWarn) return;
        window._rdtiTimeoutWarn = true;
        var lastActivity = Date.now();
        var WARN_AFTER_MS = 8 * 60 * 1000; // 8 minutes
        document.addEventListener('click', function() { lastActivity = Date.now(); });
        document.addEventListener('keypress', function() { lastActivity = Date.now(); });
        setInterval(function() {
            var idle = Date.now() - lastActivity;
            var banner = document.getElementById('rdti-timeout-warn');
            if (idle > WARN_AFTER_MS) {
                if (!banner) {
                    banner = document.createElement('div');
                    banner.id = 'rdti-timeout-warn';
                    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#fef3cd;color:#856404;padding:12px 20px;text-align:center;font-size:14px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.15);';
                    banner.innerHTML = '⚠️ Session may time out soon due to inactivity. Click anywhere or type to stay active. Your data is auto-saved.';
                    document.body.prepend(banner);
                }
            } else if (banner) {
                banner.remove();
            }
        }, 10000);
    })();
    </script>
    """, height=0)


def _save_session_to_localstorage(session_data: dict, chat_messages: list, mode: str):
    """Inject JS to save session state to localStorage."""
    import streamlit.components.v1 as components
    payload = json.dumps({
        "session": session_data,
        "chat_messages": chat_messages,
        "mode": mode,
        "timestamp": time.time(),
    })
    # Escape for JS string
    escaped = payload.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    components.html(f"""
    <script>
    try {{
        localStorage.setItem('rdti_session', '{escaped}');
    }} catch(e) {{}}
    </script>
    """, height=0)


def _inject_restore_check():
    """Inject JS that reads localStorage and writes to a hidden div for Streamlit to read."""
    import streamlit.components.v1 as components
    result = components.html("""
    <script>
    try {
        var saved = localStorage.getItem('rdti_session');
        if (saved) {
            var data = JSON.parse(saved);
            // Check if session is less than 24 hours old
            var age = (Date.now() / 1000) - (data.timestamp || 0);
            if (age < 86400) {
                // Send data back to Streamlit via query params trick
                document.getElementById('rdti-restore-data').innerText = saved;
            }
        }
    } catch(e) {}
    </script>
    <div id="rdti-restore-data" style="display:none;"></div>
    """, height=0)
    return result


def _clear_localstorage():
    """Inject JS to clear saved session from localStorage."""
    import streamlit.components.v1 as components
    components.html("""
    <script>
    try { localStorage.removeItem('rdti_session'); } catch(e) {}
    </script>
    """, height=0)


# ── Financial Year options ─────────────────────────────────────────────────────

def _get_fy_options():
    """Generate financial year options from FY2020-21 to FY2027-28."""
    options = []
    for start_year in range(2020, 2028):
        end_year = start_year + 1
        options.append(f"FY{start_year}-{str(end_year)[-2:]}")
    return options


# ── Navbar ─────────────────────────────────────────────────────────────────────
_business_display = st.session_state.get("company_name", "")
_navbar_subtitle = f"<span>{_business_display}</span>" if _business_display else "<span>Generate a compliance review report from your R&amp;D Tax Incentive plan</span>"
st.markdown(f"""
<div class="rdti-navbar">
    <h1>📋 RDTI Compliance Review</h1>
    {_navbar_subtitle}
</div>
""", unsafe_allow_html=True)

# Inject keep-alive and persistence JS
_inject_keep_alive_and_persistence()

# ── Session restore check ─────────────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = None

if "session_restored" not in st.session_state:
    st.session_state.session_restored = False

if "restore_offered" not in st.session_state:
    st.session_state.restore_offered = False

# On first load, check if there's a saved session
if not st.session_state.restore_offered and st.session_state.mode is None:
    _inject_restore_check()
    st.session_state.restore_offered = True
    # Since we can't synchronously read localStorage from Python,
    # we use a manual restore approach: save to session_state via a form
    if "pending_restore" not in st.session_state:
        st.session_state.pending_restore = False


# ── Mode selection ─────────────────────────────────────────────────────────────

if st.session_state.mode is None:
    st.markdown("### How would you like to start?")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="mode-card">
            <div class="mode-icon">📤</div>
            <div class="mode-title">Upload Document</div>
            <div class="mode-desc">Upload your existing R&D plan PDF.<br>AI extracts, fills gaps and scores it.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select Upload Mode", use_container_width=True, type="primary"):
            st.session_state.mode = "upload"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="mode-card">
            <div class="mode-icon">✏️</div>
            <div class="mode-title">Fill In Manually</div>
            <div class="mode-desc">Answer guided questions in a chat.<br>AI builds your report step by step.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select Manual Mode", use_container_width=True):
            st.session_state.mode = "manual"
            st.rerun()

    st.stop()


# ── Back button ────────────────────────────────────────────────────────────────
if st.button("← Back to start", key="back_btn"):
    _clear_localstorage()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1 — UPLOAD DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.mode == "upload":
    st.markdown("## 📤 Upload Your R&D Plan")
    st.markdown("Upload an existing R&D project plan PDF. The AI will extract all content, identify and fill gaps, score the claim, and generate a completed ATO-compliant report.")

    uploaded_file = st.file_uploader(
        "Upload R&D Plan (PDF)",
        type=["pdf"],
        help="Your existing RDTI project plan — prior year or current draft"
    )

    col1, col2 = st.columns(2)
    with col1:
        include_recs = st.toggle("Include AI recommendations", value=True)
    with col2:
        flag_incomplete = st.toggle("Flag incomplete sections", value=True)

    report_title = st.text_input("Report title", value="RDTI Compliance Review Report")

    if uploaded_file and st.button("🚀 Generate Report", type="primary", use_container_width=True):
        from scenario_upload import process_uploaded_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        progress = st.progress(0)
        status = st.status("Processing your document...", expanded=True)

        try:
            with status:
                st.write("📖 Extracting text from PDF...")
                progress.progress(15)
                time.sleep(0.3)

                st.write("🤖 Parsing structured data with AI...")
                progress.progress(35)

                result = process_uploaded_document(tmp_path, output_dir="outputs")
                progress.progress(70)

                st.write("📊 Scoring RDTI eligibility...")
                progress.progress(85)
                time.sleep(0.3)

                st.write("📄 Generating PDF report...")
                progress.progress(100)

            status.update(label="✅ Report generated successfully!", state="complete")

            data = result["data"]
            pdf_path = result["pdf_path"]
            scoring = data.get("scoring", {})

            total = scoring.get("total", 0)
            outcome = scoring.get("outcome", "")
            cls = "score-strong" if total >= 80 else "score-likely" if total >= 65 else "score-risk" if total >= 50 else "score-unlikely"

            st.markdown(f"""
            <div class="rdti-result-card">
                <h3>RDTI Eligibility Score</h3>
                <div class="score-badge {cls}">{total}/100 — {outcome}</div>
            """, unsafe_allow_html=True)

            breakdown = scoring.get("breakdown", [])
            if breakdown:
                for item in breakdown:
                    pct = int((item["score"] / item["max"]) * 100) if item["max"] else 0
                    st.markdown(f"""
                    <div style="margin:6px 0">
                        <div class="rdti-bar-label">
                            <span>{item['category']}</span>
                            <span>{item['score']}/{item['max']}</span>
                        </div>
                        <div class="progress-bar-wrap">
                            <div class="progress-bar-fill" style="width:{pct}%"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            gaps = scoring.get("gaps", [])
            if gaps and flag_incomplete:
                with st.expander(f"⚠️ {len(gaps)} gaps identified", expanded=False):
                    for g in gaps:
                        st.markdown(f"- {g}")

            recs = scoring.get("recommendations", [])
            if recs and include_recs:
                with st.expander("💡 Recommendations", expanded=False):
                    for r in recs:
                        st.markdown(f"- {r}")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )

        except Exception as e:
            status.update(label="❌ Error processing document", state="error")
            st.error(f"Something went wrong: {str(e)}")
        finally:
            os.unlink(tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2 — MANUAL CHAT INTERVIEW
# ══════════════════════════════════════════════════════════════════════════════

elif st.session_state.mode == "manual":
    from scenario_manual import RDTIInterviewSession, finalise_report
    from anzsic_mapping import INDUSTRY_OPTIONS, industry_to_anzsic, format_industry_display
    from abn_lookup import validate_and_lookup

    st.markdown("## ✏️ R&D Project Interview")
    st.markdown("Answer the AI's questions to build your complete RDTI report. Work through each section at your own pace.")

    # ── Business Name — first field the user sees ──────────────────────────────
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""

    business_name_input = st.text_input(
        "🏢 Business Name",
        value=st.session_state.company_name,
        placeholder="Enter your business / company name",
        key="business_name_field",
        help="This will be used as the company legal name throughout the report.",
    )
    # Persist immediately on change
    if business_name_input != st.session_state.company_name:
        st.session_state.company_name = business_name_input

    # Block the rest of the form until a business name is provided
    if not st.session_state.company_name.strip():
        st.info("👆 Please enter your business name above to begin the interview.")
        st.stop()

    # ── Initialise session (only after business name is set) ───────────────────
    if "interview_session" not in st.session_state:
        st.session_state.interview_session = RDTIInterviewSession()
        # Pre-fill company name so the AI doesn't ask for it again
        st.session_state.interview_session.collected_data["company_name"] = st.session_state.company_name
        st.session_state.chat_messages = []
        opening = st.session_state.interview_session.get_opening_message()
        st.session_state.chat_messages.append({"role": "assistant", "content": opening})
        st.session_state.abn_validated = False
        st.session_state.abn_result = None
        st.session_state.fy_selected = False
        st.session_state.industry_selected = False

    # Keep collected_data in sync if user edits the business name later
    if "interview_session" in st.session_state:
        st.session_state.interview_session.collected_data["company_name"] = st.session_state.company_name

    session: RDTIInterviewSession = st.session_state.interview_session

    # Progress indicator
    stage_labels = session.get_stage_labels()
    current_idx = min(session.stage_index, len(session.stages) - 1)
    progress_pct = int((current_idx / len(session.stages)) * 100)

    col_prog, col_stage = st.columns([3, 1])
    with col_prog:
        st.markdown(f"""
        <div class="progress-bar-wrap">
            <div class="progress-bar-fill" style="width:{progress_pct}%"></div>
        </div>
        """, unsafe_allow_html=True)
    with col_stage:
        label = stage_labels[current_idx] if current_idx < len(stage_labels) else "Complete"
        st.markdown(f'<span class="stage-pill">Step {current_idx + 1}/{len(session.stages)}: {label}</span>', unsafe_allow_html=True)

    # ── ABN validation after company_details stage ─────────────────────────────
    if (session.collected_data.get("abn")
            and session.collected_data.get("company_name")
            and not st.session_state.get("abn_validated")):
        with st.spinner("Validating ABN..."):
            abn_result = validate_and_lookup(
                session.collected_data["abn"],
                session.collected_data["company_name"],
            )
            st.session_state.abn_result = abn_result
            st.session_state.abn_validated = True

    # Show ABN validation result
    if st.session_state.get("abn_result"):
        result = st.session_state.abn_result
        if not result.get("format_ok"):
            st.markdown(f'<div class="abn-warning">❌ {result.get("error", "Invalid ABN format")}</div>', unsafe_allow_html=True)
        elif result.get("lookup_done"):
            name_match = result.get("name_match", {})
            if name_match and not name_match.get("match"):
                st.markdown(f'<div class="abn-warning">{name_match.get("message", "Name mismatch")}</div>', unsafe_allow_html=True)
            elif name_match and name_match.get("match"):
                st.markdown(f'<div class="abn-success">{name_match.get("message", "Name matches")}</div>', unsafe_allow_html=True)
        elif result.get("warning"):
            st.info(f"ℹ️ {result['warning']}")

    # ── FY & Industry dropdowns (shown at project_basics stage) ────────────────
    if session.current_stage == "project_basics" and not st.session_state.get("fy_selected"):
        st.markdown("---")
        st.markdown("#### 📅 Select Financial Year and Industry")
        st.markdown("*Please select these before continuing with the chat.*")

        col_fy, col_ind = st.columns(2)
        with col_fy:
            fy_options = _get_fy_options()
            # Default to a sensible year
            default_idx = fy_options.index("FY2024-25") if "FY2024-25" in fy_options else 4
            selected_fy = st.selectbox(
                "Financial Year",
                options=fy_options,
                index=default_idx,
                key="fy_dropdown",
            )

        with col_ind:
            selected_industry = st.selectbox(
                "Industry",
                options=["— Select industry —"] + INDUSTRY_OPTIONS,
                key="industry_dropdown",
            )

        if st.button("✅ Confirm FY & Industry", type="primary", use_container_width=True):
            if selected_industry == "— Select industry —":
                st.warning("Please select an industry.")
            else:
                session.collected_data["financial_year"] = selected_fy
                session.collected_data["industry"] = selected_industry
                session.collected_data["anzsic"] = industry_to_anzsic(selected_industry)
                st.session_state.fy_selected = True
                st.session_state.industry_selected = True
                st.rerun()

    # Also show dropdowns for continuing projects at continuing_updates stage
    if session.current_stage == "continuing_updates" and not st.session_state.get("fy_selected"):
        st.markdown("---")
        st.markdown("#### 📅 Select Financial Year for Updates")

        fy_options = _get_fy_options()
        default_idx = fy_options.index("FY2024-25") if "FY2024-25" in fy_options else 4
        selected_fy = st.selectbox(
            "Financial Year",
            options=fy_options,
            index=default_idx,
            key="fy_dropdown_cont",
        )

        if st.button("✅ Confirm Financial Year", type="primary", use_container_width=True):
            session.collected_data["financial_year"] = selected_fy
            st.session_state.fy_selected = True
            st.rerun()

    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                display = msg["content"].replace("[STAGE_COMPLETE]", "").strip()
                if display:
                    st.markdown(f'<div class="chat-user">{display}</div>', unsafe_allow_html=True)
            else:
                display = msg["content"].replace("[STAGE_COMPLETE]", "").split("<data>")[0].strip()
                if display:
                    st.markdown(f'<div class="chat-ai">{display}</div>', unsafe_allow_html=True)

    # Show generate button when at review stage or interview complete
    if session.interview_complete or session.current_stage == "review_and_score":
        st.success("✅ All information collected! You can generate your report now.")

        if session.collected_data:
            with st.expander("📋 Review Collected Data", expanded=False):
                st.json(session.collected_data)

        if st.button("🚀 Generate PDF Report", type="primary", use_container_width=True):
            session.interview_complete = True
            with st.spinner("Scoring your claim and generating PDF..."):
                try:
                    result = finalise_report(session, output_dir="outputs")
                    data = result["data"]
                    pdf_path = result["pdf_path"]
                    scoring = data.get("scoring", {})

                    total = scoring.get("total", 0)
                    outcome = scoring.get("outcome", "")
                    cls = "score-strong" if total >= 80 else "score-likely" if total >= 65 else "score-risk" if total >= 50 else "score-unlikely"

                    st.markdown(f"""
                    <div class="rdti-result-card">
                        <h3>Final Score</h3>
                        <div class="score-badge {cls}">{total}/100 — {outcome}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download PDF Report",
                            data=f.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                        )
                    # Clear localStorage on successful generation
                    _clear_localstorage()
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

        if not session.interview_complete:
            st.markdown("---")
            st.markdown("*💬 Or continue chatting to refine your answers before generating.*")

    # Chat input (only if interview not complete)
    if not session.interview_complete:
        # Block chat if FY/Industry not yet selected at project_basics stage
        if session.current_stage == "project_basics" and not st.session_state.get("fy_selected"):
            st.info("👆 Please select the Financial Year and Industry above before continuing.")
        elif session.current_stage == "continuing_updates" and not st.session_state.get("fy_selected"):
            st.info("👆 Please select the Financial Year above before continuing.")
        else:
            user_input = st.chat_input("Type your answer here...")
            if user_input:
                st.session_state.chat_messages.append({"role": "user", "content": user_input})
                with st.spinner("AI is thinking..."):
                    response = session.chat(user_input)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

                # Auto-generate opening message for new stage after transition
                if not session.interview_complete and "[STAGE_COMPLETE]" in response:
                    # Check if we need FY/Industry before next stage opens
                    if session.current_stage in ("project_basics", "continuing_updates"):
                        pass  # Will show dropdowns on rerun
                    else:
                        with st.spinner("Moving to next section..."):
                            next_opening = session.get_opening_message()
                        st.session_state.chat_messages.append({"role": "assistant", "content": next_opening})

                # Auto-save session to localStorage
                _save_session_to_localstorage(
                    session.to_dict(),
                    st.session_state.chat_messages,
                    "manual",
                )

                st.rerun()

    # Collected data sidebar
    with st.sidebar:
        # Always show business name at the top of the sidebar if set
        if st.session_state.get("company_name"):
            st.markdown(f"### 🏢 {st.session_state['company_name']}")
            st.divider()
        if session.collected_data:
            st.markdown("### 📊 Collected Data")
            st.markdown(f"**Activities found:** {len(session.collected_data.get('activities', []))}")
            if session.collected_data.get("project_title"):
                st.markdown(f"**Project:** {session.collected_data['project_title']}")
            if session.collected_data.get("financial_year"):
                st.markdown(f"**FY:** {session.collected_data['financial_year']}")
            if session.collected_data.get("industry"):
                st.markdown(f"**Industry:** {format_industry_display(session.collected_data['industry'])}")
            if session.collected_data.get("project_type"):
                st.markdown(f"**Type:** {session.collected_data['project_type'].title()}")
            st.json(session.collected_data, expanded=False)
