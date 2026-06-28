from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    parsing = "parsing"
    done = "done"
    failed = "failed"


class HaltReason(StrEnum):
    completed = "completed"
    max_time = "max_time"
    cancelled = "cancelled"


class QueryFormat(StrEnum):
    none = "none"
    kquery = "kquery"


# The hard upper bound on a job's wall-clock. The Celery visibility timeout is sized
# at twice this (ADR-0018), so the two move together: raising it without raising the
# timeout brings back the concurrent-double-run hazard after a worker death.
MAX_TIME_CEILING = 300


class KleeFlags(BaseModel):
    max_time: Annotated[int, Field(ge=1, le=MAX_TIME_CEILING)] = 60
    max_memory: Annotated[int, Field(ge=64, le=2048)] = 512
    query_format: QueryFormat = QueryFormat.none


class JobRequest(BaseModel):
    source: Annotated[str, Field(min_length=1, max_length=64_000)]
    flags: KleeFlags = Field(default_factory=KleeFlags)


class TestCase(BaseModel):
    __test__ = False  # opt out of pytest collection; this is a domain model, not a test class
    name: str
    inputs: dict[str, str]
    error: str | None = None
    path_constraint: str | None = None


class JobResult(BaseModel):
    test_cases: list[TestCase]
    messages: str
    warnings: str
    stats: dict[str, int]
    program_output: str = ""
    compile_error: str | None = None
    halt_reason: HaltReason | None = None


class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: JobStatus = JobStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    result: JobResult | None = None
    cancel_requested: bool = Field(default=False, exclude=True)


class JobCreated(BaseModel):
    job_id: UUID
