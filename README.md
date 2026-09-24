# Photo to Video

A small website that turns **one photo + some text** into an MP4 video. It is free and runs fully offline, with no paid APIs.

- Each sentence becomes a **scene**: the photo slowly zooms or pans, and the sentence appears as a caption.
- An offline voice (Piper TTS) reads the text aloud. You can turn this off.
- **AI story mode** (optional): describe an idea, e.g. *"the panda walks in the jungle talking to a friend on a mobile phone"*. A local AI (Ollama) writes an 8-scene story of about 30 seconds, and **2 scenes are animated by a free AI video model**, so the photo really moves. The other scenes use the zoom effect.
- Formats: 9:16 (Reels/Shorts), 16:9 (YouTube) and 1:1, in 720p or 1080p.

## One-time setup (Windows)

1. **Install FFmpeg.** Open PowerShell and run:
   ```
   winget install Gyan.FFmpeg
   ```
   Close and reopen the terminal, then check it works with `ffmpeg -version`.
2. **Python 3.11–3.13.** Check with `python --version`. If `pip install` fails later on 3.13, install 3.12 with `winget install Python.Python.3.12`.
3. **Double-click `setup.bat`.** It creates `venv/`, installs the packages and downloads the English voice into `voices/`.

## Run

Double-click **`run.bat`**. It opens http://localhost:8000 in your browser. Keep the black window open while you use the site; close it to stop the server.

## Share online (free)

With `run.bat` running, double-click **`share.bat`**. It prints a public link like `https://something.trycloudflare.com` that anyone can open. The link works only while your PC, `run.bat` and the `share.bat` window are all on. You get a new link each time you start it.

## Showcase site (Vercel, free)

Vercel hosts a **static showcase copy** of the website. `vercel.json` publishes only the `static/` folder, and `.vercelignore` leaves out the Python code. The showcase has no server, so it can't make videos. When the page can't reach a server, it switches to showcase mode: a banner explains this, the controls are turned off, and a screen recording of the real app (`static/samples/demo.mp4`) plays along with sample videos.

To host the real generator online, use the included `Dockerfile` on any Docker host, such as Render, Railway, a VPS, or a Hugging Face Space (Docker Spaces need HF PRO).

## How it works

```
browser --(photo + text + options)--> POST /api/generate --> job queue (1 worker)
  1. split the text into scenes (one per sentence)
  2. Piper speaks each scene into a WAV, which sets the scene's length
  3. Pillow draws every frame: moving crop of the photo + caption + fades
  4. the frames are piped into FFmpeg, which adds the voice track and encodes the MP4
browser polls GET /api/status/{id} --> shows the video from /outputs/<id>.mp4
```

| File | Purpose |
|---|---|
| `backend/main.py` | Web server, upload checks, API routes |
| `backend/jobs.py` | Background queue and progress tracking |
| `backend/generator.py` | The full pipeline for one video |
| `backend/text_split.py` | Splits the text into scenes |
| `backend/tts.py` | Piper voice-over and WAV joining |
| `backend/motion.py` | Zoom/pan camera movement |
| `backend/captions.py` | Caption styles |
| `backend/render.py` | Frame loop and FFmpeg encoding, and plays AI clips inside scenes |
| `backend/story.py` | Writes the story with Ollama (story mode) |
| `backend/animate.py` | Animates scenes with free Hugging Face Spaces (story mode) |
| `backend/config.py` | Resolutions, timings, folders |
| `static/` | The website |

## AI story mode

Story mode uses two free services:

- **Ollama** runs the story writer (`qwen2.5:3b`) on your own computer. `setup.bat` installs it. The Ollama app must be running, and it starts by itself when Windows starts.
- **Hugging Face Spaces** animate the photo using Wan 2.2, with LTX-Video as a backup. This needs the internet and is limited by free daily GPU time:

| Account | Free GPU time per day | AI clips per day |
|---|---|---|
| No account | 2 min | about 1 |
| Free account + token | 5 min | about 2 (one story video) |
| PRO ($9/month) | 40 min | about 18 |

To use your free account, create a **Read** token at https://huggingface.co/settings/tokens and paste it into a file named `hf_token.txt` in this folder. When the daily time runs out, the video is still made and those scenes use the zoom effect. The page shows a note when that happens. The time resets 24 hours after you first use it.

Tips:
- Use a photo in the same shape as the video, such as a landscape photo for 16:9, so the character stays large in the AI scenes.
- A story video takes about 5–8 minutes. Most of that is the AI animation.
- To animate more or fewer scenes, change `AI_CLIPS` in `backend/config.py`.

## Changing the voice

Download any English voice (`.onnx` + `.onnx.json`) from https://huggingface.co/rhasspy/piper-voices/tree/main/en into `voices/`. The app uses the first `.onnx` file alphabetically, so remove the old one. Good choices: `en_US-ryan-medium` (male), `en_GB-alba-medium` (British).

## Notes

- Finished videos stay in `outputs/`. Delete old ones when you like.
- The project is on your OneDrive Desktop, so OneDrive will sync `venv/` and your videos. To avoid that, move the folder somewhere like `C:\Projects\`, or pause OneDrive syncing.
