"""Background jobs (downloads, speech recognition, translation, export) that
report progress to the interface while it polls /api/job."""
import threading
import traceback
import uuid

jobs = {}


def start(kind, work):
    """Run work(progress) in the background; progress(percent, detail) updates the job."""
    job_id = uuid.uuid4().hex[:10]
    job = jobs[job_id] = {"id": job_id, "kind": kind, "percent": 0, "detail": "Starting", "done": False,
                          "error": None, "result": None}

    def progress(percent, detail=None):
        if percent is not None:
            job["percent"] = int(percent)
        if detail:
            job["detail"] = detail

    def run():
        try:
            job["result"] = work(progress)
        except (ValueError, RuntimeError, IOError) as e:
            job["error"] = str(e)
        except Exception as e:
            traceback.print_exc()
            job["error"] = f"Something went wrong: {e}"
        job["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return job


def running(kind=None):
    return [j for j in jobs.values() if not j["done"] and (kind is None or j["kind"] == kind)]
