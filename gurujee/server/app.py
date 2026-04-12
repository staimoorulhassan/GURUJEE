"""FastAPI application factory for GURUJEE server (T032)."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from gurujee.daemon.gateway_daemon import GatewayDaemon

logger = logging.getLogger(__name__)
_STATIC_DIR = Path(__file__).parent / "static"


def _setup_server_log() -> None:
    """Attach a RotatingFileHandler for server access/error logs."""
    data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "server.log"
    try:
        h = RotatingFileHandler(str(log_path), maxBytes=5_242_880, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        # Attach to both our logger and uvicorn's
        for name in ("gurujee.server", "uvicorn", "uvicorn.error", "uvicorn.access"):
            logging.getLogger(name).addHandler(h)
    except OSError as exc:
        logger.warning("Could not attach server log handler: %s", exc)


def create_app(gateway: "GatewayDaemon") -> FastAPI:
    """Create and configure the FastAPI app.

    *gateway* is injected into each router via app.state so handlers can
    publish/subscribe messages without an import cycle.
    """
    app = FastAPI(title="GURUJEE", version="1.0.0")

    _setup_server_log()

    # Security: only allow requests from localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:7171", "http://localhost:7171"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Attach gateway so routers can access it via request.app.state.gateway
    app.state.gateway = gateway

    # Register routers
    from gurujee.server.routers.health import router as health_router
    from gurujee.server.routers.chat import router as chat_router
    from gurujee.server.routers.agents import router as agents_router
    from gurujee.server.routers.automate import router as automate_router
    from gurujee.server.routers.notifications import router as notifications_router

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(agents_router)
    app.include_router(automate_router)
    app.include_router(notifications_router)

    # WebSocket endpoint
    from gurujee.server.websocket import router as ws_router
    app.include_router(ws_router)

    # T071 — global exception handler: never crash daemon on bad request
    @app.exception_handler(Exception)
    async def _global_exception_handler(req: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error for %s %s", req.method, req.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "done": True},
        )

    # Serve PWA static files at /static; also serve index.html at /
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

        from fastapi.responses import FileResponse

        @app.get("/")
        async def serve_index() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

        @app.get("/{filename:path}")
        async def serve_static(filename: str) -> FileResponse:
            base_dir = _STATIC_DIR.resolve()
            try:
                target = (base_dir / filename).resolve()
                target.relative_to(base_dir)
            except (ValueError, OSError):
                return FileResponse(str(base_dir / "index.html"))

            if target.exists() and target.is_file():
                return FileResponse(str(target))
            return FileResponse(str(base_dir / "index.html"))

    return app
