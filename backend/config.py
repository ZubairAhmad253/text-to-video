from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "uploads"   # temporary per-job working folders
OUTPUT_DIR = ROOT / "outputs"   # finished MP4 files
VOICES_DIR = ROOT / "voices"    # Piper voice models (*.onnx + *.onnx.json)
STATIC_DIR = ROOT / "static"    # the website (HTML/CSS/JS)

FPS = 24

# (width, height) for each format and quality
RESOLUTIONS = {
    "9:16": {"720": (720, 1280), "1080": (1080, 1920)},
    "16:9": {"720": (1280, 720), "1080": (1920, 1080)},
    "1:1": {"720": (720, 720), "1080": (1080, 1080)},
}

MAX_TEXT_CHARS = 2000
MAX_IMAGE_MB = 15

SCENE_GAP = 0.35       # silence (seconds) after each spoken sentence
END_PADDING = 0.8      # extra seconds on the last scene so the fade-out isn't rushed
FADE_SECONDS = 0.6     # fade from/to black at the start and end
CAPTION_FADE = 0.25    # caption fade-in time at the start of each scene

# Story mode: a local Ollama model writes the story, free Hugging Face Spaces animate a few scenes
OLLAMA_URL = "http://localhost:11434"
STORY_MODEL = "qwen2.5:3b"
STORY_SCENES = 8        # about 30 seconds of narration (the small model writes short sentences)
AI_CLIPS = 2            # scenes animated by AI per video; a free HF account gets about 2 clips a day
MAX_CLIP_SECONDS = 5.0  # longest clip requested from the animation model
MAX_CLIP_STRETCH = 1.4  # a clip may be slowed down this much to fill a longer scene
HF_TOKEN_FILE = ROOT / "hf_token.txt"  # optional; the HF_TOKEN environment variable also works

for folder in (UPLOAD_DIR, OUTPUT_DIR, VOICES_DIR):
    folder.mkdir(exist_ok=True)
