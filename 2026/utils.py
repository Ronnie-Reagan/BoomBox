#utils.py
import re
import sys
import os
import shutil
from tkinter import messagebox
from constants import AUDIO_EXTS

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def list_local_songs(folder):
    all_songs = []
    for root_dir, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(AUDIO_EXTS):
                all_songs.append(f)
    all_songs.sort(key=str.lower)
    return all_songs

def get_ffmpeg_path() -> str:
    if getattr(sys, 'frozen', False):
        internal_path = os.path.join(sys._MEIPASS, "ffmpeg-full", "bin")
        if os.path.exists(os.path.join(internal_path, "ffmpeg.exe")):
            return internal_path

    base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    external_path = os.path.join(base_path, "THIS_FOLDER_MUST_BE_HERE", "ffmpeg-full", "bin")
    if os.path.exists(os.path.join(external_path, "ffmpeg.exe")):
        return external_path

    messagebox.showerror("Missing FFmpeg", "FFmpeg binaries not found in internal or external paths.\n\nExpected:\n- ffmpeg-full/bin/ffmpeg.exe")
    sys.exit(1)

def check_js_runtime():
    if not shutil.which("node") and not shutil.which("deno"):
        messagebox.showerror(
            "Missing JS Runtime",
            "YouTube downloads require Node.js or Deno.\nPlease install one and restart BoomBox."
        )
        sys.exit(1)
