"""
app.py — RDTI Compliance Review Agent
Streamlit frontend with two modes:
  1. Upload Document — AI extracts, fills gaps, scores, generates PDF
  2. Fill In Manually — AI chat interview, then generates PDF
"""

import streamlit as st
import os
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
st.markdown("""
<style>
/* Page background */
[data-testid="stAppViewContainer"] { background: #f7f9fc; }
[data-testid="stHeader"] { background: transparent; }

/* Hide streamlit branding */
#MainMenu, footer { visibility: hidden; }

/* Top nav bar */
.rdti-navbar {
    background: #1a3c6e;
    padding: 14px 28px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.rdti-navbar h1 {
    color: white;
    font-size: 20px;
    margin: 0;
    font-weight: 600;
}
.rdti-navbar span {
    color: #8ab0e0;
    font-size: 13px;
}

/* Mode cards */
.mode-card {
    background: white;
    border: 2px solid #e0e8f5;
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
}
.mode-card:hover { border-color: #2e6fcc; box-shadow: 0 4px 16px rgba(46,111,204,0.12); }
.mode-card.selected { border-color: #2e6fcc; background: #eef4fd; }
.mode-icon { font-size: 36px; margin-bottom: 10px; }
.mode-title { font-size: 16px; font-weight: 600; color: #1a3c6e; margin-bottom: 6px; }
.mode-desc { font-size: 13px; color: #666; }

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 8px;
}
.score-strong { background: #d4f0e0; color: #1a7a4a; }
.score-likely { background: #dbeafe; color: #1a3c6e; }
.score-risk { background: #fef3cd; color: #856404; }
.score-unlikely { background: #fde8e8; color: #c0392b; }

/* Chat bubbles */
.chat-user {
    background: #1a3c6e;
    color: white;
    padding: 10px 16px;
    border-radius: 16px 16px 4px 16px;
    margin: 6px 0 6px 60px;
    font-size: 14px;
    line-height: 1.5;
}
.chat-ai {
    background: white;
    color: #333;
    padding: 10px 16px;
    border-radius: 16px 16px 16px 4px;
    margin: 6px 60px 6px 0;
    font-size: 14px;
    line-height: 1.5;
    border: 1px solid #e0e8f5;
}
.stage-pill {
    background: #eef4fd;
    color: #2e6fcc;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 10px;
}
.progress-bar-wrap {
    background: #e0e8f5;
    border-radius: 8px;
    height: 8px;
    margin: 8px 0 16px;
}
.progress-bar-fill {
    background: #2e6fcc;
    border-radius: 8px;
    height: 8px;
    transition: width 0.4s;
}
</style>
""", unsafe_allow_html=True)


# ── Navbar ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rdti-navbar">
    <h1>📋 RDTI Compliance Review</h1>
    <span>Generate a compliance review report from your R&D Tax Incentive plan</span>
</div>
""", unsafe_allow_html=True)


# ── Mode selection ─────────────────────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = None

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

            # Score display
            total = scoring.get("total", 0)
            outcome = scoring.get("outcome", "")
            cls = "score-strong" if total >= 80 else "score-likely" if total >= 65 else "score-risk" if total >= 50 else "score-unlikely"

            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:24px;border:1px solid #e0e8f5;margin:16px 0">
                <h3 style="color:#1a3c6e;margin-top:0">RDTI Eligibility Score</h3>
                <div class="score-badge {cls}">{total}/100 — {outcome}</div>
            """, unsafe_allow_html=True)

            breakdown = scoring.get("breakdown", [])
            if breakdown:
                for item in breakdown:
                    pct = int((item["score"] / item["max"]) * 100) if item["max"] else 0
                    st.markdown(f"""
                    <div style="margin:6px 0">
                        <div style="display:flex;justify-content:space-between;font-size:13px;color:#444;margin-bottom:3px">
                            <span>{item['category']}</span>
                            <span style="font-weight:600">{item['score']}/{item['max']}</span>
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

            # Download
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
    from scenario_manual import RDTIInterviewSession, INTERVIEW_STAGES, finalise_report

    st.markdown("## ✏️ R&D Project Interview")
    st.markdown("Answer the AI's questions to build your complete RDTI report. Work through each section at your own pace.")

    # Initialise session
    if "interview_session" not in st.session_state:
        st.session_state.interview_session = RDTIInterviewSession()
        st.session_state.chat_messages = []
        opening = st.session_state.interview_session.get_opening_message()
        st.session_state.chat_messages.append({"role": "assistant", "content": opening})

    session: RDTIInterviewSession = st.session_state.interview_session

    # Progress indicator
    stage_labels = [
        "Project Basics", "Company Details", "Project Overview",
        "Core Activities", "Supporting Activities", "Recordkeeping", "Review"
    ]
    current_idx = min(session.stage_index, len(INTERVIEW_STAGES) - 1)
    progress_pct = int((current_idx / len(INTERVIEW_STAGES)) * 100)

    col_prog, col_stage = st.columns([3, 1])
    with col_prog:
        st.markdown(f"""
        <div class="progress-bar-wrap">
            <div class="progress-bar-fill" style="width:{progress_pct}%"></div>
        </div>
        """, unsafe_allow_html=True)
    with col_stage:
        label = stage_labels[current_idx] if current_idx < len(stage_labels) else "Complete"
        st.markdown(f'<span class="stage-pill">Step {current_idx + 1}/{len(INTERVIEW_STAGES)}: {label}</span>', unsafe_allow_html=True)

    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                # Strip internal markers for display
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

        # Show a summary of collected data
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
                    <div style="background:white;border-radius:12px;padding:20px;border:1px solid #e0e8f5;margin:12px 0">
                        <h3 style="color:#1a3c6e;margin-top:0">Final Score</h3>
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
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

        # Still allow chat for refining answers at review stage
        if not session.interview_complete:
            st.markdown("---")
            st.markdown("*💬 Or continue chatting to refine your answers before generating.*")

    # Chat input (only if interview not complete)
    if not session.interview_complete:
        user_input = st.chat_input("Type your answer here...")
        if user_input:
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            with st.spinner("AI is thinking..."):
                response = session.chat(user_input)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})

            # Auto-generate opening message for new stage after transition
            if not session.interview_complete and "[STAGE_COMPLETE]" in response:
                with st.spinner("Moving to next section..."):
                    next_opening = session.get_opening_message()
                st.session_state.chat_messages.append({"role": "assistant", "content": next_opening})

            st.rerun()

    # Collected data sidebar
    if session.collected_data:
        with st.sidebar:
            st.markdown("### 📊 Collected Data")
            st.markdown(f"**Activities found:** {len(session.collected_data.get('activities', []))}")
            if session.collected_data.get("project_title"):
                st.markdown(f"**Project:** {session.collected_data['project_title']}")
            if session.collected_data.get("company_name"):
                st.markdown(f"**Company:** {session.collected_data['company_name']}")
            st.json(session.collected_data, expanded=False)
