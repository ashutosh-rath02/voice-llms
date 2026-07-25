from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.voice import router as voice_router
from app.core import db
from app.core.config import get_settings
from app.core.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared clients at startup, close them cleanly at shutdown.

    Anything stored on app.state here is one instance per process (one
    connection pool, one Redis client) shared by all requests.
    """
    settings = get_settings()
    app.state.settings = settings
    app.state.db_engine = db.create_engine(settings)
    app.state.db_sessions = db.create_session_factory(app.state.db_engine)
    app.state.redis = aioredis.from_url(settings.redis_url)
    log.info("startup", app=settings.app_name, env=settings.app_env)

    yield

    await app.state.redis.aclose()
    await app.state.db_engine.dispose()
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.app_env != "dev")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    # Health endpoints stay unversioned: infra probes shouldn't break on API v2.
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(voice_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    return app


app = create_app()
