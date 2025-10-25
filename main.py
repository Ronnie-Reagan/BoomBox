# boombox_pyqt.py
# Run: pip install PyQt5 pygame mutagen yt-dlp pypresence
# Notes:
# - Keeps your function names and global state where feasible.
# - Uses a frameless, translucent window with rounded mask and custom painting.
# - Replaces Tk widgets with PyQt5 equivalents. Logging uses QTextEdit with colored lines.
# - Uses QTimer instead of Tk .after. Threading stays via threading.Thread.

import os, sys, io, re, glob, time, threading
import yt_dlp
import pygame
from mutagen.mp3 import MP3

from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt

# ------------------------------ Pygame init ------------------------------
pygame.mixer.init()

# ------------------------------ FFmpeg path ------------------------------
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        internal_path = os.path.join(sys._MEIPASS, "ffmpeg-full", "bin")
        if os.path.exists(os.path.join(internal_path, "ffmpeg.exe")):
            return internal_path
    base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    external_path = os.path.join(base_path, "THIS_FOLDER_MUST_BE_HERE", "ffmpeg-full", "bin")
    if os.path.exists(os.path.join(external_path, "ffmpeg.exe")):
        return external_path
    QtWidgets.QMessageBox.critical(None, "Missing FFmpeg",
        "FFmpeg binaries not found in internal or external paths.\n\nExpected:\n- ffmpeg-full/bin/ffmpeg.exe")
    sys.exit(1)

FFMPEG_PATH = get_ffmpeg_path()
if not os.path.exists(os.path.join(FFMPEG_PATH, "ffmpeg.exe")):
    QtWidgets.QMessageBox.critical(None, "Missing FFmpeg",
        "FFmpeg binaries not found.\n\nPlease ensure THIS_FOLDER_MUST_BE_HERE/ffmpeg-full/bin/ffmpeg.exe exists next to this app.")
    sys.exit(1)

# ------------------------------ Globals kept ------------------------------
search_results = []
queue = []
current_song = None
is_paused = False
playback_position = 0
song_length = 0
start_time = 0
is_seeking = False

rpc = None
rpc_song_start_time = 0
rpc_current_song = None
heldRPC = None
lastRpcPayloadTime = 0
rpcLock = threading.Lock()

# ------------------------------ Util ------------------------------
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def format_song_title(song_title):
    if not song_title:
        return "Idle"
    name = song_title.replace(".mp3", "")
    name = re.sub(r"[_%]+", " ", name)
    return name.strip()

# ------------------------------ Logging redirect ------------------------------
class ConsoleRedirector(io.TextIOBase):
    COLORS = {
        "error": "#ff4c4c",
        "warning": "#ffc107",
        "download": "#4cff4c",
        "ffmpeg": "#4ca6ff",
        "extract": "#da70d6",
        "info": "#aaaaaa",
        "complete": "#00ffff",
        "default": "#ffffff",
    }
    def __init__(self, text_edit: QtWidgets.QTextEdit, log_tab_widget: QtWidgets.QTabWidget, log_index: int):
        self.text_edit = text_edit
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QtGui.QFont("Consolas", 9))
        self.log_tab_widget = log_tab_widget
        self.log_index = log_index

    def write(self, message):
        # defer to main GUI thread safely
        def append():
            html = self._format_html(message)
            self.text_edit.append(html)
            self.text_edit.verticalScrollBar().setValue(
                self.text_edit.verticalScrollBar().maximum()
            )
        QtCore.QTimer.singleShot(0, append)

    def flush(self):
        pass

    def _format_html(self, message: str) -> str:
        if "\r" in message:
            message = message.split("\r")[-1]
        tag = self.get_tag_for_line(message)
        color = self.COLORS.get(tag, self.COLORS["default"])
        safe = QtGui.QTextDocument().toPlainText  # not used; message assumed plain
        # Simple escape
        esc = (message.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
        return f'<span style="color:{color}">{esc}</span>'

    def get_tag_for_line(self, message: str):
        lowered = message.lower()
        if "[error]" in lowered or "error" in lowered or "exception" in lowered:
            # focus console tab on error
            QtCore.QTimer.singleShot(0, lambda: self.log_tab_widget.setCurrentIndex(self.log_index))
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
        elif "[youtube]" in lowered or "[info]" in lowered or "info:" in lowered:
            return "info"
        else:
            return "default"

class YTDLRedirectLogger:
    def __init__(self, redirector):
        self.redirector = redirector
    def debug(self, msg): self.redirector.write(msg + "\n")
    def warning(self, msg): self.redirector.write("WARNING: " + msg + "\n")
    def error(self, msg): self.redirector.write("ERROR: " + msg + "\n")

# ------------------------------ Discord RPC ------------------------------
def start_rpc():
    global rpc
    try:
        from pypresence import Presence
        DISCORD_APP_ID = "1331776648890159164"
        _rpc = Presence(DISCORD_APP_ID)
        _rpc.connect()
        rpc = _rpc
    except Exception as e:
        print(f"[RPC Disabled] {e}")
        rpc = None

def cleanup_rpc():
    global rpc
    if rpc:
        try:
            rpc.clear()
        except Exception as e:
            print(f"[RPC ERROR on exit] {e}")

def rpc_worker():
    global heldRPC, lastRpcPayloadTime, rpc
    while True:
        if rpc:
            with rpcLock:
                if heldRPC and (time.time() - lastRpcPayloadTime) >= 15:
                    try:
                        rpc.update(**heldRPC)
                        lastRpcPayloadTime = time.time()
                        heldRPC = None
                    except Exception as e:
                        print(f"[RPC ERROR] {e}")
                        heldRPC = None
        time.sleep(1)

def update_discord_status(state="Idle", song_title=None, paused=False, reset_time=False):
    global rpc_song_start_time, rpc_current_song, current_song, rpc, heldRPC, rpcLock
    if not rpc:
        return
    if reset_time or song_title != rpc_current_song:
        rpc_song_start_time = int(time.time())
        rpc_current_song = song_title
    payload = {
        "state": f"{format_song_title(current_song)}" if song_title else state,
        "details": state,
        "large_image": "embedded_cover",
        "large_text": "BoomBox by Don",
        "small_image": "flag_of_canada",
        "small_text": "Made in Canada",
        "buttons": [{"label": "Get BoomBox", "url": "https://github.com/Ronnie-Reagan/BoomBox"}]
    }
    if not paused and song_title:
        payload["start"] = rpc_song_start_time
    with rpcLock:
        heldRPC = payload

# ------------------------------ Main Window (skinned) ------------------------------
class BoomBoxWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Frameless + translucent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(760, 920)
        self._drag_pos = None

        # Mask build
        self._rebuild_mask()

        # Icon if available
        icon_path = self.resource_path("favicon-6.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Layouts
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(10)

        # Title + Close
        title_bar = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel("BoomBox by Don — PyQt5")
        self.title_label.setStyleSheet("color:#1a2438; font: 700 12pt 'Segoe UI';")
        title_bar.addWidget(self.title_label)
        title_bar.addStretch(1)
        self.close_btn_rect = QtCore.QRectF()  # painted button; also provide a fallback minimal close
        close_fallback = QtWidgets.QPushButton("×")
        close_fallback.setFixedSize(24,24)
        close_fallback.clicked.connect(self.close)
        close_fallback.setStyleSheet("background:#e4caca; color:#7a2b2b; border-radius:6px; border:1px solid #7a2b2b; font: 700 12pt 'Segoe UI';")
        title_bar.addWidget(close_fallback)
        outer.addLayout(title_bar)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0px; }
            QTabBar::tab { background:#21252b; color:white; padding:8px 14px; border-top-left-radius:6px; border-top-right-radius:6px; }
            QTabBar::tab:selected { background:#2b313a; }
        """)
        outer.addWidget(self.tabs, 1)

        # Player tab
        self.player = QtWidgets.QWidget()
        self.player.setObjectName("player")
        self.player.setStyleSheet("#player{background-color: rgba(18,18,18,180); border-radius:14px;}")
        p_lay = QtWidgets.QVBoxLayout(self.player)
        p_lay.setContentsMargins(16,16,16,16)
        p_lay.setSpacing(10)

        header = QtWidgets.QLabel("BoomBox by Don")
        header.setStyleSheet("color:#ff3b3b; font: 700 12pt 'Segoe UI';")
        p_lay.addWidget(header)

        search_row = QtWidgets.QHBoxLayout()
        self.search_entry = QtWidgets.QLineEdit()
        self.search_entry.setPlaceholderText("Search for a song...")
        self.search_entry.setStyleSheet("""
            QLineEdit {background:#1e1e1e; color:white; border:1px solid #393939; padding:6px; border-radius:6px;}
            QLineEdit:focus { border:1px solid #ff3b3b; }
        """)
        search_btn = QtWidgets.QPushButton("Search")
        search_btn.clicked.connect(lambda: self.search_youtube(self.search_entry.text()))
        search_btn.setStyleSheet(self.btn_style())
        search_row.addWidget(self.search_entry, 1)
        search_row.addWidget(search_btn, 0)
        p_lay.addLayout(search_row)

        self.results_list = QtWidgets.QListWidget()
        self.results_list.setStyleSheet(self.list_style())
        self.results_list.setFixedHeight(120)
        p_lay.addWidget(self.results_list)

        dl_row = QtWidgets.QHBoxLayout()
        btn_mp3 = QtWidgets.QPushButton("Download MP3")
        btn_both = QtWidgets.QPushButton("Download BOTH")
        btn_mp4 = QtWidgets.QPushButton("Download MP4")
        for b in (btn_mp3, btn_both, btn_mp4):
            b.setStyleSheet(self.btn_style())
        btn_mp3.clicked.connect(lambda: self.download_selected(1))
        btn_both.clicked.connect(lambda: self.download_selected(2))
        btn_mp4.clicked.connect(lambda: self.download_selected(3))
        dl_row.addWidget(btn_mp3); dl_row.addWidget(btn_both); dl_row.addWidget(btn_mp4)
        p_lay.addLayout(dl_row)

        p_lay.addWidget(self.label_red("Local Songs:"))
        self.local_songs_list = QtWidgets.QListWidget()
        self.local_songs_list.setStyleSheet(self.list_style())
        self.local_songs_list.setFixedHeight(260)
        p_lay.addWidget(self.local_songs_list)

        qrow = QtWidgets.QHBoxLayout()
        b_next = QtWidgets.QPushButton("Play Next")
        b_now  = QtWidgets.QPushButton("Play Now")
        b_end  = QtWidgets.QPushButton("Add to End")
        for b in (b_next, b_now, b_end): b.setStyleSheet(self.btn_style())
        b_next.clicked.connect(lambda: self.add_to_queue("next"))
        b_now.clicked.connect(lambda: self.add_to_queue("now"))
        b_end.clicked.connect(lambda: self.add_to_queue("end"))
        qrow.addWidget(b_next); qrow.addWidget(b_now); qrow.addWidget(b_end)
        p_lay.addLayout(qrow)

        p_lay.addWidget(self.label_red("Queue:"))
        self.queue_list = QtWidgets.QListWidget()
        self.queue_list.setStyleSheet(self.list_style())
        self.queue_list.setFixedHeight(120)
        p_lay.addWidget(self.queue_list)

        self.now_playing_label = QtWidgets.QLabel("Now Playing: None")
        self.now_playing_label.setStyleSheet("color:white; font: 700 11pt 'Segoe UI';")
        p_lay.addWidget(self.now_playing_label)

        vol_row = QtWidgets.QHBoxLayout()
        vol_row.addWidget(self.label_red("Volume"))
        self.volume_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0,100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(lambda v: self.set_volume(int(v)))
        self.volume_slider.setStyleSheet(self.slider_style())
        vol_row.addWidget(self.volume_slider, 1)
        p_lay.addLayout(vol_row)

        self.playback_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.playback_slider.setRange(0,1000)
        self.playback_slider.setStyleSheet(self.slider_style())
        self.playback_slider.sliderPressed.connect(self.start_seeking)
        self.playback_slider.sliderReleased.connect(self.stop_seeking)
        p_lay.addWidget(self.playback_slider)

        ctrl_row = QtWidgets.QHBoxLayout()
        b_play = QtWidgets.QPushButton("Play")
        b_pause= QtWidgets.QPushButton("Pause")
        b_skip = QtWidgets.QPushButton("Skip")
        b_back = QtWidgets.QPushButton("Back")
        for b in (b_play,b_pause,b_skip,b_back): b.setStyleSheet(self.btn_style())
        b_play.clicked.connect(self.play_song)
        b_pause.clicked.connect(self.pause_song)
        b_skip.clicked.connect(self.skip_song)
        b_back.clicked.connect(self.previous_song)
        ctrl_row.addWidget(b_play); ctrl_row.addWidget(b_pause); ctrl_row.addWidget(b_skip); ctrl_row.addWidget(b_back)
        p_lay.addLayout(ctrl_row)

        # Console tab
        self.console = QtWidgets.QWidget()
        self.console.setObjectName("console")
        self.console.setStyleSheet("#console{background-color: rgba(30,30,30,200); border-radius:14px;}")
        c_lay = QtWidgets.QVBoxLayout(self.console)
        c_lay.setContentsMargins(16,16,16,16)
        c_lay.setSpacing(10)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setStyleSheet("QTextEdit{background:#1e1e1e; color:#69ff3b; border:1px solid #333; border-radius:6px;}")
        c_lay.addWidget(self.log_text, 1)

        self.tabs.addTab(self.player, "Player")
        console_index = self.tabs.addTab(self.console, "Console Output")

        # Logger redirect
        self.redirector = ConsoleRedirector(self.log_text, self.tabs, console_index)
        self.logger = YTDLRedirectLogger(self.redirector)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        # Paths and initial load
        self.MUSIC_FOLDER = self.select_music_folder()
        print(f"[INFO] Using music folder: {self.MUSIC_FOLDER}")
        self.load_local_songs()

        # Playback bar timer
        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.timeout.connect(self.update_playback_bar)
        self.playback_timer.start(200)

        # RPC
        start_rpc()
        t = threading.Thread(target=rpc_worker, daemon=True)
        t.start()
        update_discord_status()

    # ---------- Styling helpers ----------
    def btn_style(self):
        return ("QPushButton{background:#2b2b2b; color:white; border:1px solid #454545; border-radius:8px; padding:6px 10px;}"
                "QPushButton:hover{background:#343434;}"
                "QPushButton:pressed{background:#ff5c5c;}")
    def list_style(self):
        return ("QListWidget{background:#1e1e1e; color:white; border:1px solid #393939; border-radius:8px;}"
                "QListWidget::item:selected{background:#ff3b3b; color:black;}")
    def slider_style(self):
        return ("QSlider::groove:horizontal{height:6px; background:#2c2c2c; border-radius:3px;}"
                "QSlider::handle:horizontal{background:#ff3b3b; width:14px; height:14px; margin:-4px 0; border-radius:7px;}")
    def label_red(self, text):
        lab = QtWidgets.QLabel(text)
        lab.setStyleSheet("color:#ff3b3b; font: 700 10pt 'Segoe UI';")
        return lab

    # ---------- Custom window shape and paint ----------
    def _rebuild_mask(self):
        w, h = 800, 960  # nominal for mask; real size uses margins
        r = 26
        path = QtGui.QPainterPath()
        rect = QtCore.QRectF(10, 10, self.width()-20, self.height()-20)
        path.addRoundedRect(rect, r, r)
        region = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        # Soft shadow
        for i in range(10):
            alpha = int(110 * (1 - i / 10))
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor(0,0,0,alpha))
            rect = QtCore.QRectF(10 - i, 10 - i, w - 20 + 2*i, h - 20 + 2*i)
            path = QtGui.QPainterPath()
            path.addRoundedRect(rect, 26 + i, 26 + i)
            p.drawPath(path)

        # Glass body
        body = QtCore.QRectF(10, 10, w - 20, h - 20)
        grad = QtGui.QLinearGradient(body.topLeft(), body.bottomRight())
        grad.setColorAt(0.0, QtGui.QColor(240, 245, 255, 230))
        grad.setColorAt(1.0, QtGui.QColor(205, 215, 235, 230))
        p.setPen(QtGui.QPen(QtGui.QColor(40, 50, 70, 220), 1.2))
        p.setBrush(grad)
        path = QtGui.QPainterPath()
        path.addRoundedRect(body, 26, 26)
        p.drawPath(path)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rebuild_mask()

    # Dragging
    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent):
        if self._drag_pos and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        self._drag_pos = None

    # ---------- Path helpers ----------
    def resource_path(self, relative_path):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def select_music_folder(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Music")
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select your music directory", default_dir)
        if not folder:
            QtWidgets.QMessageBox.information(self, "No Folder Selected", f"Using default: {default_dir}")
            folder = default_dir
        os.makedirs(folder, exist_ok=True)
        return folder

    # ---------- App logic (ported names preserved) ----------
    def load_local_songs(self):
        self.local_songs_list.clear()
        music_files = glob.glob(os.path.join(self.MUSIC_FOLDER, "*.mp3"))
        for file in music_files:
            self.local_songs_list.addItem(os.path.basename(file))

    def ytdl_progress_hook(self, status):
        if status['status'] == 'downloading':
            percent = status.get('_percent_str', '').strip()
            speed = status.get('_speed_str', '')
            eta = status.get('_eta_str', '')
            print(f"Downloading: {percent} at {speed} ETA {eta}")
        elif status['status'] == 'finished':
            print("Download complete.")

    def search_youtube(self, query, max_results=5):
        global search_results
        search_results.clear()
        self.results_list.clear()

        ydl_opts = {
            "quiet": True,
            "default_search": "ytsearch",
            "extract_flat": True,
            "force_generic_extractor": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        for entry in info.get("entries", []):
            title, url = entry["title"], entry["url"]
            search_results.append((title, url))
            self.results_list.addItem(title)

    def download_selected(self, downloadType):
        selected = self.results_list.currentRow()
        if selected < 0: return
        title, url = search_results[selected]
        threading.Thread(target=self.download_audio, args=(url, title, downloadType), daemon=True).start()

    def download_audio(self, url, title, downloadType):
        safe_title = sanitize_filename(title)
        mp3_path = os.path.join(self.MUSIC_FOLDER, f"{safe_title}.mp3")
        mp4_path = os.path.join(self.MUSIC_FOLDER, f"{safe_title}.mp4")

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
            "logger": self.logger,
            "progress_hooks": [self.ytdl_progress_hook],
            "noplaylist": True,
        }
        ydl_opts_video = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "outtmpl": mp4_path,
            "ffmpeg_location": FFMPEG_PATH,
            "merge_output_format": "mp4",
            "quiet": True,
            "logger": self.logger,
            "progress_hooks": [self.ytdl_progress_hook],
            "noplaylist": True,
        }

        if downloadType < 3:
            with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                ydl.download([url])
        if downloadType > 1:
            try:
                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                    ydl.download([url])
            except Exception as e:
                print("Video download failed:", e)

        self.load_local_songs()

    # --- Queue/Playback functions (names preserved) ---
    def set_volume(self, vol):
        pygame.mixer.music.set_volume(vol / 100)

    def start_seeking(self):
        global is_seeking
        is_seeking = True

    def stop_seeking(self):
        global is_seeking
        is_seeking = False
        self.seek_to_position(self.playback_slider.value())

    def seek_to_position(self, value):
        global playback_position, start_time, current_song, song_length
        if not current_song: return
        try:
            print(f"Seeking to {value}")
            new_pos = float(value) / 1000 * song_length
            pygame.mixer.music.play(start=new_pos)
            playback_position = new_pos
            start_time = time.time() - new_pos
        except Exception as e:
            print("[ERROR] Seek failed:", e)

    def update_queue_display(self):
        self.queue_list.clear()
        for song in queue:
            self.queue_list.addItem(os.path.basename(song))

    def play_song(self):
        global current_song, is_paused, playback_position, song_length, start_time, queue
        if is_paused and current_song:
            is_paused = False
            pygame.mixer.music.unpause()
            start_time = time.time() - playback_position
            update_discord_status(state="Now Playing", song_title=current_song, paused=False, reset_time=False)
            return
        if not queue:
            self.now_playing_label.setText("Now Playing: None")
            update_discord_status(state="Idle", song_title=None)
            return
        current_song = queue.pop(0)
        song_path = os.path.join(self.MUSIC_FOLDER, current_song)
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            song_length = MP3(song_path).info.length
            playback_position = 0
            start_time = time.time()
            self.now_playing_label.setText(f"Now Playing: {current_song}")
            update_discord_status(state="Now Playing", song_title=current_song, paused=False, reset_time=True)
        except Exception as e:
            print("[ERROR]  playing file:", e)
            current_song = None
        self.update_queue_display()

    def pause_song(self):
        global is_paused, playback_position, current_song, start_time
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            update_discord_status(state="Paused", song_title=current_song, paused=True)
            is_paused = True
            playback_position = time.time() - start_time

    def skip_song(self):
        global current_song
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.play_song()

    def previous_song(self):
        global current_song, queue
        if current_song:
            queue.insert(0, current_song)
            self.play_song()

    def add_to_queue(self, position="end"):
        selected = self.local_songs_list.currentRow()
        if selected < 0: return
        file_name = self.local_songs_list.item(selected).text()
        if position == "now":
            shouldSkip = current_song is not None
            queue.insert(0, file_name)
            if shouldSkip:
                self.skip_song()
                return
            else:
                update_discord_status(state="Now Playing", song_title=file_name, paused=False, reset_time=True)
        elif position == "next":
            queue.insert(0, file_name)
        else:
            queue.append(file_name)
        self.update_queue_display()
        if not pygame.mixer.music.get_busy():
            self.play_song()

    # Playback bar with queue advance
    def update_playback_bar(self):
        global is_paused, current_song, song_length, start_time
        if song_length > 0 and not is_paused and not is_seeking:
            if pygame.mixer.music.get_busy():
                elapsed = time.time() - start_time
                self.playback_slider.blockSignals(True)
                self.playback_slider.setValue(int((elapsed / song_length) * 1000))
                self.playback_slider.blockSignals(False)
            else:
                if current_song and (time.time() - start_time) > (song_length - 1):
                    # Finished, play next
                    _prev = current_song
                    current_song = None
                    self.play_song()

    # Graceful close
    def closeEvent(self, e: QtGui.QCloseEvent):
        cleanup_rpc()
        super().closeEvent(e)

# ------------------------------ Main ------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("BoomBox by Don")
    win = BoomBoxWindow()
    # Center
    screen = app.primaryScreen().availableGeometry()
    win.move(screen.center() - win.rect().center())
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
