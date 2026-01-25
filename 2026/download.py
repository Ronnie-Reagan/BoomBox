#download.py
import os
import yt_dlp
from config import MUSIC_FOLDER, VIDEO_FOLDER
from utils import sanitize_filename, get_ffmpeg_path
FFMPEG_PATH = get_ffmpeg_path()

search_results = []

def search_youtube(query, max_results=5):
    global search_results
    search_results.clear()
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

def ytdl_progress_hook(status):
    if status['status'] == 'downloading':
        percent = status.get('_percent_str', '').strip()
        speed = status.get('_speed_str', '')
        eta = status.get('_eta_str', '')
        print(f"Downloading: {percent} at {speed} ETA {eta}")
    elif status['status'] == 'finished':
        print("Download complete.")


# Download from YouTube
def download_audio(url, title, downloadType, logger, refresh_callback=None):
    safe_title = sanitize_filename(title)
    mp3_path = os.path.join(MUSIC_FOLDER, f"{safe_title}.mp3")
    mp4_path = os.path.join(VIDEO_FOLDER, f"{safe_title}.mp4")

    ydl_opts_audio = {
        "format": "bestaudio/best",
        "js_runtimes": {"node": {}, "deno": {}},
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
        "js_runtimes": {"node": {}, "deno": {}},
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
        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
            ydl.download([url])

    if refresh_callback:
        refresh_callback()
