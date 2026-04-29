"""POST /automate endpoint (T051)."""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gurujee.agents.base_agent import Message, MessageType

router = APIRouter()

_REPLY_TIMEOUT = 15.0


class AutomateRequest(BaseModel):
    command: str


@router.post("/automate")
async def automate(request: Request, body: AutomateRequest) -> JSONResponse:
    """Dispatch a natural-language command to AutomationAgent, await result."""
    gateway = request.app.state.gateway
    reply_id = f"automate:{uuid.uuid4().hex[:8]}"

    inbox: asyncio.Queue[Message] = asyncio.Queue()
    gateway._bus.register_agent(reply_id, inbox)

    try:
        # Simple intent → tool_call mapping (real dispatch is via AI tool_calls)
        tool_call = _parse_command(body.command)
        await gateway._bus.send(
            Message(
                type=MessageType.AUTOMATE_REQUEST,
                from_agent="server",
                to_agent="automation",
                payload={
                    "tool_call": tool_call,
                    "input_text": body.command,
                },
                reply_to=reply_id,
            )
        )

        try:
            msg = await asyncio.wait_for(inbox.get(), timeout=_REPLY_TIMEOUT)
        except asyncio.TimeoutError:
            return JSONResponse(
                {"success": False, "result": "timeout", "command_type": "unknown", "duration_ms": 0},
                status_code=504,
            )

        return JSONResponse(msg.payload)
    finally:
        gateway._bus.deregister_agent(reply_id)


def _parse_command(command: str) -> dict[str, Any]:
    """Very simple keyword-to-tool mapping for direct /automate calls.

    In the full flow the AI produces tool_calls; this is a direct-API fallback.
    """
    cmd = command.lower()
    if "open" in cmd or "launch" in cmd or "start" in cmd:
        app_name = command.split()[-1]
        return {"function": {"name": "open_app", "arguments": {"app_name": app_name}}}
    if "notification" in cmd:
        return {"function": {"name": "read_notifications", "arguments": {}}}
    if "volume" in cmd:
        import re
        m = re.search(r"(\d+)", command)
        level = int(m.group(1)) if m else 8
        return {"function": {"name": "device_setting", "arguments": {"setting": "volume", "value": level}}}
    if "wifi" in cmd:
        enabled = "on" in cmd or "enable" in cmd
        return {"function": {"name": "device_setting", "arguments": {"setting": "wifi", "value": enabled}}}
    if "bluetooth" in cmd:
        enabled = "on" in cmd or "enable" in cmd
        return {"function": {"name": "device_setting", "arguments": {"setting": "bluetooth", "value": enabled}}}
    # Fallback — open app with last word
    return {"function": {"name": "open_app", "arguments": {"app_name": command.strip()}}}
