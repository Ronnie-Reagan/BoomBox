#audio.py
import time
import pygame
from mutagen.mp3 import MP3
from config import MUSIC_FOLDER

pygame.mixer.init()

queue = []
current_song = None
is_paused = False
playback_position = 0
song_length = 0
start_time = 0
is_seeking = False

def set_volume(vol):
    pygame.mixer.music.set_volume(vol / 100)

def seek_to_position(value):
    global playback_position, start_time
    if not current_song:
        return
    try:
        new_pos = float(value) / 1000 * song_length
        pygame.mixer.music.play(start=new_pos)
        playback_position = new_pos
        start_time = time.time() - new_pos
    except Exception as e:
        print("[ERROR] Seek failed:", e)

def update_queue_display():
    pass  # implemented in ui.py with reference to queue Listbox

def play_song(update_callback=None):
    global current_song, is_paused, playback_position, song_length, start_time
    if is_paused and current_song:
        is_paused = False
        pygame.mixer.music.unpause()
        start_time = time.time() - playback_position
        return
    if not queue:
        return
    current_song = queue.pop(0)
    song_path = f"{MUSIC_FOLDER}/{current_song}"
    try:
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        song_length = MP3(song_path).info.length
        playback_position = 0
        start_time = time.time()
        if update_callback:
            update_callback()
    except Exception as e:
        print("[ERROR] playing file:", e)
        current_song = None

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

def add_to_queue(file_name, position="end", callback=None):
    global current_song, queue, is_paused
    if position == "now":
        shouldSkip = current_song != None
        queue.insert(0, file_name)
        if shouldSkip:
            skip_song()
    elif position == "next":
        queue.insert(0, file_name)
    else:
        queue.append(file_name)
    if current_song == None:
        play_song()
    if callback:
        callback()
