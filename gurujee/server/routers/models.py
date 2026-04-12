"""Models router — GET /api/models/providers (ADR-005)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gurujee.ai.client import AIClient
from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


def _get_ai_client(request: Request) -> AIClient:
    """Resolve AIClient from the gateway daemon attached to app.state."""
    gateway = getattr(request.app.state, "gateway", None)
    if gateway is not None:
        soul = getattr(gateway, "_soul_agent", None)
        if soul is not None and hasattr(soul, "_ai_client"):
            return soul._ai_client  # type: ignore[return-value]
    # Fallback: construct a read-only client for catalog queries
    config_dir = Path(os.environ.get("GURUJEE_CONFIG_DIR", "config"))
    data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
    return AIClient(
        models_config_path=config_dir / "models.yaml",
        user_config_path=data_dir / "user_config.yaml",
    )


@router.get("/providers")
async def list_providers(request: Request) -> JSONResponse:
    """Return the full provider catalogue from config/models.yaml.

    Response shape:
    ```json
    {
      "builtin": { "<provider>": { "label": "...", "models": [...] } },
      "custom":  { "<provider>": { "label": "...", "base_url": "...", "models": [...] } },
      "default": { "primary": "...", "fallbacks": [...] }
    }
    ```
    """
    try:
        client = _get_ai_client(request)
        catalog = client.list_provider_catalog()
        return JSONResponse(content=catalog)
    except Exception as exc:
        logger.error("list_providers error: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})
