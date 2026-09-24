"""The full pipeline: text -> scenes -> voice -> (AI clips) -> frames -> MP4."""
import shutil
import traceback
from pathlib import Path

from .animate import QuotaExceeded, animate
from .config import AI_CLIPS, END_PADDING, MAX_CLIP_SECONDS, OUTPUT_DIR, RESOLUTIONS, SCENE_GAP
from .motion import prepare_base
from .render import render_video
from .story import write_story
from .text_split import split_into_scenes
from .tts import concat_wavs, synthesize


def _stage(progress, start: float, share: float):
    """Map a step's own 0..1 progress onto its slice [start, start + share] of the whole job."""
    return lambda fraction, step: progress(start + share * fraction, step)


def _animate_scenes(job_dir: Path, image_path: Path, actions: list[str], durations: list[float],
                    size: tuple[int, int], progress, notes: list[str]) -> list[Path | None]:
    """Animate up to AI_CLIPS scenes, spread through the story. Failed scenes stay None (zoom/pan)."""
    clips: list[Path | None] = [None] * len(actions)
    count = min(AI_CLIPS, len(actions))
    picks = [round(k * len(actions) / count) for k in range(count)]

    start_image = job_dir / "animate_start.jpg"
    prepare_base(image_path, size).save(start_image, quality=92)  # same shape as the video

    for n, index in enumerate(picks):
        progress(n / count, f"Animating scene {index + 1} with AI ({n + 1}/{count}), about 2-4 minutes")
        clip_path = job_dir / f"clip_{index}.mp4"
        try:
            animate(start_image, actions[index], min(MAX_CLIP_SECONDS, durations[index]), clip_path)
            clips[index] = clip_path
        except QuotaExceeded:
            notes.append("The free daily AI animation time on Hugging Face is used up, "
                         "so some scenes use the zoom effect instead. It resets 24 hours after first use.")
            break
        except Exception:
            traceback.print_exc()
            notes.append(f"AI animation failed for scene {index + 1}, so it uses the zoom effect instead.")
    return clips


def generate(job_dir: Path, image_path: Path, text: str, ratio: str, quality: str,
             voice: bool, style: str, story: bool, progress) -> tuple[Path, list[str]]:
    """Make the video. Returns (mp4 path, notes for the user about anything that was skipped)."""
    size = RESOLUTIONS[ratio][quality]
    notes: list[str] = []
    audio_path = None

    if story:
        progress(0.01, "Writing the story (1–2 minutes)")
        story_scenes = write_story(text)
        scenes = [s["narration"] for s in story_scenes]
        # shares of the progress bar: story 10%, voice 10%, AI clips 55%, render 25%
        voice_stage, render_stage = _stage(progress, 0.10, 0.10), _stage(progress, 0.75, 0.25)
    else:
        story_scenes = None
        scenes = split_into_scenes(text)
        voice_stage, render_stage = _stage(progress, 0, 0.25), _stage(progress, 0.25, 0.75)
        if not voice:
            render_stage = _stage(progress, 0, 1)

    if voice:
        wavs, durations = [], []
        for i, scene in enumerate(scenes):
            wav = job_dir / f"scene_{i}.wav"
            durations.append(synthesize(scene, wav) + SCENE_GAP)
            wavs.append(wav)
            voice_stage((i + 1) / len(scenes), f"Creating voice ({i + 1}/{len(scenes)})")
        audio_path = job_dir / "voice.wav"
        concat_wavs(wavs, SCENE_GAP, audio_path)
    else:
        # No narration: give each scene enough time to read its caption.
        durations = [max(2.5, len(scene.split()) * 0.4) + SCENE_GAP for scene in scenes]

    clips = None
    if story_scenes:
        clips = _animate_scenes(job_dir, image_path, [s["action"] for s in story_scenes], durations,
                                size, _stage(progress, 0.20, 0.55), notes)

    durations[-1] += END_PADDING
    out_path = OUTPUT_DIR / f"{job_dir.name}.mp4"
    render_video(image_path, scenes, durations, size, style, audio_path, out_path,
                 on_progress=lambda f: render_stage(f, "Rendering video"), clips=clips)

    shutil.rmtree(job_dir, ignore_errors=True)
    return out_path, notes
