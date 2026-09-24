import uuid
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image

from . import jobs
from .captions import STYLES
from .config import MAX_IMAGE_MB, MAX_TEXT_CHARS, OUTPUT_DIR, RESOLUTIONS, STATIC_DIR, UPLOAD_DIR
from .render import ffmpeg_path
from .story import ollama_available
from .text_split import split_into_scenes
from .tts import voice_available

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

app = FastAPI(title="Photo to Video")


@app.get("/api/health")
def health():
    return {"ffmpeg": ffmpeg_path() is not None, "voice": voice_available(), "story": ollama_available()}


@app.post("/api/generate")
async def create_video(
    image: UploadFile = File(...),
    text: str = Form(...),
    ratio: str = Form("9:16"),
    quality: str = Form("720"),
    style: str = Form("bold"),
    voice: bool = Form(True),
    story: bool = Form(False),
):
    text = text.strip()
    if ratio not in RESOLUTIONS:
        raise HTTPException(400, "Unknown format.")
    if quality not in RESOLUTIONS[ratio]:
        raise HTTPException(400, "Unknown quality.")
    if style not in STYLES:
        raise HTTPException(400, "Unknown caption style.")
    if not text or not split_into_scenes(text):
        raise HTTPException(400, "Please enter some text.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(400, f"Text is too long (max {MAX_TEXT_CHARS} characters).")

    data = await image.read()
    if len(data) > MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(400, f"Photo is too large (max {MAX_IMAGE_MB} MB).")
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except Exception:
        raise HTTPException(400, "That file is not a valid image.")
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(400, "Please upload a JPG, PNG or WebP photo.")

    if ffmpeg_path() is None:
        raise HTTPException(500, "FFmpeg is not installed on the server. See README.md.")
    if voice and not voice_available():
        raise HTTPException(400, "No voice model installed. Turn off voice-over or see README.md.")
    if story and not ollama_available():
        raise HTTPException(400, "Story mode needs Ollama running with the qwen2.5:3b model. See README.md.")

    job_id = uuid.uuid4().hex[:12]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir()
    image_path = job_dir / f"photo.{ALLOWED_FORMATS[fmt]}"
    image_path.write_bytes(data)

    jobs.submit(job_id, {"job_dir": job_dir, "image_path": image_path, "text": text,
                         "ratio": ratio, "quality": quality, "voice": voice, "style": style, "story": story})
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found (the server may have restarted).")
    return job


app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="site")
