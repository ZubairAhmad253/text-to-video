"""A tiny in-memory job queue. One worker thread renders videos one at a time."""
import queue
import threading
import traceback

from .generator import generate

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_queue: queue.Queue = queue.Queue()


def submit(job_id: str, params: dict) -> None:
    with _lock:
        _jobs[job_id] = {"status": "queued", "progress": 0, "step": "Waiting in queue",
                         "video_url": None, "error": None, "notes": []}
    _queue.put((job_id, params))


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update(job_id: str, **fields) -> None:
    with _lock:
        _jobs[job_id].update(fields)


def _worker() -> None:
    while True:
        job_id, params = _queue.get()
        _update(job_id, status="running", step="Starting")
        try:
            out, notes = generate(**params, progress=lambda p, step: _update(job_id, progress=round(p * 100), step=step))
            _update(job_id, status="done", progress=100, step="Done", video_url=f"/outputs/{out.name}", notes=notes)
        except Exception as exc:
            traceback.print_exc()
            _update(job_id, status="error", error=str(exc))
        finally:
            _queue.task_done()


threading.Thread(target=_worker, daemon=True).start()
