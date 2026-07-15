from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from klee_web.deps import get_fleet_control, get_telemetry, get_usage_stats
from klee_web.jobs.telemetry import (
    CapacityAboveLimit,
    FleetControl,
    FleetTelemetry,
    WorkerControlRejected,
    WorkerUnavailable,
)
from klee_web.jobs.usage import UsageStatsStore
from klee_web.models import ErrorResponse, Telemetry, UsageStats, WorkerCapacityUpdate

router = APIRouter(prefix="/admin")


@router.get("/telemetry", response_model=Telemetry)
async def telemetry(fleet: Annotated[FleetTelemetry, Depends(get_telemetry)]) -> Telemetry:
    return await fleet.snapshot()


@router.get("/stats", response_model=UsageStats)
async def stats(usage: Annotated[UsageStatsStore, Depends(get_usage_stats)]) -> UsageStats:
    return await usage.snapshot()


@router.patch(
    "/workers/{worker_name}/capacity",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def set_worker_capacity(
    worker_name: str,
    update: WorkerCapacityUpdate,
    fleet: Annotated[FleetControl, Depends(get_fleet_control)],
) -> Response:
    try:
        await fleet.set_max_concurrency(worker_name, update.max_concurrency)
    except CapacityAboveLimit as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum worker capacity is {exc.maximum}",
        ) from exc
    except WorkerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Worker did not respond: {worker_name}",
        ) from exc
    except WorkerControlRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
