
from config import load_config
from utils import check_js_runtime, get_ffmpeg_path
import ui

if __name__ == "__main__":
    check_js_runtime()
    load_config()
    FFMPEG_PATH = get_ffmpeg_path()
    ui.start_app()
