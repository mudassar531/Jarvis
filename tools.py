"""
V2A (Voice-to-Action) Tool Handlers
Provides web search, URL opening, file operations, and command execution.
"""

import asyncio
import datetime
import json
import os
import subprocess
import webbrowser

import aiohttp
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Action log for auditability
ACTION_LOG = []


def get_tools():
    """Return tool definitions as Pipecat FunctionSchema objects wrapped in ToolsSchema."""
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema

    schemas = [
        FunctionSchema(
            name="search_web",
            description="Search the web for current information. Use this for any factual question, recent events, or when the user asks you to look something up.",
            properties={
                "query": {"type": "string", "description": "The search query"},
            },
            required=["query"],
        ),
        FunctionSchema(
            name="open_application",
            description="Open a desktop application by name. Use this when the user asks to open, launch, or start any app. Examples: chrome, discord, notepad, spotify, vscode, file explorer, calculator, word, excel.",
            properties={
                "name": {"type": "string", "description": "The application name, e.g. 'chrome', 'discord', 'notepad', 'spotify'"},
            },
            required=["name"],
        ),
        FunctionSchema(
            name="open_url",
            description="Open a URL in the user's default web browser.",
            properties={
                "url": {"type": "string", "description": "The URL to open"},
            },
            required=["url"],
        ),
        FunctionSchema(
            name="read_file",
            description="Read the contents of a file on the local system.",
            properties={
                "path": {"type": "string", "description": "The file path to read"},
            },
            required=["path"],
        ),
        FunctionSchema(
            name="run_command",
            description="Run a shell command on Windows and return its output. Use for system tasks like checking processes, getting system info, etc.",
            properties={
                "command": {"type": "string", "description": "The Windows command to execute"},
            },
            required=["command"],
        ),
        FunctionSchema(
            name="computer_use",
            description="Control the computer visually — see the screen, click buttons, type text, navigate any app. Use ONLY for tasks that require seeing the screen and clicking specific things. Examples: 'click the first video on YouTube', 'click the submit button', 'select the second Chrome profile'.",
            properties={
                "task": {"type": "string", "description": "Natural language description of what to do on the computer"},
            },
            required=["task"],
        ),
        FunctionSchema(
            name="take_screenshot",
            description="Take a screenshot of the current screen and describe what you see. Use when the user asks what's on screen, or you need to check state.",
            properties={},
            required=[],
        ),
        FunctionSchema(
            name="youtube_search",
            description="Search YouTube for a video and open the results page. Use when user asks to find or play a song, video, or anything on YouTube.",
            properties={
                "query": {"type": "string", "description": "The YouTube search query, e.g. 'Never Gonna Give You Up Rick Astley'"},
            },
            required=["query"],
        ),
        FunctionSchema(
            name="google_search_browse",
            description="Search Google and open the results in Chrome. Use when user wants to search and see results in the browser.",
            properties={
                "query": {"type": "string", "description": "The Google search query"},
            },
            required=["query"],
        ),
        FunctionSchema(
            name="save_memory",
            description="Save an important fact or preference about the user. Use when user tells you their name, preferences, habits, or anything worth remembering for future conversations.",
            properties={
                "category": {"type": "string", "description": "Category: 'user' for personal info, 'preference' for settings/likes, 'knowledge' for general facts"},
                "content": {"type": "string", "description": "The fact or preference to remember"},
            },
            required=["category", "content"],
        ),
        # ──── Gmail Email Tools ────
        FunctionSchema(
            name="compose_email",
            description="Open Gmail in Chrome with a pre-filled email (to, subject, body, cc). The user can see the email in the browser, review it, and ask you to fix spelling or other errors via computer_use before sending. If the user gives a name, look up their email in contacts first. If they give an email address directly, use that.",
            properties={
                "to": {"type": "string", "description": "Recipient name (looked up in contacts) OR direct email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Full email body. Write a complete professional message with greeting and sign-off based on what the user wants to say."},
                "cc": {"type": "string", "description": "Optional CC recipient name or email address"},
            },
            required=["to", "subject", "body"],
        ),
        FunctionSchema(
            name="read_inbox",
            description="Read the latest emails from the user's Gmail inbox.",
            properties={
                "count": {"type": "integer", "description": "Number of emails to fetch (default 5, max 20)"},
            },
            required=[],
        ),
        FunctionSchema(
            name="add_contact",
            description="Save a person's email to contacts for future use. Use when user tells you someone's email.",
            properties={
                "name": {"type": "string", "description": "Person's name"},
                "email": {"type": "string", "description": "Person's email address"},
            },
            required=["name", "email"],
        ),
        FunctionSchema(
            name="list_contacts",
            description="Show all saved contacts with their email addresses.",
            properties={},
            required=[],
        ),
    ]
    return ToolsSchema(standard_tools=schemas)


async def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result string."""
    logger.info(f"Tool call: {tool_name}({json.dumps(tool_input, indent=2)})")
    result = ""

    try:
        if tool_name == "search_web":
            result = await _search_web(tool_input["query"])
        elif tool_name == "open_application":
            result = _open_application(tool_input["name"])
        elif tool_name == "open_url":
            result = _open_url(tool_input["url"])
        elif tool_name == "read_file":
            result = _read_file(tool_input["path"])
        elif tool_name == "run_command":
            result = await _run_command(tool_input["command"])
        elif tool_name == "computer_use":
            result = await _computer_use(tool_input["task"])
        elif tool_name == "take_screenshot":
            result = await _take_screenshot()
        elif tool_name == "youtube_search":
            result = _youtube_search(tool_input["query"])
        elif tool_name == "google_search_browse":
            result = _google_search_browse(tool_input["query"])
        elif tool_name == "save_memory":
            result = _save_memory(tool_input.get("category", "user"), tool_input["content"])
        elif tool_name == "compose_email":
            result = _compose_email(
                tool_input["to"],
                tool_input["subject"],
                tool_input["body"],
                tool_input.get("cc"),
            )
        elif tool_name == "read_inbox":
            result = await _read_inbox(tool_input.get("count", 5))
        elif tool_name == "add_contact":
            result = _add_contact(tool_input["name"], tool_input["email"])
        elif tool_name == "list_contacts":
            result = _list_contacts()
        else:
            result = f"Unknown tool: {tool_name}"
    except Exception as e:
        result = f"Error executing {tool_name}: {str(e)}"

    _log_action(tool_name, tool_input, result)
    logger.info(f"Tool result: {result[:200]}...")
    return result


async def _search_web(query: str) -> str:
    """Search the web using Brave Search API."""
    api_key = os.getenv("BRAVE_API_KEY")

    if not api_key or api_key == "YOUR_KEY_HERE":
        return await _search_web_fallback(query)

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": 5}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                return f"Search failed with status {resp.status}"
            data = await resp.json()

    results = []
    for item in data.get("web", {}).get("results", [])[:5]:
        title = item.get("title", "")
        description = item.get("description", "")
        link = item.get("url", "")
        results.append({"title": title, "description": description, "url": link})

    if not results:
        return "No search results found."

    # Print formatted results to terminal for visual display
    _print_search_results(query, results)

    # Return concise text for the LLM to speak aloud
    spoken = [f"{r['title']}: {r['description']}" for r in results[:3]]
    return f"Search results for '{query}':\n" + "\n".join(f"- {s}" for s in spoken)


def _print_search_results(query: str, results: list):
    """Print search results to terminal with formatting."""
    print(f"\n{'='*60}")
    print(f"  🔍 SEARCH: {query}")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r['title']}")
        print(f"      {r['description'][:120]}")
        if r['url']:
            print(f"      🔗 {r['url']}")
        print()
    print(f"{'='*60}\n")


async def _search_web_fallback(query: str) -> str:
    """Fallback search using DuckDuckGo instant answers (no API key needed)."""
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return "Search unavailable. Please provide a BRAVE_API_KEY in .env for web search."
            data = await resp.json()

    abstract = data.get("AbstractText", "")
    answer = data.get("Answer", "")
    related = [t.get("Text", "") for t in data.get("RelatedTopics", [])[:3] if isinstance(t, dict)]

    if abstract:
        return f"Search result: {abstract}"
    elif answer:
        return f"Answer: {answer}"
    elif related:
        return "Related information:\n" + "\n".join(f"- {r}" for r in related if r)
    else:
        return f"No instant results found for '{query}'. Try rephrasing the question."


def _open_url(url: str) -> str:
    """Open a URL in the default browser."""
    webbrowser.open(url)
    return f"Opened {url} in your browser."


def _open_application(name: str) -> str:
    """Open a desktop application by name on Windows."""
    # Map common names to Windows launch commands
    app_map = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "firefox": "start firefox",
        "edge": "start msedge",
        "discord": r'start "" "%LOCALAPPDATA%\Discord\Update.exe" --processStart Discord.exe',
        "notepad": "start notepad",
        "file explorer": "start explorer",
        "explorer": "start explorer",
        "spotify": "start spotify:",
        "calculator": "start calc",
        "calc": "start calc",
        "terminal": "start wt",
        "cmd": "start cmd",
        "powershell": "start powershell",
        "vscode": "start code",
        "vs code": "start code",
        "code": "start code",
        "word": "start winword",
        "excel": "start excel",
        "outlook": "start outlook",
        "teams": "start msteams:",
        "paint": "start mspaint",
        "snipping tool": "start snippingtool",
        "task manager": "start taskmgr",
        "settings": "start ms-settings:",
        "store": "start ms-windows-store:",
    }

    key = name.lower().strip()
    cmd = app_map.get(key, f"start {key}")

    logger.info(f"Opening application '{name}' with: {cmd}")
    try:
        subprocess.Popen(cmd, shell=True)
        return f"Opened {name}."
    except Exception as e:
        return f"Failed to open {name}: {str(e)}"


def _read_file(path: str) -> str:
    """Read file contents (with size limit)."""
    if not os.path.exists(path):
        return f"File not found: {path}"

    size = os.path.getsize(path)
    if size > 50_000:
        return f"File too large ({size} bytes). Maximum is 50KB."

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return f"Contents of {path}:\n{content}"


async def _run_command(command: str) -> str:
    """Run a system command with timeout."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace").strip()
        errors = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            return output[:2000] if output else "Command completed successfully."
        else:
            return f"Command failed (exit {proc.returncode}): {errors[:1000]}"
    except asyncio.TimeoutError:
        return "Command timed out after 15 seconds."


def _log_action(tool_name: str, tool_input: dict, result: str):
    """Log action for auditability."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tool": tool_name,
        "input": tool_input,
        "result_preview": result[:200],
    }
    ACTION_LOG.append(entry)
    logger.debug(f"Action logged: {tool_name}")


async def _computer_use(task: str) -> str:
    """Execute a complex computer use task via vision-based agent."""
    from computer_use import run_computer_use

    logger.info(f"🖥️ Computer Use tool called: {task}")
    try:
        result = await run_computer_use(task)
        return result
    except Exception as e:
        logger.error(f"Computer Use error: {e}")
        return f"Computer use failed: {str(e)}"


async def _take_screenshot() -> str:
    """Take a screenshot and describe what's on screen using Gemini Vision."""
    from computer_use import take_screenshot, screenshot_to_base64

    logger.info("📸 Taking screenshot for description...")
    try:
        screenshot = take_screenshot()
        screenshot_b64 = screenshot_to_base64(screenshot, scale=0.5)

        from google import genai

        api_key = os.getenv("GOOGLE_CREDENTIALS", "")
        if not api_key:
            return "Cannot describe screen: no Google API key."

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": "image/jpeg", "data": screenshot_b64}},
                        {"text": "Describe what's on this screen in 2-3 short sentences. What apps are open, what content is visible?"},
                    ],
                }
            ],
        )
        return f"Screenshot taken. I can see: {response.text}"
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return f"Failed to take screenshot: {str(e)}"


def _youtube_search(query: str) -> str:
    """Open YouTube search results directly in browser."""
    import urllib.parse
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    logger.info(f"🎵 YouTube search: {query}")
    return f"Opened YouTube search for '{query}'. The results are now showing in your browser."


def _google_search_browse(query: str) -> str:
    """Open Google search results directly in browser."""
    import urllib.parse
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    logger.info(f"🔍 Google search browse: {query}")
    return f"Opened Google search for '{query}' in your browser."


def _save_memory(category: str, content: str) -> str:
    """Save a fact or preference to persistent memory."""
    from memory import save_fact, save_preference

    if category == "preference":
        # Try to extract key=value from content
        if ":" in content:
            key, value = content.split(":", 1)
            save_preference(key.strip(), value.strip())
        else:
            save_fact("preference", content, importance=7)
    else:
        importance = 8 if category == "user" else 5
        save_fact(category, content, importance=importance)

    logger.info(f"🧠 Saved to memory [{category}]: {content}")
    return f"Got it, I'll remember that."


# ──────────────────────────────────────────────
# Gmail Email Tools
# ──────────────────────────────────────────────

def _compose_email(to: str, subject: str, body: str, cc: str = None) -> str:
    """Open Gmail compose in Chrome with pre-filled fields."""
    import urllib.parse
    from contacts import find_contact

    # Resolve recipient: name → email lookup
    to_email = to
    if "@" not in to:
        contact = find_contact(to)
        if contact:
            to_email = contact["email"]
            logger.info(f"📧 Contact found: {to} → {contact['email']}")
        else:
            return (
                f"I don't have an email address for '{to}'. "
                f"Tell me their email and I'll save it, or give me the email address directly."
            )

    # Resolve CC if provided
    cc_email = None
    if cc:
        if "@" in cc:
            cc_email = cc
        else:
            cc_contact = find_contact(cc)
            if cc_contact:
                cc_email = cc_contact["email"]
            else:
                return f"I don't have an email for CC recipient '{cc}'. Tell me their email first."

    # Build Gmail compose URL
    params = {
        "view": "cm",
        "fs": "1",
        "to": to_email,
        "su": subject,
        "body": body,
    }
    if cc_email:
        params["cc"] = cc_email

    url = "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)
    webbrowser.open(url)

    logger.info(f"📧 Gmail compose opened → To: {to_email}, Subject: {subject}")

    result = f"I've opened Gmail with your email ready to review.\n"
    result += f"To: {to_email}\n"
    if cc_email:
        result += f"CC: {cc_email}\n"
    result += f"Subject: {subject}\n"
    result += "You can see it in Chrome now. Let me know if you want me to fix any spelling or make changes — I'll use screen control to edit it. When it looks good, just tell me to hit send."
    return result


async def _read_inbox(count: int = 5) -> str:
    """Read latest emails from Gmail inbox."""
    import asyncio
    from gmail_service import read_inbox

    count = min(max(1, count), 20)
    emails = await asyncio.to_thread(read_inbox, count)

    if not emails:
        return "Your inbox is empty or Gmail is not connected."

    lines = [f"You have {len(emails)} recent emails:"]
    for i, e in enumerate(emails, 1):
        sender = e["from"].split("<")[0].strip().strip('"')
        lines.append(f"{i}. From {sender}: {e['subject']}. {e['snippet'][:80]}")

    return "\n".join(lines)


def _add_contact(name: str, email: str) -> str:
    """Add a contact for email lookup."""
    from contacts import add_contact
    return add_contact(name, email)


def _list_contacts() -> str:
    """List all saved contacts."""
    from contacts import list_contacts

    contacts = list_contacts()
    if not contacts:
        return "No contacts saved yet. Tell me someone's email and I'll remember it."

    lines = [f"You have {len(contacts)} contacts:"]
    for c in contacts:
        lines.append(f"- {c['name']}: {c['email']}")
    return "\n".join(lines)
