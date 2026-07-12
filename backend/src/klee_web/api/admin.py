from typing import Annotated

from fastapi import APIRouter, Depends

from klee_web.deps import get_telemetry
from klee_web.jobs.telemetry import FleetTelemetry
from klee_web.models import Telemetry

router = APIRouter(prefix="/admin")


@router.get("/telemetry", response_model=Telemetry)
async def telemetry(fleet: Annotated[FleetTelemetry, Depends(get_telemetry)]) -> Telemetry:
    return await fleet.snapshot()
