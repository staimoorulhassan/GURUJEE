"""GET /notifications and POST /notifications/refresh endpoints (T052)."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gurujee.agents.base_agent import Message, MessageType

router = APIRouter()


@router.get("/notifications")
async def get_notifications(request: Request) -> JSONResponse:
    """Return cached notifications from SQLite."""
    gateway = request.app.state.gateway
    ltm = getattr(gateway, "_ltm", None)
    if ltm and hasattr(ltm, "get_notifications"):
        return JSONResponse(ltm.get_notifications(limit=20))
    return JSONResponse([])


@router.post("/notifications/refresh")
async def refresh_notifications(request: Request) -> JSONResponse:
    """Trigger AutomationAgent to re-fetch notifications; return fresh list."""
    gateway = request.app.state.gateway
    reply_id = f"notif:{uuid.uuid4().hex[:8]}"
    inbox: asyncio.Queue[Message] = asyncio.Queue()
    gateway._bus.register_agent(reply_id, inbox)

    try:
        await gateway._bus.send(
            Message(
                type=MessageType.AUTOMATE_REQUEST,
                from_agent="server",
                to_agent="automation",
                payload={
                    "tool_call": {"function": {"name": "read_notifications", "arguments": {}}},
                    "input_text": "read notifications",
                },
                reply_to=reply_id,
            )
        )
        try:
            await asyncio.wait_for(inbox.get(), timeout=10.0)
        except asyncio.TimeoutError:
            pass
    finally:
        gateway._bus.deregister_agent(reply_id)

    ltm = getattr(gateway, "_ltm", None)
    if ltm and hasattr(ltm, "get_notifications"):
        return JSONResponse(ltm.get_notifications(limit=20))
    return JSONResponse([])
