from fastapi import FastAPI

from klee_web.api.jobs import router as jobs_router

app = FastAPI(
    title="KLEE Web",
    version="0.1.0",
    description="Browser-accessible KLEE symbolic execution.",
)

app.include_router(jobs_router)
