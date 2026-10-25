"""FastAPI application factory and CLI entry point (``caneca-server``)."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from caneca.api.routes import router
from caneca.api.security import SecurityMiddleware
from caneca.config import APP_VERSION, Settings, get_settings
from caneca.game.engine import Engine
from caneca.game.world import get_world
from caneca.persistence.db import Database
from caneca.services.games import GameService, ServiceError
from caneca.watchdog import watch_parent

log = logging.getLogger("caneca")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(settings.db_path)
        db.migrate(settings.backup_dir, settings.backups_to_keep)
        app.state.db = db
        app.state.games = GameService(db, Engine(get_world()), settings)
        app.state.log = log
        log.info("Caneca Quest %s — dados em %s", APP_VERSION, settings.data_dir)
        try:
            yield
        finally:
            db.dispose()

    app = FastAPI(
        title="Caneca Quest",
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=600,
    )
    app.add_middleware(SecurityMiddleware, settings=settings)

    @app.exception_handler(ServiceError)
    async def service_error(_req: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse({"error": {"code": exc.code, "detail": exc.detail}}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_req: Request, exc: RequestValidationError) -> JSONResponse:
        detail = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
        return JSONResponse({"error": {"code": "validation", "detail": detail}}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(_req: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected error", exc_info=exc)
        return JSONResponse({"error": {"code": "internal"}}, status_code=500)

    app.include_router(router)

    static = settings.static_dir
    if static and Path(static).is_dir():
        index = Path(static) / "index.html"
        app.mount("/assets", StaticFiles(directory=Path(static) / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:  # sync: filesystem checks run in the threadpool
            if path.startswith("api/"):
                raise ServiceError("not_found", 404)
            candidate = (Path(static) / path).resolve()
            if path and candidate.is_file() and Path(static).resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index)

    return app


def run() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Servidor do Caneca Quest")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--static-dir", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    overrides = {
        k: v
        for k, v in {
            "host": args.host,
            "port": args.port,
            "data_dir": args.data_dir,
            "static_dir": args.static_dir,
        }.items()
        if v is not None
    }
    if overrides:
        settings = settings.model_copy(update=overrides)
    logging.basicConfig(level=settings.log_level.upper(), format="%(levelname)s %(name)s: %(message)s")
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings),
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level,
            proxy_headers=False,
        )
    )
    parent = os.environ.get("CANECA_PARENT_PID", "")
    if parent.isdigit():
        watch_parent(int(parent), lambda: setattr(server, "should_exit", True))
    server.run()


if __name__ == "__main__":
    run()
