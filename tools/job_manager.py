from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from queue import Queue, Empty


@dataclass
class Job:
    id: str
    created_at: float = field(default_factory=time.time)
    queue: Queue = field(default_factory=Queue)  # progress events
    done: bool = False
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(self) -> Job:
        jid = str(uuid.uuid4())
        job = Job(id=jid)
        self._jobs[jid] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def emit(self, job_id: str, event: Dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.queue.put(event)

    def set_result(self, job_id: str, result: Dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.result = result
        job.done = True
        job.queue.put({"type": "done", "ts": time.time()})

    def set_error(self, job_id: str, message: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.error = message
        job.done = True
        job.queue.put({"type": "error", "message": message, "ts": time.time()})
        job.queue.put({"type": "done", "ts": time.time()})


JOB_MANAGER = JobManager()
