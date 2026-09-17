"""FastAPI gateway for the private Sovereign AI application."""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routes.attachments import router as attachments_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.health import router as health_router
from backend.api.routes.knowledge import router as knowledge_router
from backend.api.routes.models import router as models_router
from backend.api.routes.settings import router as settings_router
from backend.api.routes.tools import router as tools_router
from backend.core.config import PROJECT_ROOT, settings
from backend.core.logging import get_logger
from backend.db.database import init_db
from backend.services.ollama_service import ollama_service


logger = get_logger("sovereign.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    await ollama_service.start()
    warmup = asyncio.create_task(ollama_service.warm_up())
    logger.info(
        "Sovereign AI %s ready; Ollama=%s; database=%s",
        settings.app_version,
        settings.ollama_base_url,
        settings.sqlite_db_path,
    )
    try:
        yield
    finally:
        if not warmup.done():
            warmup.cancel()
        await ollama_service.close()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Private on-premise conversational AI gateway",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def secure_and_log(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api"):
            csp = "default-src 'none'; frame-ancestors 'none'"
        else:
            csp = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            )
        response.headers["Content-Security-Policy"] = csp
        logger.info(
            "%s %s -> %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": f"HTTP_{exc.status_code}"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "The request could not be validated.", "code": "VALIDATION_ERROR", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal local service error occurred.", "code": "INTERNAL_ERROR"},
        )

    for router in (
        health_router,
        models_router,
        conversations_router,
        attachments_router,
        knowledge_router,
        tools_router,
        settings_router,
        chat_router,
    ):
        app.include_router(router)

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
