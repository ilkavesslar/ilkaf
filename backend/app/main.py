import logging
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.cameras import router as cameras_router
from app.api.demo_observations import router as demo_observations_router
from app.api.detection import router as detection_router
from app.api.health import router as health_router
from app.api.lab_cameras import router as lab_cameras_router
from app.api.sites import router as sites_router
from app.api.status import router as status_router
from app.api.users import router as users_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.db import configure_database, create_schema_for_tests
from app.core.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, request_id_ctx
from app.models import (  # noqa: F401
    AuditLog,
    Camera,
    Organization,
    Role,
    Site,
    User,
    UserSiteAssignment,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(
        settings.log_level,
        settings.service_name,
        json_logs=settings.environment != "development",
    )
    logging.getLogger("ilka").info("Application started")
    if settings.environment == "production":
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required when ENVIRONMENT=production")
        settings.require_production_auth()
    configure_database(settings)
    if settings.environment == "testing" or settings.is_sqlite:
        await create_schema_for_tests()
    if settings.environment != "testing":
        root = str(Path(__file__).resolve().parents[2])
        if root not in sys.path:
            sys.path.insert(0, root)
        from cv.capabilities import schedule_capability_probe

        schedule_capability_probe()
    yield
    from app.services.person_preview import stop_all_person_previews

    stop_all_person_previews()
    logging.getLogger("ilka").info("Application shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ILKA — Intelligent Industrial Safety Monitoring Platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    cfg = get_settings()
    origins = cfg.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins) and "*" not in origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logging.getLogger("ilka.request").info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(health_router)
    app.include_router(status_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api")
    app.include_router(sites_router, prefix="/api")
    app.include_router(cameras_router, prefix="/api")
    app.include_router(demo_observations_router, prefix="/api")
    app.include_router(detection_router, prefix="/api")
    app.include_router(lab_cameras_router, prefix="/api")

    @app.get("/api/docs", include_in_schema=False)
    async def legacy_swagger_docs() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/api/redoc", include_in_schema=False)
    async def legacy_redoc() -> RedirectResponse:
        return RedirectResponse(url="/redoc")

    @app.get("/api/openapi.json", include_in_schema=False)
    async def legacy_openapi() -> RedirectResponse:
        return RedirectResponse(url="/openapi.json")

    if cfg.environment == "testing":

        @app.get("/__test/boom")
        async def _boom() -> None:
            raise RuntimeError("intentional test failure")

    return app


app = create_app()
