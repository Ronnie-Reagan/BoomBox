import os
import glob
import yt_dlp
import pygame
import threading
from tkinter import Tk, Label, Entry, Button, Listbox, Scale

# Set up paths
MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")
if not os.path.exists(MUSIC_FOLDER):
    os.makedirs(MUSIC_FOLDER)

# Initialize pygame mixer
pygame.init()
pygame.mixer.init()
# pygame.display.set_mode((100, 100))

# Create the main window
root = Tk()
root.title("YouTube Music Player")
root.geometry("600x750")

# Global variables
queue = []
current_song = None
is_paused = False

# UI Elements
Label(root, text="Search YouTube:").pack()
search_entry = Entry(root, width=50)
search_entry.pack()
Button(root, text="Search", command=lambda: search_youtube(search_entry.get())).pack()

results_list = Listbox(root, width=60, height=10)
results_list.pack()
Button(root, text="Download", command=lambda: download_selected()).pack()

Label(root, text="Local Songs:").pack()
local_songs_list = Listbox(root, width=60, height=10)
local_songs_list.pack()

# Queue UI
Label(root, text="Queue:").pack()
queue_list = Listbox(root, width=60, height=5)
queue_list.pack()

# Load local music files
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

# Download Music
def download_audio(url, title):
    file_path = os.path.join(MUSIC_FOLDER, f"{title}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "outtmpl": file_path,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    load_local_songs()

# Handle Download Button
def download_selected():
    selected_index = results_list.curselection()
    if not selected_index:
        return

    title, url = search_results[selected_index[0]]
    
    # Run the download in a separate thread
    threading.Thread(target=download_audio, args=(url, title), daemon=True).start()

# Queue Management
def update_queue_display():
    queue_list.delete(0, "end")
    for song in queue:
        queue_list.insert("end", os.path.basename(song))

def play_next():
    selected_index = local_songs_list.curselection()
    if not selected_index:
        return
    
    file_name = local_songs_list.get(selected_index)
    file_path = os.path.join(MUSIC_FOLDER, file_name)
    
    queue.insert(0, file_path)  # Add after the current song
    update_queue_display()
    
    if not pygame.mixer.music.get_busy():
        play_song()

def play_now():
    global current_song
    selected_index = local_songs_list.curselection()
    if not selected_index:
        return

    file_name = local_songs_list.get(selected_index)
    file_path = os.path.join(MUSIC_FOLDER, file_name)

    queue.insert(0, file_path)  # Add to front of queue
    update_queue_display()
    
    pygame.mixer.music.stop()
    play_song()  # Immediately play it

def add_to_end():
    selected_index = local_songs_list.curselection()
    if not selected_index:
        return
    
    file_name = local_songs_list.get(selected_index)
    file_path = os.path.join(MUSIC_FOLDER, file_name)

    queue.append(file_path)
    update_queue_display()
        
    if not pygame.mixer.music.get_busy():
        play_song()

# Add a "Now Playing" label above the queue
now_playing_label = Label(root, text="Now Playing: None", font=("Arial", 12))
now_playing_label.pack()

# Modify the play_song function to update the "Now Playing" label
def play_song():
    global current_song, is_paused

    if not queue:
        return
    
    if is_paused and current_song:
        pygame.mixer.music.unpause()
        is_paused = False
        return
    
    current_song = queue.pop(0)
    pygame.mixer.music.load(current_song)
    pygame.mixer.music.play()

    # Update the "Now Playing" label with the song title
    song_title = os.path.basename(current_song).replace(".mp3", "")
    now_playing_label.config(text=f"Now Playing: {song_title}")
    
    pygame.mixer.music.set_endevent(pygame.USEREVENT)  # Auto-skip when song ends
    update_queue_display()

def pause_song():
    global is_paused
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        is_paused = True

def skip_song():
    if queue:
        play_song()
    else:
        pygame.mixer.music.stop()

def previous_song():
    global current_song
    if current_song:
        queue.insert(0, current_song)
        play_song()

def set_volume(val):
    pygame.mixer.music.set_volume(int(val) / 100)

# Playback Controls UI
Button(root, text="Play", command=play_song).pack(side="left", padx=5)
Button(root, text="Pause", command=pause_song).pack(side="left", padx=5)
Button(root, text="Skip", command=skip_song).pack(side="left", padx=5)
Button(root, text="Back", command=previous_song).pack(side="left", padx=5)

Label(root, text="Volume:").pack()
volume_slider = Scale(root, from_=0, to=100, orient="horizontal", command=set_volume)
volume_slider.set(50)
volume_slider.pack()

# Queue Controls
Button(root, text="Play Next", command=play_next).pack(side="left", padx=5)
Button(root, text="Play Now", command=play_now).pack(side="left", padx=5)
Button(root, text="Add to End", command=add_to_end).pack(side="left", padx=5)

# Load local songs on startup
load_local_songs()

# Function to check if the song ended and play the next one
def check_song_end():
    if not pygame.mixer.music.get_busy() and queue:
        play_song()
    root.after(100, check_song_end)

root.after(100, check_song_end)

root.mainloop()
