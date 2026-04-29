"""App launch actions via Shizuku am start (T044)."""
from __future__ import annotations

from gurujee.automation.executor import ShizukuExecutor

# Extensible via config/automation.yaml app_packages
_PACKAGE_MAP: dict[str, str] = {
    "whatsapp": "com.whatsapp",
    "chrome": "com.android.chrome",
    "camera": "com.android.camera2",
    "settings": "com.android.settings",
    "clock": "com.android.deskclock",
    "messages": "com.google.android.apps.messaging",
    "youtube": "com.google.android.youtube",
    "maps": "com.google.android.apps.maps",
    "gmail": "com.google.android.gm",
    "calculator": "com.google.android.calculator",
    "photos": "com.google.android.apps.photos",
}


def resolve_package(app_name: str) -> str:
    """Map a common app name to its package identifier."""
    return _PACKAGE_MAP.get(app_name.lower().strip(), app_name)


async def open_app(executor: ShizukuExecutor, package_name: str) -> str:
    """Launch *package_name* via am start. Returns stdout."""
    cmd = (
        f"am start -a android.intent.action.MAIN "
        f"-c android.intent.category.LAUNCHER "
        f"-f 0x10200000 {package_name}"
    )
    stdout, stderr, rc = await executor.execute(cmd)
    if rc != 0:
        # Fallback attempt
        fallback = f"am start -n {package_name}/.MainActivity"
        stdout, stderr, rc = await executor.execute(fallback)
    return stdout or f"Launched {package_name}"


async def list_running_apps(executor: ShizukuExecutor) -> str:
    """Return the currently focused activity."""
    stdout, _, _ = await executor.execute(
        "dumpsys activity | grep mResumedActivity"
    )
    return stdout
