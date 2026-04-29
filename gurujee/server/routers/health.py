"""GET /health endpoint (T034, T072)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> JSONResponse:
    """Return daemon readiness, per-agent status, and optional warnings.

    T072: if Shizuku is unavailable, add ``"shizuku_inactive"`` to *warnings*.
    The daemon is still fully usable for chat without Shizuku.
    """
    gateway = request.app.state.gateway
    if not gateway.ready:
        return JSONResponse({"status": "starting"})

    agent_statuses = {
        name: state.status.name
        for name, state in gateway.agent_states.items()
    }
    response: dict[str, Any] = {"status": "ready", "agents": agent_statuses}
    warnings: list[str] = []

    # Surface any crashed agents as non-fatal warnings
    from gurujee.daemon.gateway_daemon import AgentStatus
    errored = [
        name for name, state in gateway.agent_states.items()
        if state.status == AgentStatus.ERROR
    ]
    if errored:
        warnings.append(f"agent_errors:{','.join(errored)}")

    # Shizuku health check — non-fatal warning
    try:
        from gurujee.automation.executor import ShizukuExecutor  # lazy import
        executor = ShizukuExecutor()
        if not executor.is_available():
            warnings.append("shizuku_inactive")
    except Exception:
        warnings.append("shizuku_inactive")

    if warnings:
        response["warnings"] = warnings
    return JSONResponse(response)
