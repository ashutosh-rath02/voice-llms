import asyncio

import structlog
from fastapi import APIRouter, Request, Response, status

from app.core import db

router = APIRouter(tags=["health"])
log = structlog.get_logger()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: the process is up and serving requests.

    Deliberately checks nothing external — an orchestrator restarts the
    container when this fails, and a Postgres outage should not cause a
    restart loop.
    """
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict[str, str]:
    """Readiness probe: dependencies are reachable, traffic can be routed here.

    Returns 503 with per-dependency detail when something is down, so the
    deploy platform holds traffic and the dashboard can show what broke.
    """
    settings = request.app.state.settings
    timeout = settings.health_check_timeout_seconds
    checks: dict[str, str] = {}

    async def run_check(name: str, coro) -> None:
        try:
            await asyncio.wait_for(coro, timeout=timeout)
            checks[name] = "ok"
        except Exception as exc:
            checks[name] = "error"
            # repr, not str: TimeoutError's str() is empty, which logs nothing useful.
            log.warning("readiness_check_failed", component=name, error=repr(exc))

    await asyncio.gather(
        run_check("postgres", db.ping(request.app.state.db_engine)),
        run_check("redis", request.app.state.redis.ping()),
    )

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if all_ok else "degraded", **checks}
