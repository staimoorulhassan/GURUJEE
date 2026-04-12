"""GET /agents endpoint (T035)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/agents")
async def agents(request: Request) -> JSONResponse:
    """Return a snapshot of all agent states."""
    gateway = request.app.state.gateway
    result = [
        {
            "name": name,
            "status": state.status.name,
            "restart_count": state.restart_count,
            "last_error": state.last_error,
        }
        for name, state in gateway.agent_states.items()
    ]
    return JSONResponse(result)
