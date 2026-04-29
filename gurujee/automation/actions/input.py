"""Touch / keyboard input actions via Shizuku (T046)."""
from __future__ import annotations

from gurujee.automation.executor import ShizukuExecutor


def _escape_text(text: str) -> str:
    """Escape special shell characters for `input text`."""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace(" ", "%s")


async def tap(executor: ShizukuExecutor, x: int, y: int) -> str:
    stdout, _, _ = await executor.execute(f"input tap {int(x)} {int(y)}")
    return stdout or f"Tapped ({x}, {y})"


async def swipe(
    executor: ShizukuExecutor,
    x1: int, y1: int, x2: int, y2: int,
    duration_ms: int = 300,
) -> str:
    stdout, _, _ = await executor.execute(
        f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}"
    )
    return stdout or f"Swiped ({x1},{y1})→({x2},{y2})"


async def type_text(executor: ShizukuExecutor, text: str) -> str:
    safe = _escape_text(text)
    stdout, _, _ = await executor.execute(f"input text \"{safe}\"")
    return stdout or f"Typed: {text}"


async def key_event(executor: ShizukuExecutor, keycode: int) -> str:
    stdout, _, _ = await executor.execute(f"input keyevent {int(keycode)}")
    return stdout or f"Key event {keycode}"


async def press_back(executor: ShizukuExecutor) -> str:
    return await key_event(executor, 4)
