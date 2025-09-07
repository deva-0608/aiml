import streamlit as st
import requests
import json
from PIL import Image
import os

st.title("📊 Excel to PowerPoint Converter")

uploaded_file = st.file_uploader("Upload Excel/CSV File", type=["csv", "xlsx"])
if uploaded_file:
    response = requests.post("http://localhost:8000/upload", files={"file": uploaded_file})
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        st.success(f"✅ File uploaded. Job ID: `{job_id}`")

        info_response = requests.post("http://localhost:8000/info", json={"uuid": job_id})
        if info_response.status_code == 200:
            columns = info_response.json().get("columns", [])
            selected_cols = st.multiselect("📌 Select Important Columns", columns)
            theme = st.selectbox("🎨 Select Theme", ["Vibrant Colors", "Minimal", "Corporate", "Custom"])
            ppt_format = st.file_uploader("Upload PPT Format (optional)", type=["pptx"])

            if st.button("🚀 Generate Presentation") and selected_cols:
                input_json = {
                    "uuid": job_id,
                    "title": uploaded_file.name,
                    "theme": theme,
                    "location": f"storage/uploads/{job_id}",
                    "input_pptx": "input.pptx" if ppt_format else None,
                    "important_columns": selected_cols
                }

                with open(f"storage/uploads/{job_id}/input.json", "w") as f:
                    json.dump(input_json, f, indent=2)

                if ppt_format:
                    with open(f"storage/uploads/{job_id}/input.pptx", "wb") as f:
                        f.write(ppt_format.getbuffer())

                gen_response = requests.post("http://localhost:8000/generate", json={"uuid": job_id})
                if gen_response.status_code == 200:
                    st.success("✅ Presentation generated!")

                    status = requests.get(f"http://localhost:8000/status/{job_id}").json()
                    st.subheader("🖼️ Preview of First 4 Slides")
                    for i, slide in enumerate(status["preview"]["slides"][:4]):
                        st.markdown(f"**Slide {i+1}:** {slide['title']}")
                        st.markdown(f"*{slide['subtitle']}*")
                        img_path = slide.get("image_path")
                        if img_path and os.path.exists(img_path):
                            st.image(Image.open(img_path), caption=f"Slide {i+1}", use_column_width=True)

                    st.markdown(f"[📥 Download PPT]({status['download_url']})")