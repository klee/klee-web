from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from .flag_allowlist import validate_extra_flags
from .symbolic_input import SymArgs, SymFiles, SymStdin


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


# The hard upper bound on a job's wall-clock, the ceiling the max_time flag is capped at.
# max_time is the whole job's budget: KLEE runs up to it, then per-path replay uses the
# leftover, so this bounds KLEE and replay together, not each separately.
MAX_TIME_CEILING = 600

# Cap on the free-text power-user flag string (ADR-0019).
EXTRA_FLAGS_MAX_LEN = 500


class KleeFlags(BaseModel):
    max_time: Annotated[int, Field(ge=1, le=MAX_TIME_CEILING)] = 60
    max_memory: Annotated[int, Field(ge=64, le=2048)] = 512
    query_format: QueryFormat = QueryFormat.none
    extra_flags: Annotated[str, Field(max_length=EXTRA_FLAGS_MAX_LEN)] = ""
    sym_stdin: SymStdin | None = None
    sym_files: SymFiles | None = None
    sym_args: SymArgs | None = None

    @field_validator("extra_flags")
    @classmethod
    def _validate_extra_flags(cls, v: str) -> str:
        return validate_extra_flags(v)


class JobRequest(BaseModel):
    source: Annotated[str, Field(min_length=1, max_length=64_000)]
    flags: KleeFlags = Field(default_factory=KleeFlags)


class SymbolicInput(BaseModel):
    name: str
    value: str  # default heuristic decode (little-endian int by size, else hex)
    bytes_hex: str  # raw ktest bytes, lowercase hex, so the frontend can re-decode to any type


class TestCase(BaseModel):
    __test__ = False  # opt out of pytest collection; this is a domain model, not a test class
    name: str
    inputs: list[SymbolicInput]
    error: str | None = None
    path_constraint: str | None = None
    program_output: str | None = None


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


class WorkerTelemetry(BaseModel):
    name: str
    concurrency: int  # pool size: jobs this Worker runs at once
    active: int  # jobs running now
    reserved: int  # jobs prefetched, not yet started


class QueueTelemetry(BaseModel):
    name: str
    depth: int  # jobs waiting in the broker, not yet on a Worker


class Telemetry(BaseModel):
    workers: list[WorkerTelemetry]
    queue: QueueTelemetry | None = None  # None: no queue (in-process) or unreadable
