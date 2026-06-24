from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from klee_web.deps import get_dispatcher, get_job_store
from klee_web.jobs.dispatch import JobDispatcher
from klee_web.jobs.store import JobStore
from klee_web.models import Job, JobCreated, JobRequest, JobStatus

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreated)
async def create_job(
    request: JobRequest,
    store: Annotated[JobStore, Depends(get_job_store)],
    dispatcher: Annotated[JobDispatcher, Depends(get_dispatcher)],
) -> JobCreated:
    job = Job()
    await store.create(job)
    await dispatcher.dispatch(job.id, request)
    return JobCreated(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(
    job_id: UUID,
    store: Annotated[JobStore, Depends(get_job_store)],
) -> Job:
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post(
    "/jobs/{job_id}/cancel",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Job,
)
async def cancel_job(
    job_id: UUID,
    store: Annotated[JobStore, Depends(get_job_store)],
) -> Job:
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in (JobStatus.done, JobStatus.failed):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is already finished")
    await store.request_cancel(job_id)
    updated = await store.get(job_id)
    assert updated is not None  # store never drops a job that get() just returned
    return updated
