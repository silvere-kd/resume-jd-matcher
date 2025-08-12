# frontend/streamlit_app.py

import os
import json
import streamlit as st

from api_client import BackendClient

st.set_page_config(page_title="🧠 Resume ↔ JD Matcher", layout="wide")

# Backend URL (can be set via env BACKEND_URL)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
client = BackendClient(base_url=BACKEND_URL)

st.title("🧠 AI Resume ↔ Job Description Matcher")
st.caption(f"Backend: {BACKEND_URL}")

with st.expander("ℹ️ Instructions", expanded=False):
    st.markdown("""
    1) Upload **Resume** and **Job Description** (PDF or paste text).
    2) Click an action: **Run Matching**, **Enhance Resume**, or **Generate Cover Letter**.
    3) The app submits a job to the backend and waits for the result.
    """)

st.markdown("---")

col1, col2 = st.columns(2)

def extract_text_from_upload(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    # Delegate parsing to backend to keep logic consistent
    bytes_data = uploaded_file.read()
    return client.parse_pdf(bytes_data, filename=uploaded_file.name)

with col1:
    st.subheader("📄 Resume")
    resume_input = st.radio("Input method", ["Upload PDF", "Paste Text"], key="resume_method")
    resume_text = ""
    if resume_input == "Upload PDF":
        up_res = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="resume_pdf")
        if up_res:
            with st.spinner("Parsing resume PDF..."):
                try:
                    resume_text = extract_text_from_upload(up_res)
                except Exception as e:
                    st.error(f"Resume parsing failed: {e}")
    else:
        resume_text = st.text_area("Paste Resume Text", height=250, key="resume_textarea")

    if resume_text:
        with st.expander("🔍 Resume Preview"):
            st.text_area("Resume Text", resume_text, height=150, key="resume_preview")

with col2:
    st.subheader("📑 Job Description")
    jd_input = st.radio("Input method", ["Upload PDF", "Paste Text"], key="jd_method")
    jd_text = ""
    if jd_input == "Upload PDF":
        up_jd = st.file_uploader("Upload JD (PDF)", type=["pdf"], key="jd_pdf")
        if up_jd:
            with st.spinner("Parsing JD PDF..."):
                try:
                    jd_text = extract_text_from_upload(up_jd)
                except Exception as e:
                    st.error(f"JD parsing failed: {e}")
    else:
        jd_text = st.text_area("Paste JD Text", height=250, key="jd_textarea")

    if jd_text:
        with st.expander("🔍 JD Preview"):
            st.text_area("JD Text", jd_text, height=150, key="jd_preview")

st.markdown("---")

# Action buttons
disabled = not (resume_text and jd_text)
c1, c2, c3 = st.columns(3)
output = st.empty()

# Keep last job info in session_state for download links
if "last_job" not in st.session_state:
    st.session_state.last_job = {"id": None, "type": None, "result": None}

def _html_button(label: str, href: str):
    # Simple anchor styled like a button; works across Streamlit versions
    return f"""
    <a href="{href}" target="_blank" style="
        display: inline-block;
        text-decoration: none;
        background: #0f62fe;
        color: white;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid #0f62fe;
        text-align: center;
        width: 100%;
        ">
        {label}
    </a>
    """

def _render_downloads(job_id: str):
    st.markdown("### 📥 Download Result")
    url_pdf = client.download_url(job_id, "pdf")
    st.markdown(_html_button("⬇️ Download PDF", url_pdf), unsafe_allow_html=True)


def _run_job(job_type: str, resume: str, jd: str):
    with output.container():
        st.info(f"Submitting **{job_type}** job...")
        try:
            job_id = client.submit_job(job_type, resume, jd)
        except Exception as e:
            st.error(f"Failed to submit job: {e}")
            return

        st.success(f"Job submitted. ID: `{job_id}`")
        prog = st.progress(0)
        status_box = st.empty()

        def on_tick(elapsed, status):
            pct = min(100, int((elapsed / 60.0) * 100))  # scale progress to 60s
            prog.progress(pct)
            status_box.write(f"⏳ Elapsed: {int(elapsed)}s — Status: **{status}**")

        with st.spinner("Waiting for result..."):
            result = client.wait_with_progress(job_id, total_wait=180.0, poll_interval=1.5, on_tick=on_tick)

        prog.progress(100)
        st.write("")

        status = result.get("status")
        st.session_state.last_job = {"id": job_id, "type": job_type, "result": result}

        if status == "SUCCESS":
            st.success("✅ Job finished")

            # Minimal on-screen preview; full artifacts are downloadable
            payload = result.get("result") or {}
            with st.expander("👀 Quick Preview (raw result)", expanded=False):
                st.json(payload)

            _render_downloads(job_id)
        elif status == "FAILURE":
            st.error(f"❌ Job failed: {result.get('error')}")
        else:
            st.warning(f"Job ended in state {status}. Try again or check logs.")
        st.write("---")

with c1:
    if st.button("🚀 Run Matching", disabled=disabled, use_container_width=True):
        _run_job("match", resume_text, jd_text)

with c2:
    if st.button("📝 Enhance Resume", disabled=disabled, use_container_width=True):
        _run_job("enhance", resume_text, jd_text)

with c3:
    if st.button("✉️ Generate Cover Letter", disabled=disabled, use_container_width=True):
        _run_job("cover_letter", resume_text, jd_text)

# If a job already completed this session, show its download buttons again at the bottom
if st.session_state.last_job.get("id"):
    st.markdown("---")
    st.markdown("### Last job downloads")
    _render_downloads(st.session_state.last_job["id"])
