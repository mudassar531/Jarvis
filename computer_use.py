"""
JARVIS Computer Use Agent
Vision-based desktop automation: screenshot → Gemini Vision → action → repeat
Uses pyautogui for mouse/keyboard and Gemini for visual understanding.
"""

import asyncio
import base64
import io
import json
import os
import re
import time

import pyautogui
from PIL import Image
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

MAX_STEPS = 15
SCREENSHOT_SCALE = 0.5

VISION_SYSTEM_PROMPT = """You control a Windows 11 PC. You see a screenshot (scaled down but coordinates are for 1920x1080).
Return ONLY a JSON object — no markdown, no code fences.

{
  "thought": "what I see and plan to do",
  "action": "click|double_click|type|key|scroll|wait|done",
  "x": 0, "y": 0,
  "text": "",
  "key": "",
  "done": false,
  "summary": ""
}

Actions: click(x,y), double_click(x,y), type(text, optional x,y to click first), key(combo like "enter","ctrl+a"), scroll(x,y, text="up"/"down"), wait(2s), done(summary).
Coordinates are absolute 1920x1080 pixels. Taskbar is at the bottom. Be precise — aim at CENTER of targets.
To open an app: Win search or Start menu. When done, set done=true with summary."""


def take_screenshot() -> Image.Image:
    """Capture the full screen and return as PIL Image."""
    return pyautogui.screenshot()


def screenshot_to_base64(img: Image.Image, scale: float = SCREENSHOT_SCALE) -> str:
    """Convert PIL Image to base64 string, optionally downscaled."""
    if scale != 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def parse_action(response_text: str) -> dict:
    """Parse the JSON action from Gemini's response."""
    text = response_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning(f"Failed to parse action JSON: {text[:200]}")
    return {"action": "done", "done": True, "summary": "Failed to understand the screen. Please try again."}


def execute_action(action: dict) -> str:
    """Execute a single action using pyautogui. Returns status string."""
    action_type = action.get("action", "done")
    x = action.get("x", 0)
    y = action.get("y", 0)
    text = action.get("text", "")
    key = action.get("key", "")

    logger.info(f"🖱️ Action: {action_type} at ({x},{y}) text='{text}' key='{key}'")

    try:
        if action_type == "click":
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})"

        elif action_type == "double_click":
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at ({x}, {y})"

        elif action_type == "right_click":
            pyautogui.rightClick(x, y)
            return f"Right-clicked at ({x}, {y})"

        elif action_type == "type":
            if x > 0 and y > 0:
                pyautogui.click(x, y)
                time.sleep(0.3)
            import pyperclip
            try:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pyautogui.typewrite(text, interval=0.03)
            return f"Typed '{text}'"

        elif action_type == "key":
            pyautogui.hotkey(*key.split("+"))
            return f"Pressed key: {key}"

        elif action_type == "scroll":
            direction = text.lower() if text else "down"
            clicks = 3 if direction == "down" else -3
            pyautogui.scroll(clicks, x, y)
            return f"Scrolled {direction} at ({x}, {y})"

        elif action_type == "wait":
            time.sleep(2)
            return "Waited 2 seconds"

        elif action_type == "done":
            return action.get("summary", "Task completed.")

        else:
            return f"Unknown action: {action_type}"

    except Exception as e:
        return f"Action failed: {str(e)}"


async def analyze_screen(task: str, screenshot_b64: str, history: list[str], step: int) -> dict:
    """Send screenshot to Gemini Vision and get the next action."""
    from google import genai

    api_key = os.getenv("GOOGLE_CREDENTIALS", "")
    if not api_key:
        return {"action": "done", "done": True, "summary": "No Google API key configured."}

    client = genai.Client(api_key=api_key)

    history_text = ""
    if history:
        history_text = "\n\nPrevious actions taken:\n" + "\n".join(f"  Step {i+1}: {h}" for i, h in enumerate(history))

    prompt = f"""TASK: {task}
Step: {step}/{MAX_STEPS}{history_text}

Look at the screenshot and decide the next action. Respond with ONLY a JSON object."""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": VISION_SYSTEM_PROMPT},
                        {"inline_data": {"mime_type": "image/jpeg", "data": screenshot_b64}},
                        {"text": prompt},
                    ],
                }
            ],
        )

        response_text = response.text
        logger.info(f"🧠 Gemini Vision response: {response_text[:300]}")
        return parse_action(response_text)

    except Exception as e:
        logger.error(f"Gemini Vision error: {e}")
        return {"action": "done", "done": True, "summary": f"Vision analysis failed: {str(e)}"}


async def run_computer_use(task: str, status_callback=None) -> str:
    """
    Main computer use agent loop.
    Takes a natural language task, controls the computer to accomplish it.
    Returns a summary of what was done.
    """
    logger.info(f"🖥️ Computer Use Agent starting: {task}")

    if status_callback:
        status_callback("thinking", f"🖥️ Computer Use: {task[:40]}...")

    history = []

    for step in range(1, MAX_STEPS + 1):
        screenshot = take_screenshot()
        screenshot_b64 = screenshot_to_base64(screenshot, scale=SCREENSHOT_SCALE)

        if status_callback:
            status_callback("thinking", f"🖥️ Step {step}: Analyzing screen...")

        action = await analyze_screen(task, screenshot_b64, history, step)

        thought = action.get("thought", "")
        logger.info(f"🧠 Step {step} thought: {thought}")

        if action.get("done", False) or action.get("action") == "done":
            summary = action.get("summary", "Task completed.")
            logger.info(f"✅ Computer Use completed: {summary}")
            if status_callback:
                status_callback("speaking", f"✅ Done: {summary[:50]}...")
            return summary

        if status_callback:
            status_callback("thinking", f"🖥️ Step {step}: {action.get('action', '?')}...")

        result = execute_action(action)
        history.append(f"{action.get('action', '?')}: {result}")

        await asyncio.sleep(0.5)

    summary = f"Reached maximum {MAX_STEPS} steps. Last actions: " + "; ".join(history[-3:])
    logger.warning(f"⚠️ Computer Use max steps: {summary}")
    return summary
