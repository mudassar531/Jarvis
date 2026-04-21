"""
JARVIS Status Overlay — Floating always-on-top status indicator.
Shows agent state: LIVE, LISTENING, THINKING, SPEAKING.
Runs tkinter in a background thread so it doesn't block the async pipeline.
"""

import queue
import threading
import tkinter as tk


# States and their visual config: (label, bg_color, fg_color, emoji)
STATES = {
    "starting": ("  STARTING...  ", "#333333", "#AAAAAA", "⏳"),
    "live":     ("  ● JARVIS LIVE  ", "#1a1a2e", "#00ff88", "🟢"),
    "listening":("  🎙️ LISTENING  ", "#1a1a2e", "#00ccff", "🎙️"),
    "thinking": ("  🧠 THINKING   ", "#1a1a2e", "#ffaa00", "🧠"),
    "speaking": ("  🔊 SPEAKING   ", "#1a1a2e", "#ff6699", "🔊"),
    "error":    ("  ⚠ ERROR       ", "#4a0000", "#ff4444", "⚠️"),
}


class StatusOverlay:
    """Thread-safe floating status window."""

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._label: tk.Label | None = None
        self._transcript_label: tk.Label | None = None
        self._running = False

    def start(self):
        """Launch the overlay in a daemon thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()

    def update(self, state: str, transcript: str = ""):
        """Queue a state update (thread-safe)."""
        self._queue.put((state, transcript))

    def stop(self):
        self._running = False
        self._queue.put(("_quit", ""))

    def _run_tk(self):
        root = tk.Tk()
        self._root = root
        root.title("JARVIS")
        root.overrideredirect(True)  # No title bar
        root.attributes("-topmost", True)  # Always on top
        root.attributes("-alpha", 0.92)
        root.configure(bg="#1a1a2e")

        # Position top-right of screen
        screen_w = root.winfo_screenwidth()
        x = screen_w - 340
        y = 20
        root.geometry(f"320x100+{x}+{y}")

        # Make it draggable
        self._drag_data = {"x": 0, "y": 0}
        root.bind("<Button-1>", self._on_drag_start)
        root.bind("<B1-Motion>", self._on_drag_motion)

        # Rounded appearance via a frame
        frame = tk.Frame(root, bg="#1a1a2e", padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        self._label = tk.Label(
            frame,
            text="  ⏳ STARTING...  ",
            font=("Segoe UI", 16, "bold"),
            bg="#1a1a2e",
            fg="#AAAAAA",
            anchor="w",
        )
        self._label.pack(fill=tk.X, pady=(5, 0))

        # Transcript/subtitle label
        self._transcript_label = tk.Label(
            frame,
            text="Initializing pipeline...",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#666688",
            anchor="w",
            wraplength=300,
        )
        self._transcript_label.pack(fill=tk.X, pady=(0, 5))

        # Poll the queue every 100ms
        self._poll_queue()
        root.mainloop()

    def _poll_queue(self):
        try:
            while True:
                state, transcript = self._queue.get_nowait()
                if state == "_quit":
                    self._root.destroy()
                    return
                if state in STATES:
                    label_text, bg, fg, _ = STATES[state]
                    self._label.config(text=label_text, fg=fg, bg=bg)
                    self._root.configure(bg=bg)
                    # Update all child backgrounds
                    for w in self._root.winfo_children():
                        w.configure(bg=bg)
                        for c in w.winfo_children():
                            c.configure(bg=bg)
                if transcript:
                    self._transcript_label.config(text=transcript)
        except queue.Empty:
            pass
        if self._running and self._root:
            self._root.after(100, self._poll_queue)

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        x = self._root.winfo_x() + event.x - self._drag_data["x"]
        y = self._root.winfo_y() + event.y - self._drag_data["y"]
        self._root.geometry(f"+{x}+{y}")
