import os
import time
import requests
import streamlit as st

BASE_URL = os.environ.get("EXCELPPT_API", "http://localhost:8000")

st.set_page_config(page_title="CSV to PowerPoint Converter", page_icon="📊", layout="wide")

# ---------- Styles (to match your card-like UI) ----------
def gradient_card(text_top: str, text_bottom: str = "", height: int = 200):
    st.markdown(
        f"""
        <div style="
            border-radius: 18px;
            padding: 28px;
            height: {height}px;
            background: linear-gradient(135deg, rgba(216,180,254,0.35), rgba(253,232,239,0.6));
            border: 1px solid rgba(0,0,0,0.06);
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
            display:flex; flex-direction:column; justify-content:center; align-items:center;
            ">
            <div style="font-weight: 700; font-size: 22px; margin-bottom: 6px; color:#3b0764;">{text_top}</div>
            <div style="font-size:14px; color:#6b7280;">{text_bottom}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def soft_card(inner_html: str, padding=16):
    st.markdown(
        f"""
        <div style="
            border-radius: 18px;
            padding: {padding}px;
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        ">
            {inner_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- State ----------
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None
if "slides" not in st.session_state:
    st.session_state.slides = []
if "selected_slide" not in st.session_state:
    st.session_state.selected_slide = 0
if "status" not in st.session_state:
    st.session_state.status = "idle"

st.markdown(
    "<h2 style='margin-top:0;'>CSV to PowerPoint Converter</h2>",
    unsafe_allow_html=True,
)

left, mid, right = st.columns([1.2, 1, 1.4])

# ---------- Left: Upload ----------
with left:
    soft_card("<div style='font-weight:600; margin-bottom:10px;'>Upload CSV File</div>")
    uploaded = st.file_uploader(" ", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
   # Only upload once, not on every rerun
if uploaded is not None:
    if st.session_state.uploaded_name != uploaded.name:
        with st.spinner("Uploading..."):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            try:
                r = requests.post(f"{BASE_URL}/upload", files=files, timeout=60)
                r.raise_for_status()
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

            data = r.json()
            st.session_state.job_id = data["job_id"]
            st.session_state.uploaded_name = data["filename"]
            st.session_state.status = "pending"
            st.session_state.slides = []
            st.session_state.selected_slide = 0


    if st.session_state.uploaded_name:
        st.caption("Preview:")
        st.code(st.session_state.uploaded_name)

# ---------- Middle: Theme Selector & Sample ----------
with mid:
    soft_card("<div style='font-weight:600; margin-bottom:10px;'>Select Theme</div>")
    theme = st.selectbox(
        "Theme",
        ["Vibrant Colors", "Minimal Gray", "Blue Breeze", "Forest Mist"],
        index=0,
        label_visibility="collapsed",
    )
    st.caption("Theme Preview:")
    gradient_card("Sample Slide", f"Theme: {theme}", height=180)

# ---------- Right: Preview & Download ----------
with right:
    soft_card("<div style='font-weight:600; margin-bottom:10px;'>Preview</div>")
    placeholder = st.empty()
    btn_col = st.container()

    def poll_status(job_id: str, tries: int = 50, delay: float = 1.2):
        """Poll backend for job status. Stops early when ready."""
        for _ in range(tries):
            try:
                resp = requests.get(f"{BASE_URL}/status/{job_id}", timeout=20).json()
            except Exception:
                time.sleep(delay)
                continue

            if resp.get("status") == "ready":
                slides = resp.get("preview", {}).get("slides", [])
                st.session_state.slides = slides
                st.session_state.status = "ready"
                st.session_state.download_url = f"{BASE_URL}/download/{job_id}"
                return
            time.sleep(delay)
        st.session_state.status = "pending"  # still pending after polling window

    # Kick off polling automatically when we have a new pending job
    if st.session_state.job_id and st.session_state.status == "pending":
        with st.spinner("Generating PPT… (checking for output)"):
            poll_status(st.session_state.job_id)

    # Render the preview panel
    if st.session_state.status == "ready" and st.session_state.slides:
        slides = st.session_state.slides
        n = len(slides)
        idx = st.session_state.selected_slide

      # --- Slide navigation & preview ---
        slides = st.session_state.slides
        n = len(slides)

        # Navigation as radio (doesn't reset job_id)
        idx = st.radio(
            "Slides",
            options=list(range(n)),
            format_func=lambda i: f"Slide {i+1}",
            horizontal=True,
            index=st.session_state.selected_slide,
            key="slide_selector",
        )
        st.session_state.selected_slide = idx

        # Show selected slide
        slide = slides[idx]
        title = slide.get("title") or f"Slide {idx+1}"
        subtitle = slide.get("subtitle", "")
        gradient_card(title, subtitle, height=210)

        # Download
        st.download_button(
            "⬇️ Download PPT",
            data=requests.get(st.session_state.download_url, timeout=60).content,
            file_name=f"presentation_{st.session_state.job_id}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
        )


    elif st.session_state.status == "pending" and st.session_state.job_id:
        gradient_card("Waiting for PPT…", f"Job ID: {st.session_state.job_id}", height=210)
        st.info("We’re polling the output folder. As soon as your generator drops the PPT, the preview appears here automatically.")
    else:
        gradient_card("Data Presentation", "Upload a CSV/XLSX to begin", height=210)