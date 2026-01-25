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
    "--name", "BoomBox 3.0",
    "--icon=2026/favicon.ico",
    "--add-data=2026/THIS_FOLDER_MUST_BE_HERE;THIS_FOLDER_MUST_BE_HERE",
    "--add-data=2026/favicon.ico;.",
    "--noconfirm",
    "--clean",
    "2026/__main__.py"
]

MODULE_ZIP_URL = "https://github.com/Ronnie-Reagan/BoomBox/archive/refs/heads/main.zip"
REQUIREMENTS_URL = "https://raw.githubusercontent.com/Ronnie-Reagan/BoomBox/refs/heads/main/2026/requirements.txt"

FFMPEG_DIR = os.path.join("2026", "THIS_FOLDER_MUST_BE_HERE", "ffmpeg-full")
FFMPEG_BIN_DIR = os.path.join(FFMPEG_DIR, "bin")
FFMPEG_ZIPS = {
    "64bit": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "32bit": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials-32bit.zip"
}

LOGO_PATH = "2026/DonReaganLogo.png"

# --- Python 3.11 Detection ---
def find_python311():
    if sys.version_info[:2] == (3, 11):
        return [sys.executable]

    py_exe = shutil.which("py")
    if py_exe:
        try:
            result = subprocess.run([py_exe, "-3.11", "--version"], capture_output=True, text=True)
            if "3.11" in (result.stdout + result.stderr):
                return [py_exe, "-3.11"]
        except Exception:
            pass

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

# --- System Check ---
def check_system():
    if platform.system() != "Windows":
        messagebox.showerror("OS Unsupported", "This launcher only runs on Windows.")
        return None

    py311 = find_python311()
    if not py311:
        confirmed = messagebox.askyesno(
            "Python 3.11 Not Found",
            "Python 3.11 was not found. The build may fail.\nPlease install Python 3.11.\nAttempt to proceed anyway?"
        )
        if not confirmed:
            sys.exit()
    return py311

# --- Fetch Latest Module ---
def fetch_module():
    confirm = messagebox.askyesno(
        "Fetch Latest Module",
        "Do you want to download the latest BoomBox module from GitHub?"
    )
    if not confirm:
        return

    try:
        r = requests.get(MODULE_ZIP_URL, stream=True)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for member in zf.namelist():
                if member.startswith("BoomBox-main/2026/"):
                    zf.extract(member, ".")
            extracted_path = os.path.join(".", "BoomBox-main", "2026")
            if os.path.exists(extracted_path):
                if os.path.exists("2026"):
                    shutil.rmtree("2026")
                shutil.move(extracted_path, "2026")
        shutil.rmtree(os.path.join(".", "BoomBox-main"), ignore_errors=True)
        messagebox.showinfo("Success", "Module updated!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch module:\n{e}")

# --- Fetch FFmpeg ---
def fetch_ffmpeg():
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
            for member in zf.namelist():
                if "/bin/" in member:
                    zf.extract(member, FFMPEG_DIR)

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

# --- Install Dependencies ---
def install_requirements(py311):
    try:
        r = requests.get(REQUIREMENTS_URL)
        r.raise_for_status()
        req_file = os.path.join("2026", "requirements.txt")
        with open(req_file, "wb") as f:
            f.write(r.content)

        subprocess.check_call(py311 + ["-m", "pip", "install", "-r", req_file])
        messagebox.showinfo("Success", "Dependencies installed!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to install dependencies:\n{e}")

# --- Build ---
def run_build(status_label, build_button):
    py311 = check_system()
    if not py311:
        return
    if not fetch_ffmpeg():
        return

    status_label.config(text="Installing dependencies...")
    build_button.config(state="disabled")

    def worker():
        try:
            install_requirements(py311)
            status_label.config(text="Building BoomBox...")

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
root.title("BoomBox Remote Builder")
root.geometry("760x1100")
root.configure(bg="#121212")

if os.path.exists(LOGO_PATH):
    logo_img = PhotoImage(file=LOGO_PATH)
    Label(root, image=logo_img, bg="#121212").pack(pady=10)

Label(root, text="BoomBox Build Launcher", font=("Segoe UI", 16, "bold"), fg="#ff3b3b", bg="#121212").pack(pady=10)

status_label = Label(root, text="Ready.", font=("Segoe UI", 12), fg="#ffffff", bg="#121212")
status_label.pack(pady=5)

Button(root, text="Fetch Latest Module", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#4caf50",
       activebackground="#66bb6a", command=fetch_module).pack(pady=10)

build_button = Button(root, text="Start Build", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#ff3b3b",
                      activebackground="#ff5c5c", command=lambda: run_build(status_label, build_button))
build_button.pack(pady=10)

Label(root, text="• Will use Python 3.11 if installed\n"
                 "• 2026/THIS_FOLDER_MUST_BE_HERE must exist\n"
                 "• FFmpeg binaries will be fetched if missing\n"
                 "• Dependencies will be installed automatically\n"
                 "• Output goes to /dist folder",
      font=("Segoe UI", 10), fg="#aaaaaa", bg="#121212", justify="left").pack(pady=10)

root.mainloop()
