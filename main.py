import os
import glob
import yt_dlp
import threading
from tkinter import Tk, Label, Entry, Button, Listbox, HORIZONTAL, Scale, Frame, Text, END
from tkinter.ttk import Notebook
import pygame
import re
from mutagen.mp3 import MP3
import time
import sys
import io

pygame.mixer.init()

def get_ffmpeg_path():
    # When running as a bundled EXE with --add-data
    if getattr(sys, 'frozen', False):
        internal_path = os.path.join(sys._MEIPASS, "ffmpeg-full", "bin")
        if os.path.exists(os.path.join(internal_path, "ffmpeg.exe")):
            return internal_path

    # Fallback: external layout (py file or manually placed)
    base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    external_path = os.path.join(base_path, "THIS_FOLDER_MUST_BE_HERE", "ffmpeg-full", "bin")

    if os.path.exists(os.path.join(external_path, "ffmpeg.exe")):
        return external_path

    # Final fallback: warn and return empty
    from tkinter import messagebox
    messagebox.showerror("Missing FFmpeg", "FFmpeg binaries not found in internal or external paths.\n\nExpected:\n- ffmpeg-full/bin/ffmpeg.exe")
    sys.exit(1)


FFMPEG_PATH = get_ffmpeg_path()

if not os.path.exists(os.path.join(FFMPEG_PATH, "ffmpeg.exe")):
    from tkinter import messagebox
    messagebox.showerror("Missing FFmpeg", "FFmpeg binaries not found.\n\nPlease ensure THIS_FOLDER_MUST_BE_HERE/ffmpeg-full/bin/ffmpeg.exe exists next to this app.")
    sys.exit(1)

class ConsoleRedirector(io.TextIOBase):
    def __init__(self, text_widget):
        self.text_widget = text_widget

        # Define color tags
        self.text_widget.tag_config("error", foreground="#ff4c4c")        # Red
        self.text_widget.tag_config("warning", foreground="#ffc107")      # Yellow
        self.text_widget.tag_config("download", foreground="#4cff4c")     # Lime green
        self.text_widget.tag_config("ffmpeg", foreground="#4ca6ff")       # Light blue
        self.text_widget.tag_config("extract", foreground="#da70d6")      # Orchid
        self.text_widget.tag_config("info", foreground="#aaaaaa")         # Gray
        self.text_widget.tag_config("complete", foreground="#00ffff")     # Cyan
        self.text_widget.tag_config("default", foreground="#ffffff")      # White

    def write(self, message):
        self.text_widget.after(0, self._write, message)

    def _write(self, message):
        if "\r" in message:
            self.text_widget.delete("end-2l", "end-1l")
            message = message.split("\r")[-1]

        tag = self.get_tag_for_line(message)
        self.text_widget.insert("end", message, tag)
        self.text_widget.see("end")

    def get_tag_for_line(self, message):
        lowered = message.lower()

        if "[error]" in lowered or "error" in lowered or "exception" in lowered:
            return "error"
        elif "[warning]" in lowered or "warning" in lowered:
            return "warning"
        elif "[download]" in lowered or "downloading" in lowered:
            return "download"
        elif "[ffmpeg]" in lowered:
            return "ffmpeg"
        elif "[extractaudio]" in lowered or "destination:" in lowered:
            return "extract"
        elif "complete" in lowered or "deleting original file" in lowered:
            return "complete"
        elif "[youtube]" in lowered or "[info]" in lowered:
            return "info"
        else:
            return "default"

    def flush(self):
        pass


class YTDLRedirectLogger:
    def __init__(self, redirector):
        self.redirector = redirector

    def debug(self, msg):
        self.redirector.write(msg + "\n")

    def warning(self, msg):
        self.redirector.write("WARNING: " + msg + "\n")

    def error(self, msg):
        self.redirector.write("ERROR: " + msg + "\n")


def safePrint(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    print(message, **kwargs)
    if "error" in message.lower() or "exception" in message.lower():
        notebook.select(log_frame)  # auto-focus log tab

# Set up paths
MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")
os.makedirs(MUSIC_FOLDER, exist_ok=True)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller onefile """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

icon_path = resource_path("favicon.ico")

# Global state
queue = []
current_song = None
is_paused = False
playback_position = 0
song_length = 0
start_time = 0
is_seeking = False


# UI Setup
root = Tk()
root.title("BoomBox by Don")
root.geometry("690x870")
root.configure(bg="#121212")
root.iconbitmap(icon_path)

notebook = Notebook(root)
notebook.pack(fill="both", expand=True)

main_frame = Frame(notebook, bg="#121212")
log_frame = Frame(notebook, bg="#1e1e1e")

log_text = Text(log_frame, bg="#1e1e1e", fg="#69ff3b", insertbackground="#69ff3b", font=("Consolas", 8), wrap="none")
log_text.pack(fill="both", expand=True, padx=5, pady=5)

redirector = ConsoleRedirector(log_text)
logger = YTDLRedirectLogger(redirector)

sys.stdout = redirector
sys.stderr = redirector

notebook.add(main_frame, text="Player")
notebook.add(log_frame, text="Console Output")
main_frame.configure(bg="#121212")  # Matte black

default_font = ("Segoe UI", 10)

DARK_STYLE = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "activebackground": "#ff5c5c",
    "activeforeground": "#ffffff",
    "relief": "flat",
    "bd": 1,
    "font": default_font,
}

LABEL_STYLE = {
    "bg": "#121212",
    "fg": "#ff3b3b",
    "font": ("Segoe UI", 10, "bold")
}

ENTRY_STYLE = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "insertbackground": "#ff3b3b",
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": "#393939",
    "font": default_font
}

LISTBOX_STYLE = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "selectbackground": "#ff3b3b",
    "selectforeground": "#000000",
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": "#393939",
    "font": default_font
}


SCALE_STYLE = {
    "bg": "#121212",
    "highlightthickness": 0,
    "troughcolor": "#2c2c2c",
    "activebackground": "#ff3b3b",
    "sliderrelief": "flat"
}

Label(main_frame, text="BoomBox by Don", **LABEL_STYLE).pack()
search_entry = Entry(main_frame, width=50, **ENTRY_STYLE)
search_entry.insert(0, "Search for a song...")
search_entry.pack(pady=3)

def clear_placeholder(event):
    if search_entry.get() == "Search for a song...":
        search_entry.delete(0, "end")
        search_entry.config(fg="#ffffff")

def restore_placeholder(event):
    if not search_entry.get():
        search_entry.insert(0, "Search for a song...")
        search_entry.config(fg="#888888")

search_entry.bind("<FocusIn>", clear_placeholder)
search_entry.bind("<FocusOut>", restore_placeholder)
search_entry.config(fg="#888888")
Button(main_frame, text="Search", command=lambda: search_youtube(search_entry.get()), **DARK_STYLE).pack()

results_list = Listbox(main_frame, width=90, height=5, **LISTBOX_STYLE)
results_list.pack(pady=3)
download_frame = Frame(main_frame, bg="#121212")
download_frame.pack(pady=5)

Button(download_frame, text="Download MP3", command=lambda: download_selected(1), **DARK_STYLE).pack(side="left", padx=5)
Button(download_frame, text="Download BOTH", command=lambda: download_selected(2), **DARK_STYLE).pack(side="left", padx=5)
Button(download_frame, text="Download MP4", command=lambda: download_selected(3), **DARK_STYLE).pack(side="left", padx=5)

Label(main_frame, text="Local Songs:", **LABEL_STYLE).pack(pady=(10, 0))
local_songs_list = Listbox(main_frame, width=90, height=15, **LISTBOX_STYLE)
local_songs_list.pack(pady=2)

queue_controls = Frame(main_frame, bg="#121212")
queue_controls.pack(pady=(2, 2))

Button(queue_controls, text="Play Next", command=lambda: add_to_queue("next"), **DARK_STYLE).pack(side="left", padx=5)
Button(queue_controls, text="Play Now", command=lambda: add_to_queue("now"), **DARK_STYLE).pack(side="left", padx=5)
Button(queue_controls, text="Add to End", command=lambda: add_to_queue(), **DARK_STYLE).pack(side="left", padx=5)

Label(main_frame, text="Queue:", **LABEL_STYLE).pack(pady=(10, 0))
queue_list = Listbox(main_frame, width=90, height=5, **LISTBOX_STYLE)
queue_list.pack(pady=2)

now_playing_label = Label(main_frame, text="Now Playing: None", font=("Segoe UI", 11, "bold"), bg="#121212", fg="#ffffff")
now_playing_label.pack(pady=(10, 5))

volume_frame = Frame(main_frame, bg="#121212")
volume_frame.pack(padx=10)

Label(volume_frame, text="Volume", **LABEL_STYLE).pack(side="left", padx=(0, 10))

volume_slider = Scale(
    volume_frame,
    from_=0,
    to=100,
    orient=HORIZONTAL,
    showvalue=True,
    command=lambda v: set_volume(int(v)),
    **SCALE_STYLE
)
volume_slider.set(50)
volume_slider.pack(side="left", fill="x", expand=True)


playback_slider = Scale(main_frame, from_=0, to=1000, orient=HORIZONTAL, length=400, showvalue=False, **SCALE_STYLE)
playback_slider.pack(pady=(2, 15))
def start_seeking(event):
    global is_seeking
    is_seeking = True

def stop_seeking(event):
    global is_seeking
    is_seeking = False
    seek_to_position(playback_slider.get())

playback_slider.bind("<ButtonPress-1>", start_seeking)
playback_slider.bind("<ButtonRelease-1>", stop_seeking)



controls = Frame(main_frame, bg="#121212")
controls.pack(pady=(2, 5))

# playtime bar with seek, handles next song queueing
def update_playback_bar():
    global is_paused, current_song

    if song_length > 0 and not is_paused and not is_seeking:
        if pygame.mixer.music.get_busy():
            elapsed = time.time() - start_time
            playback_slider.set(int((elapsed / song_length) * 1000))
        else:
            if current_song and (time.time() - start_time) > (song_length - 1):
                current_song = None
                play_song()

    main_frame.after(200, update_playback_bar)

# Utility
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# Load local songs
def load_local_songs():
    local_songs_list.delete(0, "end")
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    for file in music_files:
        local_songs_list.insert("end", os.path.basename(file))

# YouTube Search
search_results = []
def search_youtube(query, max_results=5):
    global search_results
    search_results.clear()
    results_list.delete(0, "end")

    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch",
        "extract_flat": True,
        "force_generic_extractor": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    for entry in info["entries"]:
        title, url = entry["title"], entry["url"]
        search_results.append((title, url))
        results_list.insert("end", title)

def ytdl_progress_hook(status):
    if status['status'] == 'downloading':
        percent = status.get('_percent_str', '').strip()
        speed = status.get('_speed_str', '')
        eta = status.get('_eta_str', '')
        print(f"Downloading: {percent} at {speed} ETA {eta}")
    elif status['status'] == 'finished':
        print("Download complete.")

# Download from YouTube
def download_audio(url, title, downloadType):
    safe_title = sanitize_filename(title)
    mp3_path = os.path.join(MUSIC_FOLDER, f"{safe_title}.mp3")
    mp4_path = os.path.join(MUSIC_FOLDER, f"{safe_title}.mp4")

    ydl_opts_audio = {
        "format": "bestaudio/best",
        "outtmpl": mp3_path.replace(".mp3", ".%(ext)s"),
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "256",
        }],
        "quiet": True,
        "logger": logger,
        "progress_hooks": [ytdl_progress_hook],
        "noplaylist": True,
    }

    ydl_opts_video = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "outtmpl": mp4_path,
        "ffmpeg_location": FFMPEG_PATH,
        "merge_output_format": "mp4",
        "quiet": True,
        "logger": logger,
        "progress_hooks": [ytdl_progress_hook],
        "noplaylist": True,
    }

    # download type: 1 = mp3, 2 = both, 3 = mp4
    if downloadType < 3: # if dl = 1 or 2
        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
            ydl.download([url])

    if downloadType > 1: # if dl = 2 or 3
        try:
            with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                ydl.download([url])
        except Exception as e:
            safePrint("Video download failed:", e)

    load_local_songs()

def download_selected(downloadType):
    selected_index = results_list.curselection()
    if not selected_index:
        return
    title, url = search_results[selected_index[0]]
    threading.Thread(target=download_audio, args=(url, title, downloadType), daemon=True).start()

# Queue Handling
def set_volume(vol):
    pygame.mixer.music.set_volume(vol / 100)

def seek_to_position(value):
    global playback_position, start_time
    if not current_song:
        return
    try:
        safePrint(f"Seeking to {value}")
        new_pos = float(value) / 1000 * song_length
        pygame.mixer.music.play(start=new_pos)
        playback_position = new_pos
        start_time = time.time() - new_pos
    except Exception as e:
        safePrint("[ERROR] Seek failed:", e)


def update_queue_display():
    queue_list.delete(0, "end")
    for song in queue:
        queue_list.insert("end", os.path.basename(song))

def play_song():
    global current_song, is_paused, playback_position, song_length, start_time

    if is_paused and current_song:
        is_paused = False
        pygame.mixer.music.unpause()
        start_time = time.time() - playback_position
        return

    if not queue:
        now_playing_label.config(text="Now Playing: None")
        return

    current_song = queue.pop(0)
    song_path = os.path.join(MUSIC_FOLDER, current_song)

    try:
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        song_length = MP3(song_path).info.length
        playback_position = 0
        start_time = time.time()
        now_playing_label.config(text=f"Now Playing: {current_song}")
    except Exception as e:
        safePrint("[ERROR]  playing file:", e)
        current_song = None

    update_queue_display()

def pause_song():
    global is_paused, playback_position
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        is_paused = True
        playback_position = time.time() - start_time

def skip_song():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    play_song()

def previous_song():
    global current_song
    if current_song:
        queue.insert(0, current_song)
        play_song()

def add_to_queue(position="end"):
    selected_index = local_songs_list.curselection()
    if not selected_index:
        return
    file_name = local_songs_list.get(selected_index)
    if position == "now":
        shouldSkip = current_song == None and False or True
        queue.insert(0, file_name)
        if shouldSkip:
            skip_song()
    elif position == "next":
        queue.insert(0, file_name)
    else:
        queue.append(file_name)

    update_queue_display()
    if not pygame.mixer.music.get_busy():
        play_song()

# Controls
Button(controls, text="Play", command=play_song, **DARK_STYLE).pack(side="left", padx=5)
Button(controls, text="Pause", command=pause_song, **DARK_STYLE).pack(side="left", padx=5)
Button(controls, text="Skip", command=skip_song, **DARK_STYLE).pack(side="left", padx=5)
Button(controls, text="Back", command=previous_song, **DARK_STYLE).pack(side="left", padx=5)


load_local_songs()
update_playback_bar()
main_frame.mainloop()
