# 🧠 JARVIS — Voice Agent Neural Operating System

An always-on AI assistant that lives on your Windows PC. Talk to it naturally — it listens, thinks, speaks back, controls your computer, remembers your conversations, and learns about you over time.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  Microphone  │───▶│  Silero VAD  │───▶│ Deepgram STT │───▶│ Gemini 2.5  │
│  (PyAudio)   │    │  (local)     │    │  (Nova-3)    │    │ Flash (LLM) │
└─────────────┘    └──────────────┘    └──────────────┘    └──────┬──────┘
                                                                  │
┌─────────────┐    ┌──────────────┐                               │
│  Speakers   │◀───│  Kokoro TTS  │◀──────────────────────────────┘
│  (PyAudio)  │    │  (local)     │
└─────────────┘    └──────────────┘
```

**Pipeline:** Silero VAD → Deepgram STT → Gemini 2.5 Flash → Kokoro TTS

## Features

| Feature | Description |
|---|---|
| 🎙️ **Voice Control** | Always-on listening with Silero VAD + Deepgram STT |
| 🧠 **Persistent Memory** | Remembers facts, preferences, and past conversations (SQLite) |
| 🖥️ **Computer Use** | Vision-based desktop automation — sees screen, clicks, types (Gemini Vision + pyautogui) |
| 🔍 **Web Search** | Brave Search API with DuckDuckGo fallback |
| 🚀 **App Launcher** | Opens any Windows application by name |
| 🌐 **URL/YouTube** | Opens URLs, YouTube searches, Google searches |
| 📁 **File Reader** | Reads local files on command |
| ⚡ **System Commands** | Runs any Windows shell command |
| 📸 **Screenshot** | Takes & describes what's on screen |
| 💬 **Context Aware** | Knows active window, time of day, and user history |
| 🎯 **Status Overlay** | Floating always-on-top indicator (LIVE/LISTENING/THINKING/SPEAKING) |
| 📧 **Gmail Email** | Send/read emails via voice — draft → confirm → send pattern |
| 📇 **Contacts** | Name → email lookup with fuzzy matching |

## V2A (Voice-to-Action) Tools

The `tools.py` module is the V2A engine — it converts voice commands into system actions. Current tools:

| Tool | Speed | Description |
|---|---|---|
| `search_web` | Fast | Brave Search / DuckDuckGo |
| `open_application` | Instant | Launch any Windows app |
| `open_url` | Instant | Open any URL in browser |
| `youtube_search` | Instant | YouTube search in browser |
| `google_search_browse` | Instant | Google search in browser |
| `read_file` | Fast | Read local file contents |
| `run_command` | Fast | Execute Windows commands |
| `computer_use` | Slow | Vision-based screen automation |
| `take_screenshot` | Fast | Capture & describe screen |
| `save_memory` | Instant | Save user facts/preferences |
| `send_email` | Fast | Draft email (contact lookup + HTML) |
| `confirm_send_email` | Fast | Send drafted email via Gmail |
| `cancel_email` | Instant | Cancel pending email draft |
| `read_inbox` | Fast | Read latest Gmail inbox emails |
| `add_contact` | Instant | Save name → email mapping |
| `list_contacts` | Instant | Show all saved contacts |

**To add a new V2A tool:**
1. Add a `FunctionSchema` in `get_tools()` in `tools.py`
2. Add a handler function (e.g., `_my_new_tool()`)
3. Add the routing in `handle_tool_call()`
4. The LLM will automatically discover and use it based on the schema description

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Windows 10/11** (computer use + context awareness use Win32 APIs)
- **A microphone and speakers/headphones**

### 1. Clone & Setup

```bash
git clone https://github.com/mudassar531/Jarvis.git
cd Jarvis

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
copy .env.example .env
```

Edit `.env` and add your API keys. **Minimum required:**
- `DEEPGRAM_API_KEY` — for speech-to-text ([get free key](https://console.deepgram.com))
- **One LLM** (pick one):
  - `GOOGLE_CREDENTIALS` — Google Gemini (**recommended**, [get key](https://aistudio.google.com/app/apikey))
  - Or install [Ollama](https://ollama.com) + `ollama pull qwen3:8b` (free, local)
  - Or `GROQ_API_KEY` — Groq cloud ([get free key](https://console.groq.com/keys))

**Optional:**
- `BRAVE_API_KEY` — for web search ([get free key](https://api.search.brave.com))

### Gmail Setup (for email features)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API**: APIs & Services → Library → search "Gmail API" → Enable
4. Create credentials: APIs & Services → Credentials → Create Credentials → **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
   - Download the JSON file
5. Save it as `credentials.json` in the Jarvis folder
6. First time you use email, a browser window opens for Google sign-in → authorize → done
7. Token is saved automatically as `token.json` (auto-refreshes, you won't be asked again)
8. Set `GMAIL_SENDER_NAME=Your Name` in `.env` for email signatures

### 3. Run

**Desktop mode** (local microphone + speakers):
```bash
python bot.py
```

**Server mode** (WebSocket for browser clients):
```bash
python server.py
```

## Project Structure

```
Jarvis/
├── bot.py              # Main pipeline — voice agent entry point
├── server.py           # FastAPI WebSocket server (browser mode)
├── tools.py            # V2A tool definitions & handlers
├── gmail_service.py    # Gmail API + OAuth2 + HTML email templates
├── contacts.py         # Contact manager (name → email lookup)
├── computer_use.py     # Vision-based desktop automation agent
├── context.py          # Context awareness (active window, time)
├── memory.py           # Persistent memory system (SQLite + Gemini)
├── ui.py               # Floating status overlay (tkinter)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── .gitignore          # Git ignore rules
```

## LLM Priority

JARVIS auto-detects the best available LLM:

1. **Google Gemini** (cloud) — Best option. Fast, great tool calling, vision support for computer use.
2. **Ollama** (local) — Free, private, no API key needed. Requires local Ollama server.
3. **Groq** (cloud) — Free tier fallback. Fast inference, limited daily tokens.

## Contributing

This is designed to be extended. Key extension points:

- **New V2A tools** → `tools.py` (see "To add a new V2A tool" above)
- **New LLM providers** → `get_llm_service()` in `bot.py`
- **Computer use improvements** → `computer_use.py` (action types, vision prompts)
- **Memory enhancements** → `memory.py` (new fact categories, smarter summarization)
- **UI changes** → `ui.py` (overlay states, styling)

## License

MIT
