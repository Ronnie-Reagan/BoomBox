import os
import json

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".boombox_config.json")

# Default paths
MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")
VIDEO_FOLDER = os.path.join(os.path.expanduser("~"), "Videos")

def load_config():
    global MUSIC_FOLDER, VIDEO_FOLDER
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                MUSIC_FOLDER = config.get("music_folder", MUSIC_FOLDER)
                VIDEO_FOLDER = config.get("video_folder", VIDEO_FOLDER)
        except Exception as e:
            print("[WARNING] Failed to load config:", e)

    os.makedirs(MUSIC_FOLDER, exist_ok=True)
    os.makedirs(VIDEO_FOLDER, exist_ok=True)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"music_folder": MUSIC_FOLDER, "video_folder": VIDEO_FOLDER}, f)
