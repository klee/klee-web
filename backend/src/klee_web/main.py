from fastapi import FastAPI

from klee_web.api.admin import router as admin_router
from klee_web.api.health import router as health_router
from klee_web.api.jobs import router as jobs_router

app = FastAPI(
    title="KLEE Web",
    version="0.1.0",
    description="Browser-accessible KLEE symbolic execution.",
)

app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(admin_router)
