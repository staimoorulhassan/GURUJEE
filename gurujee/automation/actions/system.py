"""System-level actions via Shizuku (T048)."""
from __future__ import annotations

from gurujee.config.loader import ConfigLoader
from gurujee.automation.executor import ShizukuExecutor


async def take_screenshot(executor: ShizukuExecutor) -> str:
    """Take a screenshot; returns the path to the saved file."""
    cfg = ConfigLoader.load_automation()
    path = cfg.get(
        "screenshot_path",
        "/data/data/com.termux/files/home/gurujee_screenshot.png",
    )
    await executor.execute(f"screencap -p {path}")
    return path


async def get_running_apps(executor: ShizukuExecutor) -> str:
    """Return the currently focused app."""
    stdout, _, _ = await executor.execute(
        "dumpsys activity | grep mFocusedApp"
    )
    return stdout
