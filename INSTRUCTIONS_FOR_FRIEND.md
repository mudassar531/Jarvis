# 📋 JARVIS Setup & Development Instructions
# For V2A Tool Development

Hey! This doc will get you up and running with JARVIS and help you understand
how to work on the V2A (Voice-to-Action) tools.

---

## 🚀 Step 1: Clone the Repo

```bash
git clone https://github.com/mudassar531/Jarvis.git
cd Jarvis
```

---

## 🐍 Step 2: Set Up Python Environment

You need **Python 3.11+** on **Windows 10/11**.

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

⚠️ **PyAudio note:** If `pip install` fails on PyAudio, install it manually:
```bash
pip install pipwin
pipwin install pyaudio
```
Or download the .whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

---

## 🔑 Step 3: Set Up API Keys

```bash
copy .env.example .env
```

Then edit `.env` and fill in your keys:

### REQUIRED:
1. **Deepgram** (Speech-to-Text) — https://console.deepgram.com
   - Sign up → get API key → paste as `DEEPGRAM_API_KEY`
   - You get $200 free credits

2. **Google Gemini** (LLM + Vision) — https://aistudio.google.com/app/apikey
   - Create API key → paste as `GOOGLE_CREDENTIALS`
   - This powers the brain AND the computer vision (screen automation)

### OPTIONAL:
3. **Brave Search** — https://api.search.brave.com
   - Free 2000 queries/month
   - If not set, falls back to DuckDuckGo (limited)

### ALTERNATIVE LLMs (if you don't want Google):
- **Ollama** (local, free): Install from https://ollama.com then run `ollama pull qwen3:8b`
- **Groq** (cloud, free tier): https://console.groq.com/keys

---

## ▶️ Step 4: Run JARVIS

### Desktop Mode (main way to use it):
```bash
python bot.py
```
- It will ask you to pick your microphone and speakers
- A floating overlay appears in the top-right showing status
- Just start talking!

### Server Mode (for browser/web clients):
```bash
python server.py
```
- Runs on http://localhost:8080
- WebSocket at ws://localhost:8080/ws
- Visit http://localhost:8080 to verify it's running

### Stop:
- Press `Ctrl+C` — it will save conversation memory before exiting

---

## 🗂️ Project Structure — What Does What

```
bot.py           → Main entry point. The voice pipeline. Start here.
                   Silero VAD → Deepgram STT → Gemini LLM → Kokoro TTS

tools.py         → ⭐ V2A TOOLS — THIS IS WHERE YOU'LL WORK MOST ⭐
                   All voice-to-action tool definitions and handlers.
                   Each tool = a FunctionSchema + a handler function.

computer_use.py  → Vision-based computer automation.
                   Screenshots → Gemini Vision → pyautogui clicks/types.
                   This is the "slow but powerful" tool.

memory.py        → SQLite-based persistent memory.
                   Stores conversations, user facts, preferences.
                   Auto-summarizes sessions using Gemini.

context.py       → Context awareness module.
                   Detects active window, time of day, etc.

ui.py            → Floating status overlay (tkinter).
                   Shows LIVE / LISTENING / THINKING / SPEAKING states.

server.py        → FastAPI WebSocket server for browser clients.
```

---

## 🔧 How to Add a New V2A Tool

This is the main thing you'll be doing. Here's the step-by-step:

### 1. Open `tools.py`

### 2. Add a FunctionSchema in `get_tools()`:
```python
FunctionSchema(
    name="my_new_tool",
    description="What this tool does — be descriptive so the LLM knows when to use it",
    properties={
        "param1": {"type": "string", "description": "What this param is for"},
        "param2": {"type": "integer", "description": "Optional numeric param"},
    },
    required=["param1"],
),
```

### 3. Add the handler function:
```python
async def _my_new_tool(param1: str, param2: int = 0) -> str:
    """Do the actual work here."""
    # Your logic
    return "Result message that JARVIS will speak aloud"
```

### 4. Add routing in `handle_tool_call()`:
```python
elif tool_name == "my_new_tool":
    result = await _my_new_tool(tool_input["param1"], tool_input.get("param2", 0))
```

### 5. Test it — run `python bot.py` and say something that should trigger your tool.

**Tips:**
- The `description` in FunctionSchema is CRITICAL — the LLM uses it to decide when to call the tool
- Return values are spoken aloud by TTS, so keep them conversational
- For async operations, use `await` and `asyncio`
- For sync operations, they still work fine (the pipeline handles it)

---

## 🖥️ Computer Use System (How It Works)

The `computer_use.py` module is a vision-action loop:

1. Takes a screenshot
2. Sends it to Gemini Vision with the task description
3. Gemini returns a JSON action (click, type, scroll, etc.)
4. pyautogui executes the action
5. Repeat until done or max 15 steps

If you need to modify what actions are possible, edit:
- `VISION_SYSTEM_PROMPT` — tells Gemini what actions exist
- `execute_action()` — actually runs the actions
- `parse_action()` — parses Gemini's JSON response

---

## 🧠 Memory System

JARVIS remembers things across sessions via SQLite:
- **Facts** — things learned about the user ("name is John", "likes dark mode")
- **Preferences** — key-value settings
- **Conversations** — full history + AI-generated summaries

The DB file (`jarvis_memory.db`) is auto-created on first run.
To reset memory: just delete the .db file.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| "No LLM available" | Add GOOGLE_CREDENTIALS or GROQ_API_KEY to .env |
| PyAudio install fails | Use `pipwin install pyaudio` or download .whl |
| No audio detected | Check mic selection at startup, try increasing AUDIO_GAIN in .env |
| Computer use not working | Needs GOOGLE_CREDENTIALS (Gemini Vision) |
| "Module not found" errors | Make sure venv is activated: `venv\Scripts\activate` |
| TTS not working | Kokoro runs locally, ensure pipecat[kokoro] installed |

---

## 💡 Ideas for V2A Tools to Add

- **clipboard_read/write** — access clipboard content
- **volume_control** — adjust system volume
- **window_management** — minimize/maximize/arrange windows
- **notification_send** — show Windows toast notifications
- **timer/alarm** — set timers and alarms
- **email_send** — send emails via SMTP
- **calendar_check** — read Google Calendar events
- **music_control** — play/pause/skip media
- **file_search** — search files on the system
- **git_commands** — run git operations by voice

---

Good luck with V2A development! The system is designed to be extended —
just add tools in tools.py and JARVIS will automatically use them.
