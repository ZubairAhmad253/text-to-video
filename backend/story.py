"""Turn a short idea into a scene-by-scene story using a local Ollama model."""
import json
import urllib.error
import urllib.request

from .config import OLLAMA_URL, STORY_MODEL, STORY_SCENES

MIN_STORY_WORDS = 70  # about 27+ seconds of narration with the Piper voice
STORY_ATTEMPTS = 2

SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "minItems": STORY_SCENES,
            "maxItems": STORY_SCENES,
            "items": {
                "type": "object",
                "properties": {"narration": {"type": "string"}, "action": {"type": "string"}},
                "required": ["narration", "action"],
            },
        },
    },
    "required": ["scenes"],
}

PROMPT = """Write a short story for a 30-second video about the main character in the user's photo.

Idea: {idea}

Rules:
- Exactly {n} scenes, with a clear beginning, middle and a fun ending.
- narration: ONE sentence of 10 to 16 words, read aloud by a narrator.
- Only the character from the photo is ever on screen. Anyone else (for example the person on
  the phone) can be heard or talked about, but is never seen.
- action: what the camera sees in that scene, for an image-to-video model. Always name the main
  character, describe only visible movement (walking, turning, talking on a phone, waving...),
  and keep the same character and place as the photo. One short sentence.
"""


def ollama_available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as res:
            models = json.load(res).get("models", [])
    except (urllib.error.URLError, OSError, ValueError):
        return False
    return any(m.get("name") == STORY_MODEL for m in models)


def write_story(idea: str) -> list[dict]:
    """Return [{"narration": ..., "action": ...}, ...], one entry per scene.

    The small model sometimes writes very short sentences, which makes the video much shorter
    than 30 seconds, so a short story is rewritten (up to STORY_ATTEMPTS tries, longest kept).
    """
    best: list[dict] = []
    for _ in range(STORY_ATTEMPTS):
        scenes = _ask_for_story(idea)
        if _word_count(scenes) > _word_count(best):
            best = scenes
        if _word_count(best) >= MIN_STORY_WORDS:
            break
    return best


def _word_count(scenes: list[dict]) -> int:
    return sum(len(s["narration"].split()) for s in scenes)


def _ask_for_story(idea: str) -> list[dict]:
    body = {
        "model": STORY_MODEL,
        "messages": [{"role": "user", "content": PROMPT.format(idea=idea, n=STORY_SCENES)}],
        "format": SCHEMA,
        "stream": False,
        "options": {"temperature": 0.8},
    }
    request = urllib.request.Request(f"{OLLAMA_URL}/api/chat", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as res:
            content = json.load(res)["message"]["content"]
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach Ollama. Make sure the Ollama app is running.") from exc

    scenes = []
    for scene in json.loads(content).get("scenes", [])[:STORY_SCENES]:
        narration = " ".join(str(scene.get("narration", "")).split())
        action = " ".join(str(scene.get("action", "")).split())
        if narration:
            scenes.append({"narration": narration, "action": action or narration})
    if not scenes:
        raise RuntimeError("The story model returned an empty story. Please try again.")
    return scenes
