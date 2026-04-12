"""WebSocket /ws endpoint — broadcasts agent status and automation results (T036)."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Register the client, forward gateway events, handle keep-alive."""
    await websocket.accept()
    gateway = websocket.app.state.gateway
    gateway.ws_clients.add(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                continue
            except WebSocketDisconnect:
                break

            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except Exception as exc:
        logger.debug("WebSocket connection closed: %s", exc)
    finally:
        gateway.ws_clients.discard(websocket)


async def broadcast_to_clients(gateway: object, event: dict) -> None:
    """Utility used by GatewayDaemon to push events to all connected clients."""
    message = json.dumps(event)
    dead: list = []
    for ws in list(getattr(gateway, "ws_clients", set())):
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        getattr(gateway, "ws_clients", set()).discard(ws)
