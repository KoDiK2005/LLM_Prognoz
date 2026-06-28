from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.forecasts import router as forecasts_router
from app.api.health import router as health_router
from app.core.config import settings
from app.services.queue import close_queue
from app.services.rate_limit import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_queue()
    await close_redis()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(forecasts_router, prefix="/api/v1")
