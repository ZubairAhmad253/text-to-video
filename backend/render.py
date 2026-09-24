"""Draw every frame with Pillow and pipe them into FFmpeg to encode the MP4."""
import os
import re
import shutil
import subprocess
from itertools import accumulate
from pathlib import Path

from PIL import Image

from .captions import make_caption, with_opacity
from .config import CAPTION_FADE, FADE_SECONDS, FPS, MAX_CLIP_STRETCH
from .motion import MOVES, prepare_base, render_frame


def ffmpeg_path() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    # winget installs FFmpeg here; PATH may not include it until Windows is restarted
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    matches = sorted(packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"))
    return str(matches[-1]) if matches else None


def _clip_seconds(ffmpeg: str, path: Path) -> float:
    info = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True).stderr
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    if not match:
        raise RuntimeError(f"Could not read the AI clip {path.name}.")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


class ClipFrames:
    """Stream an AI clip's frames at the video's size and FPS, filling `duration` seconds.

    A short clip is slowed down a little; if it is still too short, its last frame is held.
    """

    def __init__(self, ffmpeg: str, path: Path, size: tuple[int, int], duration: float):
        width, height = size
        stretch = min(MAX_CLIP_STRETCH, max(1.0, duration / _clip_seconds(ffmpeg, path)))
        vf = (f"setpts={stretch:.3f}*PTS,fps={FPS},"
              f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
              f"tpad=stop_mode=clone:stop_duration={duration:.2f}")
        self.size = size
        self.frame_bytes = width * height * 3
        self.last = None
        self.proc = subprocess.Popen([ffmpeg, "-loglevel", "error", "-i", str(path), "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def next(self) -> Image.Image | None:
        data = self.proc.stdout.read(self.frame_bytes)
        if len(data) == self.frame_bytes:
            self.last = Image.frombytes("RGB", self.size, data)
        return self.last

    def close(self) -> None:
        self.proc.kill()
        self.proc.wait()


def render_video(image_path: Path, scenes: list[str], durations: list[float], size: tuple[int, int],
                 caption_style: str, audio_path: Path | None, out_path: Path, on_progress,
                 clips: list[Path | None] | None = None) -> None:
    """Encode the video. Scenes with a clip in `clips` play that clip instead of the zoom/pan effect."""
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is not installed or not on PATH.")
    clips = clips or [None] * len(scenes)

    width, height = size
    base = prepare_base(image_path, size)
    captions = [make_caption(text, size, caption_style) for text in scenes]
    starts = [0.0, *accumulate(durations)]
    total = starts[-1]
    n_frames = max(1, round(total * FPS))
    black = Image.new("RGB", size)

    cmd = [ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-"]
    if audio_path:
        cmd += ["-i", str(audio_path), "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out_path)]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    scene = 0
    clip = ClipFrames(ffmpeg, clips[0], size, durations[0]) if clips[0] else None
    try:
        for i in range(n_frames):
            t = i / FPS
            while scene < len(durations) - 1 and t >= starts[scene + 1]:
                scene += 1
                if clip:
                    clip.close()
                clip = ClipFrames(ffmpeg, clips[scene], size, durations[scene]) if clips[scene] else None
            local_t = t - starts[scene]

            frame = clip.next() if clip else None
            if frame is None:
                frame = render_frame(base, size, MOVES[scene % len(MOVES)], local_t / durations[scene])
            else:
                frame = frame.copy()  # captions are pasted onto it; keep the held last frame clean

            caption, position = captions[scene]
            if local_t < CAPTION_FADE:
                caption = with_opacity(caption, local_t / CAPTION_FADE)
            frame.paste(caption, position, caption)

            edge = min(t, total - t)
            if edge < FADE_SECONDS:
                frame = Image.blend(black, frame, max(0.0, edge / FADE_SECONDS))

            proc.stdin.write(frame.tobytes())
            if i % FPS == 0:
                on_progress(i / n_frames)
        proc.stdin.close()
    except BrokenPipeError:
        pass  # FFmpeg exited early; its error message is reported below
    finally:
        if clip:
            clip.close()
    error = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg failed: {error.strip() or 'unknown error'}")
