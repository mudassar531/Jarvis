"""
Generate JARVIS Project Documentation PDF
"""
from fpdf import FPDF
import os

class JarvisPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, "JARVIS Voice Agent - Technical Documentation", align="C")
            self.ln(5)
            self.set_draw_color(52, 152, 219)
            self.set_line_width(0.5)
            self.line(10, 18, 200, 18)
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(41, 128, 185)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(41, 128, 185)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def bullet(self, text, indent=15):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(5, 6, "-")
        self.multi_cell(0, 6, text)
        self.ln(1)

    def code_block(self, text):
        self.set_fill_color(240, 240, 240)
        self.set_font("Courier", "", 9)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        self.set_x(x + 5)
        self.multi_cell(180, 5, text, fill=True)
        self.ln(4)

    def diagram_box(self, x, y, w, h, label, color=(52, 152, 219)):
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        self.rect(x, y, w, h, style="F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        tw = self.get_string_width(label)
        self.set_xy(x + (w - tw) / 2, y + (h - 5) / 2)
        self.cell(tw, 5, label)

    def diagram_arrow(self, x1, y1, x2, y2):
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.6)
        self.line(x1, y1, x2, y2)
        # arrowhead
        self.set_fill_color(100, 100, 100)
        size = 2
        if x2 > x1:  # right arrow
            self.polygon([(x2, y2), (x2 - size, y2 - size/2), (x2 - size, y2 + size/2)], style="F")
        elif y2 > y1:  # down arrow
            self.polygon([(x2, y2), (x2 - size/2, y2 - size), (x2 + size/2, y2 - size)], style="F")

    def label_text(self, x, y, text, size=7, color=(100, 100, 100)):
        self.set_font("Helvetica", "I", size)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(0, 4, text)


def build_pdf():
    pdf = JarvisPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ==================== COVER PAGE ====================
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 20, "JARVIS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 10, "Voice Agent Neural Operating System", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_draw_color(41, 128, 185)
    pdf.set_line_width(1)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(15)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Technical Documentation & Architecture Guide", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(0, 8, "Built with Pipecat AI Framework", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "April 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(30)

    # Hardware specs box
    pdf.set_fill_color(236, 240, 241)
    pdf.rect(30, pdf.get_y(), 150, 35, style="F")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(44, 62, 80)
    bx = pdf.get_y() + 5
    pdf.set_xy(40, bx)
    pdf.cell(0, 6, "Target Hardware")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(40, bx + 8)
    pdf.cell(0, 5, "GPU: NVIDIA RTX 5060  |  RAM: 32GB DDR4")
    pdf.set_xy(40, bx + 15)
    pdf.cell(0, 5, "CPU: AMD Ryzen 5 5600  |  OS: Windows 11")
    pdf.set_xy(40, bx + 22)
    pdf.cell(0, 5, "Python 3.13.7  |  Pipecat 0.0.108")

    # ==================== TABLE OF CONTENTS ====================
    pdf.add_page()
    pdf.section_title("Table of Contents")
    pdf.ln(5)
    toc = [
        ("1.", "Project Overview", 3),
        ("2.", "System Architecture & Pipeline", 3),
        ("3.", "Pipeline Diagram", 4),
        ("4.", "Component Details", 5),
        ("5.", "Audio Processing", 6),
        ("6.", "Voice-to-Action (V2A) Tools", 7),
        ("7.", "Desktop Integration", 8),
        ("8.", "Configuration & API Keys", 9),
        ("9.", "File Structure", 10),
        ("10.", "Challenges & Solutions", 10),
        ("11.", "Future Upgrades", 11),
    ]
    for num, title, page in toc:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(12, 8, num)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(140, 8, title)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8, str(page), align="R", new_x="LMARGIN", new_y="NEXT")

    # ==================== 1. PROJECT OVERVIEW ====================
    pdf.add_page()
    pdf.section_title("1. Project Overview")
    pdf.body_text(
        "JARVIS (Voice Agent Neural Operating System) is a real-time voice AI assistant built to run "
        "on consumer-grade hardware. It listens to the user through a microphone, understands speech, "
        "thinks using a large language model, and responds with natural-sounding speech. It can also "
        "take actions: searching the web, opening applications, reading files, and running commands."
    )
    pdf.body_text(
        "The system is built on top of the Pipecat AI framework (v0.0.108), which provides a "
        "pipeline-based architecture for composing real-time voice AI applications. Each stage of "
        "the pipeline handles one task: audio input, speech recognition, language understanding, "
        "speech synthesis, and audio output."
    )

    pdf.sub_title("Key Features")
    pdf.bullet("Real-time voice conversation with sub-second latency")
    pdf.bullet("Web search via Brave Search API with DuckDuckGo fallback")
    pdf.bullet("Application launching (Chrome, Discord, Notepad, 20+ apps)")
    pdf.bullet("File reading and system command execution")
    pdf.bullet("Auto-detecting audio devices (stereo/mono, USB/built-in)")
    pdf.bullet("Floating desktop status overlay (LIVE / LISTENING / THINKING / SPEAKING)")
    pdf.bullet("Desktop launcher (JARVIS.bat) with one-click start")
    pdf.bullet("Smart LLM fallback: Ollama local -> Groq cloud")

    # ==================== 2. ARCHITECTURE ====================
    pdf.add_page()
    pdf.section_title("2. System Architecture & Pipeline")
    pdf.body_text(
        "JARVIS uses a linear pipeline architecture where audio frames flow through processors "
        "in sequence. Each processor transforms the data and passes it to the next stage."
    )

    pdf.sub_title("Pipeline Flow")
    pdf.code_block(
        "Microphone -> AudioGainFilter -> Silero VAD -> Deepgram STT -> InputStatusMonitor\n"
        "  -> UserContextAggregator -> Groq LLM -> Kokoro TTS -> OutputStatusMonitor\n"
        "  -> Speaker -> AssistantContextAggregator"
    )

    pdf.sub_title("Data Flow")
    pdf.body_text(
        "1. AUDIO IN: Microphone captures raw PCM audio (16kHz, 16-bit). The AudioGainFilter "
        "boosts volume 15x and converts stereo to mono if needed.\n\n"
        "2. VAD: Silero Voice Activity Detection determines when the user starts and stops speaking. "
        "Configured with 0.7 confidence, 0.3s start threshold, 0.8s stop threshold.\n\n"
        "3. STT: Deepgram Nova-3 transcribes speech to text in real-time via WebSocket streaming.\n\n"
        "4. LLM: Groq (llama-3.1-8b-instant) processes the text, decides whether to respond directly "
        "or call a tool (web search, open app, etc). Tool results are fed back to the LLM.\n\n"
        "5. TTS: Kokoro synthesizes the LLM's text response into 24kHz speech audio locally on GPU.\n\n"
        "6. AUDIO OUT: The synthesized speech is played through the selected output device."
    )

    # ==================== 3. PIPELINE DIAGRAM ====================
    pdf.add_page()
    pdf.section_title("3. Pipeline Diagram")
    pdf.ln(5)

    # Draw the pipeline diagram
    start_y = pdf.get_y() + 5

    # Row 1: Input chain
    colors = {
        "audio": (46, 204, 113),     # green
        "vad": (155, 89, 182),        # purple
        "stt": (52, 152, 219),        # blue
        "llm": (231, 76, 60),         # red
        "tts": (241, 196, 15),        # yellow
        "output": (46, 204, 113),     # green
        "monitor": (149, 165, 166),   # gray
        "tool": (230, 126, 34),       # orange
    }

    bw, bh = 32, 16  # box width, height

    # Row 1
    r1y = start_y
    pdf.diagram_box(10, r1y, bw+5, bh, "Microphone", colors["audio"])
    pdf.diagram_arrow(10+bw+5, r1y+bh/2, 52, r1y+bh/2)
    pdf.diagram_box(54, r1y, bw+8, bh, "Gain Filter", colors["audio"])
    pdf.diagram_arrow(54+bw+8, r1y+bh/2, 97, r1y+bh/2)
    pdf.diagram_box(99, r1y, bw+5, bh, "Silero VAD", colors["vad"])
    pdf.diagram_arrow(99+bw+5, r1y+bh/2, 141, r1y+bh/2)
    pdf.diagram_box(143, r1y, bw+13, bh, "Deepgram STT", colors["stt"])

    pdf.label_text(10, r1y + bh + 2, "16kHz PCM audio", 7)
    pdf.label_text(54, r1y + bh + 2, "15x boost + mono", 7)
    pdf.label_text(99, r1y + bh + 2, "Speech detect", 7)
    pdf.label_text(143, r1y + bh + 2, "Nova-3 streaming", 7)

    # Arrow down from STT to row 2
    pdf.diagram_arrow(165, r1y + bh, 165, r1y + bh + 18)

    # Row 2
    r2y = r1y + bh + 20
    pdf.diagram_box(10, r2y, bw+10, bh, "Input Monitor", colors["monitor"])
    pdf.diagram_arrow(10+bw+10, r2y+bh/2, 57, r2y+bh/2)
    pdf.diagram_box(59, r2y, bw+10, bh, "Context Agg.", colors["monitor"])
    pdf.diagram_arrow(59+bw+10, r2y+bh/2, 106, r2y+bh/2)
    pdf.diagram_box(108, r2y, bw+13, bh, "Groq LLM", colors["llm"])

    # Arrow from STT down-left to Input Monitor
    pdf.diagram_arrow(165, r1y + bh + 18, 35, r2y)

    pdf.label_text(10, r2y + bh + 2, "UI status updates", 7)
    pdf.label_text(59, r2y + bh + 2, "Build messages", 7)
    pdf.label_text(108, r2y + bh + 2, "llama-3.1-8b", 7)

    # Tool box branching from LLM
    pdf.diagram_box(155, r2y - 3, bw+12, bh+6, "V2A Tools", colors["tool"])
    pdf.diagram_arrow(108+bw+13, r2y+bh/2, 155, r2y+bh/2)
    pdf.label_text(155, r2y + bh + 5, "Search, Apps,", 7)
    pdf.label_text(155, r2y + bh + 10, "Files, Commands", 7)

    # Arrow down from LLM to row 3
    pdf.diagram_arrow(125, r2y + bh, 125, r2y + bh + 18)

    # Row 3
    r3y = r2y + bh + 20
    pdf.diagram_box(10, r3y, bw+10, bh, "Kokoro TTS", colors["tts"])
    pdf.diagram_arrow(10+bw+10, r3y+bh/2, 57, r3y+bh/2)
    pdf.diagram_box(59, r3y, bw+13, bh, "Output Monitor", colors["monitor"])
    pdf.diagram_arrow(59+bw+13, r3y+bh/2, 109, r3y+bh/2)
    pdf.diagram_box(111, r3y, bw+5, bh, "Speaker", colors["audio"])

    # Arrow from LLM down-left to TTS
    pdf.diagram_arrow(125, r2y + bh + 18, 35, r3y)

    pdf.label_text(10, r3y + bh + 2, "Local GPU, 24kHz", 7)
    pdf.label_text(59, r3y + bh + 2, "UI status updates", 7)
    pdf.label_text(111, r3y + bh + 2, "Audio output", 7)

    # Legend
    ly = r3y + bh + 20
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(10, ly)
    pdf.cell(0, 5, "Legend:")
    ly += 7
    legend_items = [
        ("Audio I/O", colors["audio"]),
        ("VAD", colors["vad"]),
        ("Speech-to-Text", colors["stt"]),
        ("LLM (Brain)", colors["llm"]),
        ("Text-to-Speech", colors["tts"]),
        ("V2A Tools", colors["tool"]),
        ("Monitors", colors["monitor"]),
    ]
    lx = 10
    for label, color in legend_items:
        pdf.set_fill_color(*color)
        pdf.rect(lx, ly, 6, 4, style="F")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.set_xy(lx + 7, ly - 0.5)
        pdf.cell(0, 5, label)
        lx += 30 if len(label) < 8 else 35

    # ==================== 4. COMPONENT DETAILS ====================
    pdf.add_page()
    pdf.section_title("4. Component Details")

    components = [
        ("Deepgram STT (Speech-to-Text)",
         "Model: Nova-3 (latest, 54% better WER than Nova-2)\n"
         "Protocol: WebSocket streaming for real-time transcription\n"
         "Language: English\n"
         "API: Cloud-based, ~$0.0043/min, ~$199 credit remaining"),
        ("Groq LLM (Large Language Model)",
         "Model: llama-3.1-8b-instant (fast, free tier)\n"
         "Fallback: Ollama local (qwen3:8b) if available\n"
         "Features: Tool calling for V2A actions\n"
         "Latency: ~150ms time-to-first-token via Groq cloud"),
        ("Kokoro TTS (Text-to-Speech)",
         "Engine: ONNX-based local inference on GPU\n"
         "Voice: af_heart (female, natural)\n"
         "Output: 24kHz audio\n"
         "Model: ~300MB cached at ~/.cache/kokoro-onnx/"),
        ("Silero VAD (Voice Activity Detection)",
         "Model: Silero VAD (PyTorch, runs on CPU)\n"
         "Confidence threshold: 0.7\n"
         "Start detection: 0.3 seconds\n"
         "Stop detection: 0.8 seconds\n"
         "Minimum volume: 0.15"),
        ("AudioGainFilter",
         "Runs inside transport BEFORE VAD\n"
         "Stereo mics: extracts left channel, outputs mono\n"
         "Mono mics: passes through directly\n"
         "Gain: 15x amplification\n"
         "Critical: must output mono bytes for VAD to work"),
    ]
    for title, desc in components:
        pdf.sub_title(title)
        pdf.body_text(desc)

    # ==================== 5. AUDIO PROCESSING ====================
    pdf.add_page()
    pdf.section_title("5. Audio Processing")
    pdf.body_text(
        "Audio processing was the most challenging part of the build. Different microphones "
        "behave differently on Windows, and the pipeline requires specific audio formats."
    )

    pdf.sub_title("The Realtek Stereo Problem")
    pdf.body_text(
        "The built-in Realtek microphone (common on most PCs) records in stereo (2 channels) "
        "even though it's a single microphone. When forced to record in mono (1 channel), it "
        "produces empty or noisy audio that speech recognition cannot process. The solution: "
        "record in stereo and extract the left channel programmatically."
    )

    pdf.sub_title("USB Headset Solution")
    pdf.body_text(
        "USB headsets (like the user's USB Audio Device) record natively in mono (1 channel). "
        "They work correctly with mono recording - no channel extraction needed. The "
        "AudioGainFilter auto-detects the input channel count and handles both cases."
    )

    pdf.sub_title("Audio Format Requirements")
    pdf.code_block(
        "Transport Input:  16kHz, 16-bit PCM, stereo or mono\n"
        "After Filter:     16kHz, 16-bit PCM, MUST be mono\n"
        "VAD Input:        mono audio bytes (Silero expects mono)\n"
        "STT Input:        mono audio via WebSocket to Deepgram\n"
        "TTS Output:       24kHz, 16-bit PCM (Kokoro)\n"
        "Speaker Output:   resampled to device native rate"
    )

    pdf.sub_title("Critical Discovery")
    pdf.body_text(
        "IMPORTANT: The AudioGainFilter MUST output mono bytes even when the transport records "
        "in stereo. Outputting stereo-duplicated audio (interleaving L,R,L,R) completely breaks "
        "Silero VAD detection because it interprets the interleaved samples as mono, doubling "
        "the apparent frequency and confusing the model."
    )

    # ==================== 6. V2A TOOLS ====================
    pdf.add_page()
    pdf.section_title("6. Voice-to-Action (V2A) Tools")
    pdf.body_text(
        "JARVIS includes 5 tools that allow the LLM to take real-world actions based on voice commands. "
        "Tools are registered with the LLM via Pipecat's FunctionSchema system."
    )

    tools = [
        ("search_web", "Searches the internet using Brave Search API. Falls back to DuckDuckGo "
         "instant answers if no API key. Returns top 3 results formatted for speech. Results "
         "are also printed to terminal with URLs."),
        ("open_application", "Opens desktop apps by name on Windows. Supports 20+ apps: Chrome, "
         "Discord, Notepad, Spotify, VS Code, File Explorer, Calculator, Word, Excel, Outlook, "
         "Teams, Paint, Task Manager, Settings, and more. Uses Windows 'start' command."),
        ("open_url", "Opens any URL in the user's default web browser using Python's webbrowser module."),
        ("read_file", "Reads file contents from the local filesystem. Limited to 50KB for safety. "
         "Returns the file content to the LLM for summarization."),
        ("run_command", "Executes Windows shell commands with a 15-second timeout. Returns stdout "
         "on success, stderr on failure. Useful for system info, process management, etc."),
    ]
    for name, desc in tools:
        pdf.sub_title(f"Tool: {name}")
        pdf.body_text(desc)

    # ==================== 7. DESKTOP INTEGRATION ====================
    pdf.add_page()
    pdf.section_title("7. Desktop Integration")

    pdf.sub_title("JARVIS.bat Launcher")
    pdf.body_text(
        "A batch file on the Desktop provides one-click launching. It activates the Python "
        "virtual environment, sets the console to UTF-8, displays an ASCII art banner, and "
        "runs the voice agent."
    )
    pdf.code_block(
        "Location: C:\\Users\\PC\\Desktop\\JARVIS.bat\n"
        "Action:   cd voice-agent -> activate venv -> python bot.py"
    )

    pdf.sub_title("Status Overlay (ui.py)")
    pdf.body_text(
        "A floating tkinter window shows the agent's current state in real-time. It's always-on-top, "
        "draggable, positioned at the top-right of the screen, and updates via a thread-safe queue."
    )
    pdf.body_text("States displayed:")
    pdf.bullet("STARTING - Pipeline initializing")
    pdf.bullet("LIVE - Ready, waiting for speech")
    pdf.bullet("LISTENING - User is speaking (blue pulse)")
    pdf.bullet("THINKING - Processing speech / running tools (yellow)")
    pdf.bullet("SPEAKING - TTS output playing (green)")
    pdf.bullet("ERROR - Something went wrong (red)")

    pdf.sub_title("Audio Device Picker")
    pdf.body_text(
        "On startup, JARVIS shows an interactive menu of connected audio devices. It probes each "
        "device to verify it's actually connected (filters out ghost Bluetooth devices). Shows "
        "stereo/mono labels. User selects input (mic) and output (speakers) by number."
    )

    # ==================== 8. CONFIGURATION ====================
    pdf.add_page()
    pdf.section_title("8. Configuration & API Keys")
    pdf.body_text("All configuration is in voice-agent/.env:")
    pdf.code_block(
        "# LLM - Groq (free tier, cloud)\n"
        "GROQ_API_KEY=gsk_xxxxx\n"
        "GROQ_MODEL=llama-3.1-8b-instant\n\n"
        "# Speech-to-Text - Deepgram\n"
        "DEEPGRAM_API_KEY=xxxxx\n\n"
        "# Web Search - Brave\n"
        "BRAVE_API_KEY=xxxxx\n\n"
        "# Local LLM (optional)\n"
        "OLLAMA_BASE_URL=http://localhost:11434\n"
        "OLLAMA_MODEL=qwen3:8b\n\n"
        "# Audio\n"
        "AUDIO_GAIN=15.0"
    )

    pdf.sub_title("LLM Selection Priority")
    pdf.body_text(
        "1. Ollama (local) - checked first. Uses qwen3:8b if available. Fully offline, free.\n"
        "2. Groq (cloud) - fallback. Uses llama-3.1-8b-instant. Free tier with rate limits.\n"
        "3. Exit with error if neither is available."
    )

    # ==================== 9. FILE STRUCTURE ====================
    pdf.add_page()
    pdf.section_title("9. File Structure")
    pdf.code_block(
        "vanos/\n"
        "  voice-agent/\n"
        "    bot.py          Main pipeline - AudioGainFilter, StatusMonitors,\n"
        "                    LLM selection, device picker, pipeline creation\n"
        "    tools.py        V2A tool definitions and handlers\n"
        "    ui.py           Tkinter floating status overlay\n"
        "    server.py       FastAPI WebSocket server (future)\n"
        "    .env            API keys and configuration\n"
        "    .env.example    Template for new setups\n"
        "    requirements.txt  Python dependencies\n"
        "    .gitignore      Excludes .env, venv, __pycache__\n"
        "    venv/           Python 3.13.7 virtual environment\n"
        "  vanos.pdf         Original BUILD YOUR OWN JARVIS guide\n"
        "  JARVIS_Documentation.pdf  This document"
    )

    pdf.sub_title("Key Dependencies")
    pdf.code_block(
        "pipecat-ai[silero,google,kokoro]  Pipeline framework\n"
        "pipecat-ai-services-deepgram      Speech-to-text\n"
        "pipecat-ai-services-groq          Groq LLM integration\n"
        "aiohttp                           Async HTTP for web search\n"
        "python-dotenv                     Environment variables\n"
        "pyaudio                           Audio device access\n"
        "loguru                            Structured logging"
    )

    # ==================== 10. CHALLENGES ====================
    pdf.section_title("10. Challenges & Solutions")
    challenges = [
        ("Stereo Mic Recording",
         "Realtek mic only works in stereo mode. Mono recording produces empty audio. "
         "Solution: Record stereo, extract left channel in AudioGainFilter."),
        ("VAD Breaking with Stereo Output",
         "Outputting stereo-duplicated bytes from the filter confused Silero VAD completely. "
         "Solution: Always output mono bytes from the filter, regardless of input format."),
        ("Pipecat API Deprecations",
         "Pipecat 0.0.108 has many deprecated APIs. @llm.function() decorator doesn't exist, "
         "OpenAILLMContext is deprecated, tool registration uses old signature. "
         "Solution: Use working deprecated APIs with warnings suppressed."),
        ("Ghost Bluetooth Devices",
         "Windows shows previously-paired Bluetooth audio devices even when disconnected. "
         "Solution: Probe each device with pa.open(start=False) to test actual connectivity."),
        ("Groq Rate Limits",
         "Free tier allows 100K tokens/day on llama-3.3-70b. "
         "Solution: Switch to llama-3.1-8b-instant which has separate limits."),
        ("LLM Speaking Function Syntax",
         "LLM would output raw XML function call text instead of using tool API. "
         "Solution: Added explicit system prompt rules + dedicated open_application tool."),
    ]
    for title, desc in challenges:
        pdf.sub_title(title)
        pdf.body_text(desc)

    # ==================== 11. FUTURE UPGRADES ====================
    pdf.add_page()
    pdf.section_title("11. Future Upgrades")

    pdf.sub_title("Recommended API Upgrades")
    pdf.body_text(
        "The current free-tier setup works but has limitations. For production quality:"
    )

    # Upgrade table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(45, 8, " Component", fill=True)
    pdf.cell(55, 8, " Current (Free)", fill=True)
    pdf.cell(55, 8, " Recommended Upgrade", fill=True)
    pdf.cell(35, 8, " Est. Cost", fill=True, new_x="LMARGIN", new_y="NEXT")

    rows = [
        ("LLM", "Groq 8B", "Anthropic Claude / GPT-4o", "$3-5/M tokens"),
        ("STT", "Deepgram Nova-3", "Keep (already best)", "$0.0043/min"),
        ("TTS", "Kokoro (local)", "ElevenLabs", "$5/mo starter"),
        ("Search", "Brave API", "Keep (works great)", "Free tier"),
    ]
    pdf.set_font("Helvetica", "", 9)
    for i, (comp, current, upgrade, cost) in enumerate(rows):
        bg = (245, 245, 245) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(45, 7, f" {comp}", fill=True)
        pdf.cell(55, 7, f" {current}", fill=True)
        pdf.cell(55, 7, f" {upgrade}", fill=True)
        pdf.cell(35, 7, f" {cost}", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.sub_title("Feature Roadmap")
    pdf.bullet("Pull Ollama qwen3:8b for fully offline operation")
    pdf.bullet("Browser-based frontend via server.py WebSocket server")
    pdf.bullet("Conversation memory and context persistence")
    pdf.bullet("Multi-language support (Deepgram Nova-3 supports 12+ languages)")
    pdf.bullet("Wake word detection ('Hey JARVIS')")
    pdf.bullet("Screen capture and visual understanding")
    pdf.bullet("Calendar integration and email composition")
    pdf.bullet("Smart home device control")

    pdf.ln(10)
    pdf.set_draw_color(41, 128, 185)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 8, "JARVIS - Built with Pipecat AI, Deepgram, Groq, and Kokoro", align="C")

    # Save
    output_path = os.path.join(os.path.dirname(__file__), "JARVIS_Documentation.pdf")
    pdf.output(output_path)
    print(f"\nPDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf()
