import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter.ttk import Notebook
import pygame

from config import MUSIC_FOLDER, VIDEO_FOLDER, save_config
from constants import DARK_STYLE, LABEL_STYLE, ENTRY_STYLE, LISTBOX_STYLE, SCALE_STYLE
import audio
from download import search_youtube, search_results, download_audio
from console import ConsoleRedirector, YTDLRedirectLogger
from utils import get_ffmpeg_path

# --- FFmpeg Check ---
FFMPEG_PATH = get_ffmpeg_path()

# --- Main App Setup ---
root = tk.Tk()
root.title("BoomBox by Don")
root.geometry("690x870")
root.configure(bg="#121212")
icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
if os.path.exists(icon_path):
    root.iconbitmap(icon_path)

notebook = Notebook(root)
notebook.pack(fill="both", expand=True)

# --- Frames ---
main_frame = tk.Frame(notebook, bg="#121212")
log_frame = tk.Frame(notebook, bg="#1e1e1e")
settings_frame = tk.Frame(notebook, bg="#121212")

notebook.add(main_frame, text="Player")
notebook.add(log_frame, text="Console Output")
notebook.add(settings_frame, text="Settings")

# --- Console Redirect ---
log_text = tk.Text(log_frame, bg="#1e1e1e", fg="#69ff3b", insertbackground="#69ff3b", font=("Consolas", 8), wrap="none")
log_text.pack(fill="both", expand=True, padx=5, pady=5)

redirector = ConsoleRedirector(log_text)
logger = YTDLRedirectLogger(redirector)
sys.stdout = redirector
sys.stderr = redirector

def safePrint(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    print(message, **kwargs)
    if "error" in message.lower() or "exception" in message.lower():
        notebook.select(log_frame)  # auto-focus log tab

# --- Settings Tab ---
def browse_folder(entry_widget):
    folder = filedialog.askdirectory()
    if folder:
        entry_widget.delete(0, "end")
        entry_widget.insert(0, folder)

# Music
tk.Label(settings_frame, text="Music Directory:", **LABEL_STYLE).pack(anchor="w", padx=10, pady=(10,0))
music_dir_entry = tk.Entry(settings_frame, width=60, **ENTRY_STYLE)
music_dir_entry.pack(padx=10, pady=2)
music_dir_entry.insert(0, MUSIC_FOLDER)
tk.Button(settings_frame, text="Browse", command=lambda: browse_folder(music_dir_entry), **DARK_STYLE).pack(padx=10, pady=(0,5))

# Video
tk.Label(settings_frame, text="Video Directory:", **LABEL_STYLE).pack(anchor="w", padx=10, pady=(10,0))
video_dir_entry = tk.Entry(settings_frame, width=60, **ENTRY_STYLE)
video_dir_entry.pack(padx=10, pady=2)
video_dir_entry.insert(0, VIDEO_FOLDER)
tk.Button(settings_frame, text="Browse", command=lambda: browse_folder(video_dir_entry), **DARK_STYLE).pack(padx=10, pady=(0,5))

def save_settings():
    global MUSIC_FOLDER, VIDEO_FOLDER
    MUSIC_FOLDER = music_dir_entry.get()
    VIDEO_FOLDER = video_dir_entry.get()
    os.makedirs(MUSIC_FOLDER, exist_ok=True)
    os.makedirs(VIDEO_FOLDER, exist_ok=True)
    save_config()
    safePrint(f"Settings saved:\nMusic: {MUSIC_FOLDER}\nVideo: {VIDEO_FOLDER}")
    load_local_songs()

tk.Button(settings_frame, text="Save Settings", command=save_settings, **DARK_STYLE).pack(pady=20)

# --- Main Player UI ---
tk.Label(main_frame, text="BoomBox by Don", **LABEL_STYLE).pack()
search_entry = tk.Entry(main_frame, width=50, **ENTRY_STYLE)
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

tk.Button(main_frame, text="Search", command=lambda: trigger_search(), **DARK_STYLE).pack()
results_list = tk.Listbox(main_frame, width=90, height=5, **LISTBOX_STYLE)
results_list.pack(pady=3)

download_frame = tk.Frame(main_frame, bg="#121212")
download_frame.pack(pady=5)
tk.Button(download_frame, text="Download MP3", command=lambda: download_selected(1), **DARK_STYLE).pack(side="left", padx=5)
tk.Button(download_frame, text="Download BOTH", command=lambda: download_selected(2), **DARK_STYLE).pack(side="left", padx=5)
tk.Button(download_frame, text="Download MP4", command=lambda: download_selected(3), **DARK_STYLE).pack(side="left", padx=5)

# Local Songs
tk.Label(main_frame, text="Local Songs:", **LABEL_STYLE).pack(pady=(10,0))
local_songs_list = tk.Listbox(main_frame, width=90, height=15, **LISTBOX_STYLE)
local_songs_list.pack(pady=2)

def refresh_queue_listbox():
    queue_list.delete(0, "end")
    for song in audio.queue:
        queue_list.insert("end", song)
# Queue Controls
queue_controls = tk.Frame(main_frame, bg="#121212")
queue_controls.pack(pady=(2,2))
tk.Button(queue_controls,
          text="Play Next",
          command=lambda: audio.add_to_queue(local_songs_list.get(local_songs_list.curselection()[0]), "next", refresh_queue_listbox),
          **DARK_STYLE).pack(side="left", padx=5)

tk.Button(queue_controls, text="Play Now",
          command=lambda: audio.add_to_queue(local_songs_list.get(local_songs_list.curselection()[0]), "now", refresh_queue_listbox),
          **DARK_STYLE).pack(side="left", padx=5)

tk.Button(queue_controls, text="Add to End",
          command=lambda: audio.add_to_queue(local_songs_list.get(local_songs_list.curselection()[0]), "end", refresh_queue_listbox),
          **DARK_STYLE).pack(side="left", padx=5)


# Queue
tk.Label(main_frame, text="Queue:", **LABEL_STYLE).pack(pady=(10,0))
queue_list = tk.Listbox(main_frame, width=90, height=5, **LISTBOX_STYLE)
queue_list.pack(pady=2)

# Now Playing
now_playing_label = tk.Label(main_frame, text="Now Playing: None", font=("Segoe UI", 11, "bold"), bg="#121212", fg="#ffffff")
now_playing_label.pack(pady=(10,5))

# Volume
volume_frame = tk.Frame(main_frame, bg="#121212")
volume_frame.pack(padx=10)
tk.Label(volume_frame, text="Volume", **LABEL_STYLE).pack(side="left", padx=(0,10))
volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=True,
                         command=lambda v: audio.set_volume(int(v)), **SCALE_STYLE)
volume_slider.set(50)
volume_slider.pack(side="left", fill="x", expand=True)

# Playback slider
playback_slider = tk.Scale(main_frame, from_=0, to=1000, orient=tk.HORIZONTAL, length=400, showvalue=False, **SCALE_STYLE)
playback_slider.pack(pady=(2,15))
def start_seeking(event): global is_seeking; is_seeking = True
def stop_seeking(event): global is_seeking; is_seeking = False; audio.seek_to_position(playback_slider.get())
playback_slider.bind("<ButtonPress-1>", start_seeking)
playback_slider.bind("<ButtonRelease-1>", stop_seeking)

def play_song_manual():
    audio.play_song(refresh_queue_listbox)

def skip_song_manual():
    audio.skip_song()
    refresh_queue_listbox()

def pause_song_manual():
    audio.pause_song()
    refresh_queue_listbox()

def previous_song_manual():
    audio.previous_song()
    refresh_queue_listbox()

# Controls
controls = tk.Frame(main_frame, bg="#121212")
controls.pack(pady=(2,5))
tk.Button(controls, text="Play", command=play_song_manual, **DARK_STYLE).pack(side="left", padx=5)
tk.Button(controls, text="Pause", command=pause_song_manual, **DARK_STYLE).pack(side="left", padx=5)
tk.Button(controls, text="Skip", command=skip_song_manual, **DARK_STYLE).pack(side="left", padx=5)
tk.Button(controls, text="Back", command=previous_song_manual, **DARK_STYLE).pack(side="left", padx=5)
def update_queue_display():
    queue_list.delete(0, "end")
    for song in audio.queue:
        queue_list.insert("end", os.path.basename(song))

# --- Search & Downloads ---
def trigger_search(event=None):
    query = search_entry.get().strip()
    if not query or query == "Search for a song...":
        return
    results_list.delete(0, "end")
    search_youtube(query)
    for title, url in search_results:
        results_list.insert("end", title)

def download_selected(downloadType: int):
    selected_index = results_list.curselection()
    if not selected_index:
        return
    title, url = search_results[selected_index[0]]
    threading.Thread(
        target=download_audio,
        args=(url, title, downloadType, logger, refresh_local_songs_with_filter),
        daemon=True
    ).start()


# --- Local Songs Management ---
ALL_LOCAL_SONGS = []
local_last_song = None
queue_last_song = None

def load_local_songs():
    global ALL_LOCAL_SONGS
    ALL_LOCAL_SONGS.clear()
    local_songs_list.delete(0, "end")
    for root_dir, _, files in os.walk(MUSIC_FOLDER):
        for f in files:
            if f.lower().endswith((".mp3",".wav",".flac",".ogg",".m4a")):
                ALL_LOCAL_SONGS.append(f)
    ALL_LOCAL_SONGS.sort(key=str.lower)
    for f in ALL_LOCAL_SONGS:
        local_songs_list.insert("end", f)

def filter_local_songs(query: str):
    local_songs_list.delete(0, "end")
    if not query:
        for f in ALL_LOCAL_SONGS: local_songs_list.insert("end", f)
        return
    q = query.lower()
    matches = [f for f in ALL_LOCAL_SONGS if q in f.lower()]
    for f in matches: local_songs_list.insert("end", f)

def on_search_change(event=None):
    text = search_entry.get().strip()
    if not text or text == "Search for a song...":
        filter_local_songs("")
    else:
        filter_local_songs(text)

def refresh_local_songs_with_filter():
    # Reload all songs
    load_local_songs()
    # Reapply search filter from the search bar
    on_search_change()

# --- Local List Memory ---
def on_local_focus_in(event):
    global local_last_song
    size = local_songs_list.size()
    if size == 0: return
    index_to_select = 0
    if local_last_song:
        try:
            index_to_select = local_songs_list.get(0, "end").index(local_last_song)
        except ValueError:
            index_to_select = 0
    local_songs_list.selection_clear(0, "end")
    local_songs_list.selection_set(index_to_select)
    local_songs_list.see(index_to_select)

def on_local_select(event):
    global local_last_song
    selected = local_songs_list.curselection()
    if selected:
        local_last_song = local_songs_list.get(selected[0])

def local_activate(event=None):
    selected = local_songs_list.curselection()
    if not selected:
        return
    index = selected[0]
    audio.add_to_queue(local_songs_list.get(index), "end", refresh_queue_listbox)

# --- Queue Memory ---
def on_queue_focus_in(event):
    global queue_last_song
    size = queue_list.size()
    if size == 0: return
    index_to_select = 0
    if queue_last_song:
        try:
            index_to_select = queue_list.get(0, "end").index(queue_last_song)
        except ValueError:
            index_to_select = 0
    queue_list.selection_clear(0, "end")
    queue_list.selection_set(index_to_select)
    queue_list.see(index_to_select)

def on_queue_select(event):
    global queue_last_song
    selected = queue_list.curselection()
    if selected:
        queue_last_song = queue_list.get(selected[0])

def queue_activate(event=None):
    selected_index = queue_list.curselection()
    if not selected_index: return
    file_name = queue_list.get(selected_index)
    try: audio.queue.remove(file_name)
    except ValueError: return
    audio.queue.insert(0, file_name)
    skip_song_manual()


# --- Binds ---
search_entry.bind("<KeyRelease>", on_search_change)
search_entry.bind("<Return>", trigger_search)
results_list.bind("<Return>", lambda e: download_selected(1))
local_songs_list.bind("<FocusIn>", on_local_focus_in)
local_songs_list.bind("<<ListboxSelect>>", on_local_select)
local_songs_list.bind("<Double-Button-1>", local_activate)
local_songs_list.bind("<Return>", local_activate)
queue_list.bind("<FocusIn>", on_queue_focus_in)
queue_list.bind("<<ListboxSelect>>", on_queue_select)
queue_list.bind("<Double-Button-1>", queue_activate)
queue_list.bind("<Return>", queue_activate)

# --- Playback Update ---
def update_playback_bar():
    if audio.song_length > 0 and not audio.is_paused and not is_seeking:
        if pygame.mixer.music.get_busy():
            elapsed = time.time() - audio.start_time
            playback_slider.set(int((elapsed / audio.song_length) * 1000))
        else:
            if current_song:
                current_song = None
                audio.play_song(lambda: refresh_queue_listbox())
    main_frame.after(200, update_playback_bar)

# --- Initialize ---
def start_app():
    load_local_songs()
    update_playback_bar()
    root.mainloop()
