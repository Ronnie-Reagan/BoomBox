import subprocess
import threading
import os
import sys
import platform
import struct
import shutil
from tkinter import Tk, Label, Button, PhotoImage, messagebox
import requests
import zipfile
import io

# --- Settings ---
PYINSTALLER_CMD_TEMPLATE = [
    "{python_exe}",
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "BoomBox 2.1",
    "--icon=favicon.ico",
    "--add-data=THIS_FOLDER_MUST_BE_HERE;.",
    "--add-data=favicon.ico;.",
    "--noconfirm",
    "--clean",
    "main.py"
]

FILES_TO_FETCH = {
    "main.py": "https://raw.githubusercontent.com/Ronnie-Reagan/BoomBox/refs/heads/main/main.py",
    "requirements.txt": "https://raw.githubusercontent.com/Ronnie-Reagan/BoomBox/refs/heads/main/requirements.txt",
    "favicon.ico": "https://raw.githubusercontent.com/Ronnie-Reagan/BoomBox/refs/heads/main/favicon.ico",
}

FFMPEG_DIR = os.path.join("THIS_FOLDER_MUST_BE_HERE", "ffmpeg-full")
FFMPEG_BIN_DIR = os.path.join(FFMPEG_DIR, "bin")
FFMPEG_ZIPS = {
    "64bit": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "32bit": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials-32bit.zip"
}

LOGO_PATH = "DonReaganLogo.png"

# --- Functions ---
def find_python311():
    """Locate Python 3.11 on system. Returns list usable in subprocess.run."""
    # current interpreter
    if sys.version_info[:2] == (3, 11):
        return [sys.executable]

    # py launcher
    py_exe = shutil.which("py")
    if py_exe:
        try:
            result = subprocess.run([py_exe, "-3.11", "--version"], capture_output=True, text=True)
            if "3.11" in (result.stdout + result.stderr):
                return [py_exe, "-3.11"]
        except Exception:
            pass

    # common install locations
    candidates = [
        r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files (x86)\Python311\python.exe"
    ]
    for exe in candidates:
        exe = os.path.expandvars(exe)
        if os.path.exists(exe):
            try:
                result = subprocess.run([exe, "--version"], capture_output=True, text=True)
                if "3.11" in (result.stdout + result.stderr):
                    return [exe]
            except Exception:
                continue
    return None

def check_system():
    """Check Windows OS and Python 3.11 availability."""
    if platform.system() != "Windows":
        messagebox.showerror("OS Unsupported", "This launcher only runs on Windows.")
        return None

    py311 = find_python311()
    if not py311:
        confirmed = messagebox.askyesno(
            "Python 3.11 Not Found",
            "Python 3.11 was not found. The build may fail.\n"
            "Please install Python 3.11.\n"
            "Attempt to proceed anyway?"
        )
        if not confirmed:
            sys.exit()
    return py311

def fetch_files():
    confirm = messagebox.askyesno(
        "Fetch Latest Files",
        "Do you want to download the latest versions of files from the repository?"
    )
    if not confirm:
        return

    try:
        for filename, url in FILES_TO_FETCH.items():
            r = requests.get(url)
            r.raise_for_status()
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"[INFO] Updated {filename}")
        messagebox.showinfo("Success", "Repository files updated!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch files:\n{e}")

def fetch_ffmpeg():
    """Download FFmpeg binaries for Windows if missing"""
    arch = "64bit" if struct.calcsize("P") * 8 == 64 else "32bit"
    zip_url = FFMPEG_ZIPS[arch]

    missing = [f for f in ["ffmpeg.exe", "ffplay.exe", "ffprobe.exe"]
               if not os.path.exists(os.path.join(FFMPEG_BIN_DIR, f))]
    if not missing:
        return True

    confirm = messagebox.askyesno("FFmpeg Missing",
                                  f"FFmpeg binaries are missing for {arch}.\nDownload official build?")
    if not confirm:
        return False

    try:
        os.makedirs(FFMPEG_DIR, exist_ok=True)
        messagebox.showinfo("Downloading", f"Downloading {arch} FFmpeg, please wait...")
        r = requests.get(zip_url, stream=True)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            # Extract only bin files
            for member in zf.namelist():
                if "/bin/" in member:
                    zf.extract(member, FFMPEG_DIR)

        # Move executables to bin folder
        extracted_dirs = [d for d in os.listdir(FFMPEG_DIR)
                          if os.path.isdir(os.path.join(FFMPEG_DIR, d)) and d.startswith("ffmpeg")]
        if not extracted_dirs:
            raise RuntimeError("Failed to find extracted FFmpeg folder in zip.")
        extracted_bin = os.path.join(FFMPEG_DIR, extracted_dirs[0], "bin")
        os.makedirs(FFMPEG_BIN_DIR, exist_ok=True)
        for f in ["ffmpeg.exe", "ffplay.exe", "ffprobe.exe"]:
            src = os.path.join(extracted_bin, f)
            dst = os.path.join(FFMPEG_BIN_DIR, f)
            shutil.move(src, dst)
        messagebox.showinfo("Success", f"{arch} FFmpeg binaries ready!")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to download FFmpeg:\n{e}")
        return False

def run_build(status_label, build_button):
    py311 = check_system()
    if not py311:
        return
    if not fetch_ffmpeg():
        return

    build_button.config(state="disabled")
    status_label.config(text="Building BoomBox...")

    def worker():
        try:
            cmd = []
            for c in PYINSTALLER_CMD_TEMPLATE:
                if c == "{python_exe}":
                    cmd.extend(py311)
                else:
                    cmd.append(c)

            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                status_label.config(text="Build complete! Check /dist folder.")
                messagebox.showinfo("Success", "BoomBox build complete!")
            else:
                status_label.config(text="Build failed.")
                messagebox.showerror("Error", f"Build failed:\n{process.stderr}")
        except Exception as e:
            status_label.config(text="Build failed.")
            messagebox.showerror("Exception", str(e))
        finally:
            build_button.config(state="normal")


    threading.Thread(target=worker, daemon=True).start()

# --- GUI ---
root = Tk()
root.title("BoomBox Build Launcher")
root.geometry("760x1100")
root.configure(bg="#121212")

if os.path.exists(LOGO_PATH):
    logo_img = PhotoImage(file=LOGO_PATH)
    Label(root, image=logo_img, bg="#121212").pack(pady=10)

Label(root, text="BoomBox Build Launcher", font=("Segoe UI", 16, "bold"), fg="#ff3b3b", bg="#121212").pack(pady=10)

status_label = Label(root, text="Ready.", font=("Segoe UI", 12), fg="#ffffff", bg="#121212")
status_label.pack(pady=5)

Button(root, text="Fetch Latest Files", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#4caf50",
       activebackground="#66bb6a", command=fetch_files).pack(pady=10)

build_button = Button(root, text="Start Build", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#ff3b3b",
                      activebackground="#ff5c5c", command=lambda: run_build(status_label, build_button))
build_button.pack(pady=10)

Label(root, text="• Will use Python 3.11 if installed\n"
                 "• THIS_FOLDER_MUST_BE_HERE must exist\n"
                 "• FFmpeg binaries will be fetched if missing\n"
                 "• Output goes to /dist folder",
      font=("Segoe UI", 10), fg="#aaaaaa", bg="#121212", justify="left").pack(pady=10)

root.mainloop()
