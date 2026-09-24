"""Animate the photo with free image-to-video models hosted on Hugging Face Spaces (ZeroGPU).

Free GPU time is limited per account per day (about 2 clips on a free account), so callers
should expect QuotaExceeded and fall back to the zoom/pan effect.
"""
import os
from pathlib import Path

import httpx

from .config import HF_TOKEN_FILE


class QuotaExceeded(RuntimeError):
    pass


def hf_token() -> str | None:
    token = os.environ.get("HF_TOKEN")
    if not token and HF_TOKEN_FILE.exists():
        token = HF_TOKEN_FILE.read_text(encoding="utf-8").strip()
    return token or None


def _wan(client, image, prompt: str, seconds: float):
    video, _seed = client.predict(input_image=image, prompt=prompt, duration_seconds=seconds,
                                  api_name="/generate_video")
    return video


def _ltx(client, image, prompt: str, seconds: float):
    video, _seed = client.predict(prompt=prompt, input_image_filepath=image, mode="image-to-video",
                                  duration_ui=seconds, api_name="/image_to_video")
    return video.get("video", video) if isinstance(video, dict) else video


# Tried in order until one works. Wan 2.2 looks better; LTX-Video is the backup.
SPACES = [
    ("zerogpu-aoti/wan2-2-fp8da-aoti-faster", _wan),
    ("Lightricks/ltx-video-distilled", _ltx),
]


def _download(client, video, out_path: Path) -> None:
    url = video.get("url") if isinstance(video, dict) else video
    if not url:
        raise RuntimeError("the Space returned no video")
    if not str(url).startswith("http"):  # already a local file
        Path(out_path).write_bytes(Path(url).read_bytes())
        return
    with httpx.stream("GET", url, headers=client.headers, follow_redirects=True, timeout=180) as res:
        res.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in res.iter_bytes():
                f.write(chunk)


def animate(image_path: Path, prompt: str, seconds: float, out_path: Path) -> None:
    """Create an MP4 clip at `out_path` that starts from the photo and follows `prompt`."""
    from gradio_client import Client, handle_file
    from gradio_client.exceptions import AppError

    errors = []
    for space, call in SPACES:
        try:
            client = Client(space, token=hf_token(), verbose=False, download_files=False)
            video = call(client, handle_file(str(image_path)), prompt, seconds)
            _download(client, video, out_path)
            return
        except AppError as exc:
            if "quota" in str(exc).lower():
                raise QuotaExceeded(str(exc)) from exc  # the quota is per account, so other Spaces fail too
            errors.append(f"{space}: {exc}")
        except Exception as exc:
            errors.append(f"{space}: {exc}")
    raise RuntimeError("AI animation failed. " + " | ".join(errors))
