"""POST /chat SSE streaming endpoint (T033)."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from gurujee.agents.base_agent import Message, MessageType

router = APIRouter()

_CHUNK_TIMEOUT = 30.0  # seconds to wait for next token


class ChatRequest(BaseModel):
    message: str


async def _event_generator(
    gateway: Any,
    chat_request: ChatRequest,
    reply_id: str,
) -> AsyncGenerator[str, None]:
    """Subscribe to CHAT_STREAM_CHUNK / CHAT_RESPONSE_COMPLETE messages and yield SSE."""
    # Create a per-request inbox
    inbox: asyncio.Queue[Message] = asyncio.Queue()
    gateway._bus.register_agent(reply_id, inbox)
    try:
        # Publish CHAT_REQUEST
        await gateway._bus.send(
            Message(
                type=MessageType.CHAT_REQUEST,
                from_agent="server",
                to_agent="soul",
                payload={"message": chat_request.message},
                reply_to=reply_id,
            )
        )
        while True:
            try:
                msg = await asyncio.wait_for(inbox.get(), timeout=_CHUNK_TIMEOUT)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'error': 'timeout', 'done': True})}\n\n"
                return

            if msg.type == MessageType.CHAT_CHUNK:
                chunk = msg.payload.get("chunk", "")
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            elif msg.type == MessageType.CHAT_RESPONSE_COMPLETE:
                yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"
                return

            elif msg.type == MessageType.CHAT_ERROR:
                error = msg.payload.get("error", "unknown error")
                yield f"data: {json.dumps({'error': error, 'done': True})}\n\n"
                return
    finally:
        gateway._bus.deregister_agent(reply_id)


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    """Stream AI response tokens as Server-Sent Events."""
    gateway = request.app.state.gateway
    reply_id = f"chat:{uuid.uuid4().hex[:8]}"
    return StreamingResponse(
        _event_generator(gateway, body, reply_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
