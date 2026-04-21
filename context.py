"""
JARVIS Context Awareness
Detects active window, app, and injects context into conversations.
"""

import datetime
import os
import platform

from loguru import logger


def get_active_window_info() -> dict:
    """Get information about the currently active window."""
    info = {
        "app": "Unknown",
        "title": "Unknown",
        "timestamp": datetime.datetime.now().isoformat(),
    }

    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()

            # Get window title
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            info["title"] = buf.value

            # Get process name
            import ctypes as ct
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ct.byref(pid))

            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid.value}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=3,
            )
            if result.stdout.strip():
                app_name = result.stdout.strip().split(",")[0].strip('"')
                info["app"] = app_name

    except Exception as e:
        logger.debug(f"Context awareness error: {e}")

    return info


def build_context_string() -> str:
    """Build a context string about current system state."""
    parts = []

    # Active window
    window = get_active_window_info()
    if window["title"] != "Unknown":
        parts.append(f"Active window: {window['app']} — \"{window['title']}\"")

    # Time context
    now = datetime.datetime.now()
    hour = now.hour
    if hour < 6:
        time_of_day = "late night"
    elif hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "afternoon"
    elif hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    parts.append(f"Current time: {now.strftime('%I:%M %p')} ({time_of_day}), {now.strftime('%A, %B %d, %Y')}")

    return "\n".join(parts)
