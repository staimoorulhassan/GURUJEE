"""Device settings actions via Shizuku (T045)."""
from __future__ import annotations

from gurujee.automation.executor import ShizukuExecutor


async def set_volume(executor: ShizukuExecutor, level: int) -> str:
    level = max(0, min(15, int(level)))
    stdout, _, _ = await executor.execute(
        f"media volume --set {level} --stream 3"
    )
    return stdout or f"Volume set to {level}"


async def get_volume(executor: ShizukuExecutor) -> str:
    stdout, _, _ = await executor.execute("media volume --get --stream 3")
    return stdout


async def set_wifi(executor: ShizukuExecutor, enabled: bool) -> str:
    cmd = "svc wifi enable" if enabled else "svc wifi disable"
    stdout, _, _ = await executor.execute(cmd)
    return stdout or ("WiFi enabled" if enabled else "WiFi disabled")


async def set_bluetooth(executor: ShizukuExecutor, enabled: bool) -> str:
    cmd = "svc bluetooth enable" if enabled else "svc bluetooth disable"
    stdout, _, _ = await executor.execute(cmd)
    return stdout or ("Bluetooth enabled" if enabled else "Bluetooth disabled")


async def set_brightness(executor: ShizukuExecutor, level: int) -> str:
    level = max(0, min(255, int(level)))
    stdout, _, _ = await executor.execute(
        f"settings put system screen_brightness {level}"
    )
    return stdout or f"Brightness set to {level}"
