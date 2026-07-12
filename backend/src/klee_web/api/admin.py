from typing import Annotated

from fastapi import APIRouter, Depends

from klee_web.deps import get_telemetry, get_usage_stats
from klee_web.jobs.telemetry import FleetTelemetry
from klee_web.jobs.usage import UsageStatsStore
from klee_web.models import Telemetry, UsageStats

router = APIRouter(prefix="/admin")


@router.get("/telemetry", response_model=Telemetry)
async def telemetry(fleet: Annotated[FleetTelemetry, Depends(get_telemetry)]) -> Telemetry:
    return await fleet.snapshot()


@router.get("/stats", response_model=UsageStats)
async def stats(usage: Annotated[UsageStatsStore, Depends(get_usage_stats)]) -> UsageStats:
    return await usage.snapshot()
