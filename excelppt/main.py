import os, json, uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from info import extract_columns
from worker import generate_ppt

STORAGE_ROOT = "storage"
UPLOADS_DIR = os.path.join(STORAGE_ROOT, "uploads")
OUTPUTS_DIR = os.path.join(STORAGE_ROOT, "outputs")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = FastAPI(title="Excel→PPT Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def job_dirs(job_id: str):
    return os.path.join(UPLOADS_DIR, job_id), os.path.join(OUTPUTS_DIR, job_id)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Only CSV or Excel files are supported.")

    job_id = str(uuid.uuid4())[:8]
    up_dir, out_dir = job_dirs(job_id)
    os.makedirs(up_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    input_path = os.path.join(up_dir, f"input{ext}")
    with open(input_path, "wb") as f:
        f.write(await file.read())

    metadata = {
        "uuid": job_id,
        "title": file.filename,
        "location": up_dir,
        "important_columns": [],
        "theme": "Default",
        "input_pptx": None
    }
    with open(os.path.join(up_dir, "input.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    return {"job_id": job_id, "filename": file.filename}

@app.post("/info")
async def info_endpoint(req: Request):
    data = await req.json()
    uuid = data["uuid"]
    upload_dir = os.path.join(UPLOADS_DIR, uuid)
    columns = extract_columns(upload_dir)
    return {"columns": columns}

@app.post("/generate")
async def generate_endpoint(req: Request):
    data = await req.json()
    uuid = data["uuid"]
    generate_ppt(uuid)
    return {"status": "success"}

@app.get("/status/{job_id}")
def job_status(job_id: str):
    preview_path = os.path.join(OUTPUTS_DIR, job_id, "preview.json")
    if not os.path.exists(preview_path):
        return {"status": "pending", "job_id": job_id}
    with open(preview_path) as f:
        preview = json.load(f)
    return {
        "status": "ready",
        "job_id": job_id,
        "slide_count": len(preview.get("slides", [])),
        "preview": preview,
        "download_url": f"/download/{job_id}"
    }

@app.get("/download/{job_id}")
def download(job_id: str):
    ppt_path = os.path.join(OUTPUTS_DIR, job_id, "presentation.pptx")
    if not os.path.exists(ppt_path):
        raise HTTPException(status_code=404, detail="Presentation not found.")
    return FileResponse(ppt_path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=f"presentation_{job_id}.pptx")