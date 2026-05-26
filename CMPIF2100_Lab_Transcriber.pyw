"""CMPIF2100 Lab Transcriber.

Pick a .wav, pick a destination folder, hit Transcribe. Output is saved as
<audio>.txt in the chosen folder, with the Pitt copyright notice appended.

First run installs the packages it needs into the user's site-packages (no
admin rights). If an NVIDIA GPU is present it also grabs the cuBLAS/cuDNN
wheels; otherwise it runs on CPU.
"""
import importlib.util
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "CMPIF2100 Lab Transcriber"
MODEL_NAME = "medium.en"
SUBPROC_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# Appended to every transcript file.
COPYRIGHT_NOTICE = (
    "The contents of this transcript are the exclusive intellectual property "
    "of the University of Pittsburgh and intended for personal use only. "
    "They are not to be distributed, shared, sold, or otherwise transmitted "
    "without the express permission of the University."
)


def _has_nvidia_gpu() -> bool:
    """True if nvidia-smi is on PATH and exits 0."""
    try:
        r = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=5,
            creationflags=SUBPROC_NO_WINDOW,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _required_packages():
    """List of (import_name, pip_name) needed to run on this machine."""
    pkgs = [
        ("truststore", "truststore"),
        ("faster_whisper", "faster-whisper"),
    ]
    # Only fetch the ~1.3 GB CUDA wheels if there's actually a GPU to use.
    # Linux ctranslate2 wheels bundle CUDA differently, so this is win-only.
    if os.name == "nt" and _has_nvidia_gpu():
        pkgs += [
            ("nvidia.cublas", "nvidia-cublas-cu12"),
            ("nvidia.cudnn", "nvidia-cudnn-cu12"),
        ]
    return pkgs


def _missing_packages():
    return [p for p in _required_packages() if importlib.util.find_spec(p[0]) is None]


def _pip_install_cmd(pkg_name):
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    # --user avoids needing admin on all-users Python installs. pip refuses
    # --user inside a venv, so skip it there.
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        cmd.append("--user")
    cmd.append(pkg_name)
    return cmd


def run_install_splash(to_install):
    """Modal splash that installs missing pip packages. Blocks until done."""
    win = tk.Tk()
    win.title(f"{APP_NAME}: First-time setup")
    W, H = 500, 190
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    win.resizable(False, False)
    BG = "#F5F5F7"
    win.configure(bg=BG)

    pad = tk.Frame(win, bg=BG, padx=24, pady=22)
    pad.pack(fill=tk.BOTH, expand=True)

    tk.Label(pad, text="Setting things up...", font=("Segoe UI", 12, "bold"),
             bg=BG, fg="#1C1C1E").pack(anchor="w")
    tk.Label(pad, text="One-time install. May take a few minutes on first run.",
             font=("Segoe UI", 9), bg=BG, fg="#6E6E73").pack(anchor="w", pady=(2, 14))

    status_var = tk.StringVar(value="Preparing...")
    tk.Label(pad, textvariable=status_var, font=("Segoe UI", 9),
             bg=BG, fg="#1C1C1E", anchor="w").pack(fill=tk.X)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Install.Horizontal.TProgressbar",
                    background="#4A90E2", troughcolor="#E5E5EA",
                    bordercolor=BG, lightcolor="#4A90E2", darkcolor="#4A90E2",
                    thickness=10)
    bar = ttk.Progressbar(pad, style="Install.Horizontal.TProgressbar",
                          mode="determinate", maximum=100, length=W - 70)
    bar.pack(fill=tk.X, pady=(8, 0))

    failures = []
    total = len(to_install)

    def worker():
        for idx, (_mod, pip_name) in enumerate(to_install):
            slice_start = (idx / total) * 100
            slice_end = ((idx + 1) / total) * 100
            win.after(0, lambda p=pip_name, i=idx + 1: status_var.set(
                f"Installing {p}  ({i} of {total})..."))
            try:
                proc = subprocess.Popen(
                    _pip_install_cmd(pip_name),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    creationflags=SUBPROC_NO_WINDOW,
                )
                t_start = time.time()
                # Eases toward ~90% of the package's slice while pip runs, so
                # the bar visibly moves during long downloads (cuDNN ~700MB).
                while proc.poll() is None:
                    elapsed = time.time() - t_start
                    eased = 1 - math.exp(-elapsed / 25)
                    cur = slice_start + (slice_end - slice_start) * eased * 0.9
                    win.after(0, lambda v=cur: bar.configure(value=v))
                    time.sleep(0.25)
                rc = proc.wait()
                if rc != 0:
                    try:
                        out = proc.stdout.read() if proc.stdout else ""
                    except Exception:
                        out = ""
                    failures.append((pip_name, (out or "").strip()[-600:] or
                                     f"pip exited with code {rc}"))
            except Exception as e:
                failures.append((pip_name, f"{type(e).__name__}: {e}"))
            win.after(0, lambda v=slice_end: bar.configure(value=v))
        win.after(0, win.destroy)

    threading.Thread(target=worker, daemon=True).start()
    win.protocol("WM_DELETE_WINDOW", lambda: None)  # block close during install
    win.mainloop()

    if failures:
        msg = "Failed to install:\n\n" + "\n\n".join(
            f"* {n}\n{e}" for n, e in failures)
        messagebox.showerror(f"{APP_NAME}: Setup failed", msg)
        sys.exit(1)


def _register_nvidia_dlls() -> bool:
    """Point the Windows loader at the cuBLAS/cuDNN DLLs that came in via
    pip. Without this ctranslate2 can't find them at runtime. No-op when
    not on Windows or when the wheels aren't installed."""
    if not hasattr(os, "add_dll_directory"):
        return False
    try:
        import nvidia  # type: ignore
    except ImportError:
        return False
    found = False
    for sub in ("cublas", "cudnn", "cuda_nvrtc"):
        d = os.path.join(nvidia.__path__[0], sub, "bin")
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                found = True
            except OSError:
                pass
    return found


class App:
    BG = "#F5F5F7"
    CARD = "#FFFFFF"
    BORDER = "#E5E5EA"
    TEXT = "#1C1C1E"
    MUTED = "#6E6E73"
    ACCENT = "#4A90E2"
    ACCENT_HOVER = "#3A7BC8"
    ACCENT_DISABLED = "#B0C7DC"

    def __init__(self, root):
        self.root = root
        self.audio_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")
        self.model = None
        self.device_label = None
        self._build()

    def _build(self):
        root = self.root
        root.title(APP_NAME)
        root.resizable(False, False)
        root.configure(bg=self.BG)
        # Height is computed from content at the end of _build so the window
        # always fits regardless of OS font/DPI settings.
        MIN_W = 720

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.Horizontal.TProgressbar",
                        background=self.ACCENT, troughcolor=self.BORDER,
                        bordercolor=self.BG,
                        lightcolor=self.ACCENT, darkcolor=self.ACCENT,
                        thickness=8)

        # Header
        header = tk.Frame(root, bg=self.BG)
        header.pack(fill=tk.X, padx=20, pady=(16, 0))
        tk.Label(header, text=APP_NAME, font=("Segoe UI", 13, "bold"),
                 bg=self.BG, fg=self.TEXT).pack(anchor="w")

        # Body grid: 2 columns
        body = tk.Frame(root, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 4))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=190)

        # Left column: two stacked field-cards
        left = tk.Frame(body, bg=self.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.columnconfigure(0, weight=1)

        self._field(left, row=0, label="Select .wav audio file",
                    var=self.audio_var, command=self._pick_audio)
        self._field(left, row=1, label="Set destination",
                    var=self.dest_var, command=self._pick_dest, pad_top=True)

        # Right column: Transcribe button (fills both rows)
        self.btn = tk.Button(
            body, text="Transcribe",
            font=("Segoe UI", 12, "bold"),
            bg=self.ACCENT, fg="white",
            activebackground=self.ACCENT_HOVER, activeforeground="white",
            disabledforeground="white",
            bd=0, relief="flat", cursor="hand2",
            command=self._on_transcribe,
        )
        self.btn.grid(row=0, column=1, sticky="nsew")
        self.btn.bind("<Enter>", lambda e: self._btn_hover(True))
        self.btn.bind("<Leave>", lambda e: self._btn_hover(False))

        # Status + always-visible progress bar (sits at the very bottom)
        bot = tk.Frame(root, bg=self.BG)
        bot.pack(fill=tk.X, padx=20, pady=(2, 14))
        tk.Label(bot, textvariable=self.status_var, font=("Segoe UI", 9),
                 bg=self.BG, fg=self.MUTED, anchor="w").pack(fill=tk.X)
        self.progress = ttk.Progressbar(bot, style="App.Horizontal.TProgressbar",
                                        mode="indeterminate", length=MIN_W - 40)
        self.progress.pack(fill=tk.X, pady=(8, 0))

        # Size window to fit content (handles DPI variations) and center it.
        root.update_idletasks()
        W = max(root.winfo_reqwidth(), MIN_W)
        H = root.winfo_reqheight()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

    def _btn_hover(self, on):
        if str(self.btn["state"]) == "disabled":
            return
        self.btn.configure(bg=self.ACCENT_HOVER if on else self.ACCENT)

    def _field(self, parent, *, row, label, var, command, pad_top=False):
        pady = (10, 0) if pad_top else (0, 0)
        card = tk.Frame(parent, bg=self.CARD,
                        highlightthickness=1,
                        highlightbackground=self.BORDER,
                        highlightcolor=self.BORDER)
        card.grid(row=row, column=0, sticky="ew", pady=pady)
        card.columnconfigure(0, weight=1)

        tk.Button(card, text=label, font=("Segoe UI", 10, "bold"),
                  bg=self.CARD, fg=self.ACCENT,
                  activebackground="#EEF4FB", activeforeground=self.ACCENT,
                  bd=0, relief="flat", cursor="hand2",
                  anchor="w", padx=14, pady=8, command=command
                  ).grid(row=0, column=0, sticky="ew")

        display_var = tk.StringVar()

        def sync(*_):
            v = var.get()
            display_var.set(v if v else "(none selected)")
        var.trace_add("write", sync)
        sync()

        tk.Label(card, textvariable=display_var, font=("Segoe UI", 9),
                 bg=self.CARD, fg=self.MUTED, anchor="w",
                 padx=14, wraplength=460, justify="left"
                 ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

    def _pick_audio(self):
        p = filedialog.askopenfilename(
            parent=self.root,
            title="Select .wav audio file",
            filetypes=[
                ("WAV files", "*.wav"),
                ("All audio", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac"),
                ("All files", "*.*"),
            ],
        )
        if not p:
            return
        self.audio_var.set(p)
        # Destination defaults to the audio file's own folder (user can override).
        self.dest_var.set(str(Path(p).parent))

    def _pick_dest(self):
        initial = self.dest_var.get() or (
            str(Path(self.audio_var.get()).parent) if self.audio_var.get() else ""
        )
        kwargs = {"parent": self.root, "title": "Set destination folder"}
        if initial:
            kwargs["initialdir"] = initial
        p = filedialog.askdirectory(**kwargs)
        if p:
            self.dest_var.set(p)

    def _on_transcribe(self):
        audio = self.audio_var.get()
        dest = self.dest_var.get()
        if not audio:
            messagebox.showwarning(APP_NAME, "Please select a .wav audio file first.")
            return
        if not dest:
            messagebox.showwarning(APP_NAME, "Please set a destination folder first.")
            return
        if not Path(audio).is_file():
            messagebox.showerror(APP_NAME, f"Audio file not found:\n{audio}")
            return
        if not Path(dest).is_dir():
            messagebox.showerror(APP_NAME, f"Destination folder does not exist:\n{dest}")
            return

        self.btn.configure(state="disabled", bg=self.ACCENT_DISABLED,
                           text="Transcribing...")
        self.status_var.set("Loading model... (first transcription downloads it)")
        self.progress.start(12)

        # Off the UI thread so the window keeps repainting and the bar animates.
        threading.Thread(target=self._worker, args=(audio, dest), daemon=True).start()

    def _worker(self, audio, dest):
        try:
            # huggingface_hub uses httpx, which doesn't honor SSL_CERT_FILE.
            # truststore makes Python's ssl use the OS cert store so the
            # model download doesn't fail with a verification error.
            import truststore  # type: ignore
            truststore.inject_into_ssl()
            from faster_whisper import WhisperModel  # type: ignore

            if self.model is None:
                gpu_ready = _register_nvidia_dlls()
                if gpu_ready:
                    try:
                        self.root.after(0, lambda: self.status_var.set(
                            "Loading model on GPU..."))
                        self.model = WhisperModel(MODEL_NAME, device="cuda",
                                                  compute_type="float16")
                        self.device_label = "GPU"
                    except Exception:
                        # GPU sometimes fails even when nvidia-smi works
                        # (driver/runtime mismatch). Fall back to CPU.
                        self.root.after(0, lambda: self.status_var.set(
                            "GPU unavailable, using CPU..."))
                        self.model = WhisperModel(MODEL_NAME, device="cpu",
                                                  compute_type="int8")
                        self.device_label = "CPU"
                else:
                    self.root.after(0, lambda: self.status_var.set(
                        "Loading model on CPU..."))
                    self.model = WhisperModel(MODEL_NAME, device="cpu",
                                              compute_type="int8")
                    self.device_label = "CPU"

            self.root.after(0, lambda: self.status_var.set(
                f"Transcribing on {self.device_label}..."))
            t0 = time.time()
            segments, info = self.model.transcribe(
                audio, beam_size=5, language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            lines = [s.text.strip() for s in segments if s.text and s.text.strip()]
            elapsed = time.time() - t0

            out = Path(dest) / (Path(audio).stem + ".txt")
            body = "\n".join(lines)
            divider = "-" * 78
            out.write_text(
                f"{body}\n\n{divider}\n{COPYRIGHT_NOTICE}\n",
                encoding="utf-8",
            )

            rt = info.duration / elapsed if elapsed > 0 else 0
            msg = (f"Done. {info.duration/60:.1f} min of audio in {elapsed:.1f}s "
                   f"({rt:.1f}x realtime). Saved: {out.name}")
            self.root.after(0, lambda: self._finish(msg, ok=True, path=out))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            self.root.after(0, lambda exc=err: self._finish(f"Error: {exc}", ok=False))

    def _finish(self, msg, ok, path=None):
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        self.btn.configure(state="normal", bg=self.ACCENT, text="Transcribe")
        self.status_var.set(msg)
        if ok and path:
            messagebox.showinfo(APP_NAME, f"Transcription saved to:\n{path}")
        elif not ok:
            messagebox.showerror(APP_NAME, msg)


def _enable_hidpi():
    if os.name != "nt":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    _enable_hidpi()
    to_install = _missing_packages()
    if to_install:
        run_install_splash(to_install)
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
