from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from klee_web.deps import get_readiness
from klee_web.health import Readiness

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "up"}


@router.get("/ready")
async def ready(readiness: Annotated[Readiness, Depends(get_readiness)]) -> JSONResponse:
    ok = await readiness.is_ready()
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready"},
    )
