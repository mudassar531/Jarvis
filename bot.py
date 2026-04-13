"""
JARVIS — Voice Agent Neural Operating System
An AI layer on top of Windows with voice control, computer use,
persistent memory, context awareness, and system tray always-on mode.
Pipeline: Silero VAD → Deepgram STT → Gemini 2.5 Flash → Kokoro TTS
"""

import asyncio
import os
import struct
import sys

import warnings

from dotenv import load_dotenv
from loguru import logger

warnings.filterwarnings("ignore", category=DeprecationWarning)

from pipecat.audio.filters.base_audio_filter import BaseAudioFilter
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    Frame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

from tools import get_tools, handle_tool_call
from ui import StatusOverlay
from memory import (
    start_conversation, save_message, end_conversation,
    summarize_conversation, build_memory_context, save_fact, get_memory_stats,
)
from context import build_context_string

load_dotenv()

AUDIO_GAIN = float(os.getenv("AUDIO_GAIN", "15.0"))

# Global overlay instance
overlay = StatusOverlay()

# Global conversation tracking
current_conv_id = None


class AudioGainFilter(BaseAudioFilter):
    """Transport-level filter: optional stereo→mono + gain boost. Runs BEFORE VAD."""

    def __init__(self, gain: float = 15.0, input_channels: int = 2):
        self._gain = gain
        self._input_channels = input_channels
        self._frame_count = 0

    async def start(self, sample_rate: int):
        logger.info(f"AudioGainFilter started (gain={self._gain}x, ch={self._input_channels}, rate={sample_rate})")

    async def stop(self):
        pass

    async def process_frame(self, frame):
        pass

    async def filter(self, audio: bytes) -> bytes:
        self._frame_count += 1
        n = len(audio) // 2
        samples = struct.unpack(f"<{n}h", audio)

        if self._input_channels >= 2:
            # Stereo: extract left channel
            mono = samples[0::2]
        else:
            # Already mono
            mono = samples

        m = len(mono)
        g = self._gain
        boosted = [max(-32768, min(32767, int(s * g))) for s in mono]

        if self._frame_count % 200 == 1:
            peak_in = max(abs(s) for s in mono) if mono else 0
            peak_out = max(abs(s) for s in boosted) if boosted else 0
            logger.info(f"🎤 frame#{self._frame_count} peak {peak_in}→{peak_out} ({m} samples)")

        return struct.pack(f"<{m}h", *boosted)


BASE_SYSTEM_PROMPT = """You are JARVIS, a Voice Agent Neural Operating System. You are an always-on AI assistant that lives on the user's Windows PC.

Your personality:
- Concise and natural — this is a spoken conversation, not text chat
- Confident and helpful, like a knowledgeable colleague
- You speak in short, clear sentences (2-3 max per response unless asked for detail)
- Never use bullet points, markdown, or formatting — everything is spoken aloud
- You remember past conversations and learn about the user over time

CRITICAL RULES:
- NEVER write function calls, XML tags, or code in your responses. Your text is spoken aloud by TTS.
- When you want to use a tool, use the tool calling mechanism. Do NOT write out function names or parameters in your speech.
- If a tool call succeeds, just tell the user the result naturally, like "Done, I opened Chrome for you."
- If you cannot do something, just say so. Never try to fake a tool call by writing it as text.

Your tools:
- youtube_search: INSTANT — search YouTube and open results. Use when user says "play", "search YouTube", "find a song/video".
- google_search_browse: INSTANT — open Google search in browser.
- open_application: INSTANT — open any app (Chrome, Discord, Notepad, etc.)
- open_url: INSTANT — open any URL in browser
- search_web: Search the internet and tell the user the answer (no browser needed)
- read_file: Read a file from the computer
- run_command: Run a system command on Windows
- computer_use: SLOW but powerful — sees the screen and clicks/types. Use ONLY when you need to interact with what's already on screen (click a button, select a video, fill a form).
- take_screenshot: See what's on screen right now.
- save_memory: Save an important fact or preference the user tells you.
- send_email: Draft an email to someone. Looks up their name in contacts. ALWAYS read back the draft and ask for confirmation.
- confirm_send_email: Send the drafted email ONLY after user confirms.
- cancel_email: Cancel the pending draft if user says no.
- read_inbox: Read latest emails from Gmail.
- add_contact: Save someone's email for future use.
- list_contacts: Show all saved contacts.

WHEN TO USE WHICH TOOL:
- "Search YouTube for Bohemian Rhapsody": use youtube_search (instant)
- "Play the first video": use computer_use (needs to see screen and click)
- "Open Chrome": use open_application (instant)
- "Go to gmail.com": use open_url (instant)
- "Click that button": use computer_use (needs screen vision)
- "What's on my screen?": use take_screenshot
- "What's the weather?": use search_web
- "Remember that I like dark mode": use save_memory
- "Send email to Ahmed about the meeting": use send_email
- "Yes send it" / "Go ahead": use confirm_send_email
- "No don't send it": use cancel_email
- "Check my email" / "Read my inbox": use read_inbox
- "Ahmed's email is ahmed@gmail.com": use add_contact
- "Who's in my contacts?": use list_contacts

EMAIL RULES (CRITICAL):
1. When user says "send email to [name]", use send_email to draft it.
2. Compose a professional, well-written body based on what the user wants to say.
3. ALWAYS read back: the recipient, subject, and a brief body summary.
4. ALWAYS ask "Shall I send it?" and wait for confirmation.
5. Only call confirm_send_email when user explicitly says yes/send/go ahead.
6. If the contact name is not found, ask the user for their email address.
7. If user provides an email, save it with add_contact for next time.

ALWAYS prefer instant tools over computer_use. Only use computer_use when you actually need to SEE and CLICK on screen elements.
When using tools, briefly tell the user what you're doing then report the result conversationally.
Always prioritize accuracy. If you're not sure about facts, search the web first.

MEMORY: You have persistent memory. You remember facts about the user and past conversations. Use this knowledge naturally — greet them by name, reference past topics, etc. When the user tells you something personal (name, preferences, habits), use save_memory to remember it."""


def build_system_prompt() -> str:
    """Build system prompt with dynamic memory and context."""
    parts = [BASE_SYSTEM_PROMPT]

    # Inject memory
    memory_ctx = build_memory_context()
    if memory_ctx:
        parts.append(f"\n\n--- YOUR MEMORY ---\n{memory_ctx}")

    # Inject context
    context_str = build_context_string()
    if context_str:
        parts.append(f"\n\n--- CURRENT CONTEXT ---\n{context_str}")

    return "\n".join(parts)


class InputStatusMonitor(FrameProcessor):
    """Watches input-side frames: VAD events and transcriptions. Saves to memory."""

    def __init__(self, overlay_ref: StatusOverlay, **kwargs):
        super().__init__(**kwargs)
        self._overlay = overlay_ref

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            self._overlay.update("listening", "Listening...")
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._overlay.update("thinking", "Processing speech...")
        elif isinstance(frame, TranscriptionFrame):
            text = frame.text if hasattr(frame, "text") else ""
            if text:
                self._overlay.update("thinking", f'You: "{text}"')
                # Save to memory
                if current_conv_id:
                    save_message(current_conv_id, "user", text)

        await self.push_frame(frame, direction)


class OutputStatusMonitor(FrameProcessor):
    """Watches output-side frames: TTS started/stopped."""

    def __init__(self, overlay_ref: StatusOverlay, **kwargs):
        super().__init__(**kwargs)
        self._overlay = overlay_ref

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TTSStartedFrame):
            self._overlay.update("speaking", "Speaking...")
        elif isinstance(frame, TTSStoppedFrame):
            self._overlay.update("live", "Say something — I'm listening!")

        await self.push_frame(frame, direction)


def get_llm_service():
    """Pick LLM: Google Gemini (best) > Ollama (local) > Groq (cloud free tier)."""

    # 1. Google Gemini — best option (fast, great tool calling, paid = no limits)
    google_key = os.getenv("GOOGLE_CREDENTIALS", "")
    if google_key and google_key != "YOUR_KEY_HERE":
        from pipecat.services.google.llm import GoogleLLMService
        google_model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        logger.info(f"Using CLOUD LLM: Google Gemini ({google_model})")
        return GoogleLLMService(api_key=google_key, model=google_model)

    # 2. Ollama — local, free, private
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    try:
        import urllib.request
        import json as _json
        urllib.request.urlopen(f"{ollama_url}/api/version", timeout=2)
        resp = urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5)
        tags = _json.loads(resp.read())
        model_names = [m.get("name", "") for m in tags.get("models", [])]
        found = any(ollama_model in name for name in model_names)
        if not found:
            logger.warning(f"Ollama running but model '{ollama_model}' not found. Available: {model_names}")
            raise RuntimeError("Model not available")
        from pipecat.services.ollama.llm import OLLamaLLMService
        logger.info(f"Using LOCAL LLM: Ollama ({ollama_model})")
        return OLLamaLLMService(
            settings=OLLamaLLMService.Settings(model=ollama_model),
            base_url=f"{ollama_url}/v1",
        )
    except Exception:
        pass

    # 3. Groq — cloud free tier fallback
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and groq_key != "YOUR_KEY_HERE":
        from pipecat.services.groq.llm import GroqLLMService
        groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        logger.info(f"Using CLOUD LLM: Groq ({groq_model})")
        return GroqLLMService(api_key=groq_key, model=groq_model)

    logger.error("No LLM available! Set GOOGLE_CREDENTIALS or GROQ_API_KEY in .env")
    sys.exit(1)


async def _tool_handler(function_name, tool_call_id, args, llm, context, result_callback):
    """Universal handler for all tool calls."""
    overlay.update("thinking", f"Running tool: {function_name}")
    if function_name == "computer_use":
        # Pass status callback so computer_use can update the overlay
        from computer_use import run_computer_use
        result = await run_computer_use(args.get("task", ""), status_callback=overlay.update)
    else:
        result = await handle_tool_call(function_name, args)
    overlay.update("speaking", f"Tool done: {function_name}")
    await result_callback(result)


def _is_device_usable(pa, index, is_input):
    """Test if a device is actually connected by trying to open it briefly."""
    import pyaudio
    try:
        d = pa.get_device_info_by_index(index)
        channels = d["maxInputChannels"] if is_input else d["maxOutputChannels"]
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=min(channels, 2),
            rate=int(d["defaultSampleRate"]),
            input=is_input,
            output=not is_input,
            input_device_index=index if is_input else None,
            output_device_index=index if not is_input else None,
            frames_per_buffer=512,
            start=False,
        )
        stream.close()
        return True
    except Exception:
        return False


def pick_audio_devices():
    """Interactive device picker — only shows currently connected devices.
    Returns (input_idx, output_idx, input_channels)."""
    import pyaudio
    pa = pyaudio.PyAudio()

    print("\n╔══════════════════════════════════════╗")
    print("║      🎧 JARVIS Audio Device Setup     ║")
    print("╚══════════════════════════════════════╝\n")

    # --- Input devices (deduplicated, active only) ---
    seen_names = set()
    inputs = []
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if d["maxInputChannels"] <= 0:
            continue
        name = d["name"]
        if "mapper" in name.lower() or "primary" in name.lower():
            continue
        if name in seen_names:
            continue
        if not _is_device_usable(pa, i, is_input=True):
            continue
        seen_names.add(name)
        inputs.append((i, name, d["maxInputChannels"], int(d["defaultSampleRate"])))

    print("  🎙️  INPUT DEVICES (microphone):")
    for idx, (dev_i, name, ch, rate) in enumerate(inputs):
        ch_label = "stereo" if ch >= 2 else "mono"
        print(f"    [{idx+1}] {name} ({ch_label})")
    if not inputs:
        print("    No input devices found!")

    choice = input(f"\n  Select input [{1}-{len(inputs)}] (Enter = first): ").strip()
    if choice and choice.isdigit() and 1 <= int(choice) <= len(inputs):
        sel = inputs[int(choice) - 1]
    else:
        sel = inputs[0] if inputs else (None, "unknown", 1, 16000)
    in_idx, in_name, in_channels, _ = sel
    print(f"  ✓ Input: {in_name}\n")

    # --- Output devices (deduplicated, active only) ---
    seen_names = set()
    outputs = []
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if d["maxOutputChannels"] <= 0:
            continue
        name = d["name"]
        if "mapper" in name.lower() or "primary" in name.lower():
            continue
        if name in seen_names:
            continue
        if not _is_device_usable(pa, i, is_input=False):
            continue
        seen_names.add(name)
        outputs.append((i, name, d["maxOutputChannels"]))

    print("  🔊  OUTPUT DEVICES (speakers/headphones):")
    for idx, (dev_i, name, ch) in enumerate(outputs):
        print(f"    [{idx+1}] {name}")
    if not outputs:
        print("    No output devices found!")

    choice = input(f"\n  Select output [{1}-{len(outputs)}] (Enter = first): ").strip()
    if choice and choice.isdigit() and 1 <= int(choice) <= len(outputs):
        out_idx = outputs[int(choice) - 1][0]
    else:
        out_idx = outputs[0][0] if outputs else None
    out_name = next((name for i, name, *_ in outputs if i == out_idx), "system default") if out_idx else "system default"
    print(f"  ✓ Output: {out_name}\n")

    pa.terminate()
    return in_idx, out_idx, in_channels


async def create_pipeline(in_device=None, out_device=None, in_channels=2, transport=None):
    """Create the voice agent pipeline. Accepts optional transport for server mode."""

    if transport is None:
        # Use stereo recording + mono extraction for stereo-only mics (Realtek)
        # Use mono recording + gain for mono mics (USB headsets)
        use_stereo = in_channels >= 2
        audio_filter = AudioGainFilter(gain=AUDIO_GAIN, input_channels=in_channels)
        vad = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.7,
                start_secs=0.3,
                stop_secs=0.8,
                min_volume=0.15,
            )
        )
        params = LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_in_channels=2 if use_stereo else 1,
            audio_in_filter=audio_filter,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=vad,
            vad_audio_passthrough=True,
        )
        if in_device is not None:
            params.input_device_index = in_device
        if out_device is not None:
            params.output_device_index = out_device
        transport = LocalAudioTransport(params)
        logger.info(f"Audio: {'stereo→mono' if use_stereo else 'mono'} recording, gain={AUDIO_GAIN}x")

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-3",
        language="en",
    )

    llm = get_llm_service()

    tts = KokoroTTSService(voice_id="af_heart")

    tools = get_tools()
    system_prompt = build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    context = OpenAILLMContext(messages, tools=tools)
    context_aggregator = llm.create_context_aggregator(context)

    # Log memory stats
    stats = get_memory_stats()
    logger.info(f"🧠 Memory loaded: {stats['facts']} facts, {stats['preferences']} preferences, {stats['conversations']} past conversations")

    # Register tool handlers
    for tool in tools.standard_tools:
        llm.register_function(tool.name, _tool_handler)

    input_monitor = InputStatusMonitor(overlay)
    output_monitor = OutputStatusMonitor(overlay)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            input_monitor,
            context_aggregator.user(),
            llm,
            tts,
            output_monitor,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    return pipeline


async def main():
    global current_conv_id

    # Pick audio devices
    in_dev, out_dev, in_ch = pick_audio_devices()

    # Start memory conversation
    current_conv_id = start_conversation()
    stats = get_memory_stats()

    # Start the overlay
    overlay.start()
    overlay.update("starting", "Initializing JARVIS Neural OS...")

    print("\n╔══════════════════════════════════════════╗")
    print("║    🧠 JARVIS Neural Operating System      ║")
    print("║    Voice Agent • Memory • Computer Use    ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  🧠 Memory: {stats['facts']} facts, {stats['conversations']} past conversations")
    print(f"  🤖 LLM: Gemini 2.5 Flash")
    print(f"  🎤 STT: Deepgram Nova-3")
    print(f"  🔊 TTS: Kokoro\n")

    logger.info("Starting JARVIS Neural Operating System...")

    pipeline = await create_pipeline(in_device=in_dev, out_device=out_dev, in_channels=in_ch)
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        idle_timeout_secs=None,
    )

    overlay.update("live", "Say something — I'm listening!")
    logger.info("Pipeline ready. Speak into your microphone.")
    logger.info("Press Ctrl+C to stop.\n")

    runner = PipelineRunner()
    await runner.run(task)


async def shutdown():
    """Graceful shutdown: summarize conversation and save memory."""
    global current_conv_id
    if current_conv_id:
        logger.info("🧠 Summarizing conversation before shutdown...")
        overlay.update("thinking", "Saving memory...")
        try:
            await summarize_conversation(current_conv_id)
            logger.info("🧠 Memory saved successfully.")
        except Exception as e:
            logger.error(f"Memory save failed: {e}")
            end_conversation(current_conv_id, "Session ended (summary failed)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Run shutdown to save memory
        try:
            asyncio.run(shutdown())
        except Exception:
            pass
        overlay.stop()
        logger.info("JARVIS stopped. Memory saved.")
        sys.exit(0)
