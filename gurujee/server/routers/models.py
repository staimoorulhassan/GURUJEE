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
    """
    Obtain an AIClient instance for model catalogue queries.
    
    Attempts to return an AIClient attached to the application's gateway daemon (via request.app.state.gateway._soul_agent._ai_client). If no attached client is found, returns a fallback read-only AIClient configured to read the model catalogue from paths derived from the GURUJEE_CONFIG_DIR and GURUJEE_DATA_DIR environment variables (defaulting to "config" and "data"), i.e. models.yaml and user_config.yaml.
    
    Parameters:
        request (Request): FastAPI request used to access the application state.
    
    Returns:
        AIClient: An AIClient bound to the gateway daemon if available, otherwise a read-only AIClient configured for catalogue queries.
    """
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
    """
    Return the provider catalog of available AI model providers.
    
    The response content is a mapping with the following structure:
    
    {
      "builtin": { "<provider>": { "label": "...", "models": [...] } },
      "custom":  { "<provider>": { "label": "...", "base_url": "...", "models": [...] } },
      "default": { "primary": "...", "fallbacks": [...] }
    }
    
    Returns:
        JSONResponse: JSON response whose content is the provider catalogue described above,
        or an error object {"error": "<message>"} with HTTP status 500 on failure.
    """
    try:
        client = _get_ai_client(request)
        catalog = client.list_provider_catalog()
        return JSONResponse(content=catalog)
    except Exception as exc:
        logger.error("list_providers error: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})
