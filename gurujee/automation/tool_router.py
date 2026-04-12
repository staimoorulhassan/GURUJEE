"""ToolRouter — maps OpenAI tool calls to automation action functions (T049)."""
from __future__ import annotations

import logging
from typing import Any, Coroutine

from gurujee.automation.executor import AutomationError, ShizukuExecutor

logger = logging.getLogger(__name__)

# OpenAI function-calling schemas for the 5 automation categories
TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open a mobile application by name or package",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "App name (e.g. 'WhatsApp') or package id"},
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "device_setting",
            "description": "Control device settings: volume, wifi, bluetooth, brightness",
            "parameters": {
                "type": "object",
                "properties": {
                    "setting": {"type": "string", "enum": ["volume", "wifi", "bluetooth", "brightness"]},
                    "value": {"description": "For volume/brightness: 0-15/0-255 int; for wifi/bluetooth: true/false"},
                },
                "required": ["setting", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ui_input",
            "description": "Perform touch or keyboard input on the screen",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["tap", "swipe", "type_text", "press_back"]},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "x2": {"type": "integer"},
                    "y2": {"type": "integer"},
                    "text": {"type": "string"},
                    "duration_ms": {"type": "integer", "default": 300},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_notifications",
            "description": "Read the current Android notification list",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set an alarm or reminder (opens Clock app with pre-filled time)",
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {"type": "string", "description": "Time string, e.g. '07:30' or '7:30 AM'"},
                    "label": {"type": "string"},
                },
                "required": ["time"],
            },
        },
    },
]


class ToolRouter:
    """Maps tool_call JSON from the AI to the correct action coroutine."""

    def __init__(self, executor: ShizukuExecutor) -> None:
        self._executor = executor

    def route(self, tool_call: dict[str, Any]) -> Coroutine[Any, Any, str]:
        """Return a coroutine that executes the requested tool.

        *tool_call* is an OpenAI tool_call object (function.name + function.arguments).
        Raises AutomationError for unknown tool names.
        """
        name = tool_call.get("function", {}).get("name") or tool_call.get("name", "")
        args: dict = tool_call.get("function", {}).get("arguments") or tool_call.get("arguments", {})
        if isinstance(args, str):
            import json
            args = json.loads(args)

        if name == "open_app":
            return self._open_app(args)
        if name == "device_setting":
            return self._device_setting(args)
        if name == "ui_input":
            return self._ui_input(args)
        if name == "read_notifications":
            return self._read_notifications(args)
        if name == "set_reminder":
            return self._set_reminder(args)
        raise AutomationError(f"Unknown tool: {name!r}")

    # ------------------------------------------------------------------ #
    # Action coroutines                                                     #
    # ------------------------------------------------------------------ #

    async def _open_app(self, args: dict) -> str:
        from gurujee.automation.actions.apps import open_app, resolve_package
        pkg = resolve_package(args.get("app_name", ""))
        return await open_app(self._executor, pkg)

    async def _device_setting(self, args: dict) -> str:
        from gurujee.automation.actions import device
        setting = args.get("setting", "")
        value = args.get("value")
        if setting == "volume":
            return await device.set_volume(self._executor, int(value))
        if setting == "wifi":
            return await device.set_wifi(self._executor, bool(value))
        if setting == "bluetooth":
            return await device.set_bluetooth(self._executor, bool(value))
        if setting == "brightness":
            return await device.set_brightness(self._executor, int(value))
        raise AutomationError(f"Unknown device setting: {setting!r}")

    async def _ui_input(self, args: dict) -> str:
        from gurujee.automation.actions import input as inp
        action = args.get("action", "")
        if action == "tap":
            return await inp.tap(self._executor, args["x"], args["y"])
        if action == "swipe":
            return await inp.swipe(
                self._executor,
                args["x"], args["y"], args["x2"], args["y2"],
                args.get("duration_ms", 300),
            )
        if action == "type_text":
            return await inp.type_text(self._executor, args["text"])
        if action == "press_back":
            return await inp.press_back(self._executor)
        raise AutomationError(f"Unknown ui_input action: {action!r}")

    async def _read_notifications(self, args: dict) -> str:
        from gurujee.automation.actions.notifications import list_notifications
        notifs = await list_notifications(self._executor)
        if not notifs:
            return "No notifications."
        lines = [
            f"[{n.get('appName', n.get('packageName', '?'))}] "
            f"{n.get('title', '')}: {n.get('content', '')}"
            for n in notifs[:10]
        ]
        return "\n".join(lines)

    async def _set_reminder(self, args: dict) -> str:
        from gurujee.automation.actions.apps import open_app
        time_str = args.get("time", "")
        label = args.get("label", "Reminder")
        cmd = (
            f"am start -a android.intent.action.SET_ALARM "
            f"--es android.intent.extra.alarm.MESSAGE \"{label}\" "
            f"--ez android.intent.extra.alarm.SKIP_UI false "
        )
        try:
            h, m = time_str.replace("AM", "").replace("PM", "").strip().split(":")
            cmd += f"--ei android.intent.extra.alarm.HOUR {int(h)} "
            cmd += f"--ei android.intent.extra.alarm.MINUTES {int(m)}"
        except Exception:
            pass
        await self._executor.execute(cmd)
        return f"Reminder set: {label} at {time_str}"
