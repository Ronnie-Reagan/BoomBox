# 🎧 BoomBox

A desktop music app for searching, downloading, and playing YouTube songs.

---

## Introduction

Originally a desktop Discord bot clone, BoomBox now offers:

- YouTube search with multiple results  
- MP3 & MP4 download options  
- Files saved to your system’s Music folder  
- Playback controls: play, pause, seek, volume, queue  
- Dark-themed tkinter GUI  
- Fully self-contained executable

---

## Download

[Download the latest release](https://github.com/Ronnie-Reagan/BoomBox/releases/tag/BoomBox)  

Standalone EXE: `BoomBox 2.0.exe`

---

## User Notes

- Music is saved to your **Music** folder (`C:\Users\<username>\Music`)  
- Songs are named after the YouTube video title  
- YouTube may rate-limit downloads if done too fast (recommend 15–20 songs per hour)  
- There is no “cancel download” option; close the app to stop a download in progress  

---

## Developer Notes

- Code is readable, hackable, and GUI included  
- Tested with PyInstaller onefile build  
- Pull requests welcome

---

## Build Instructions

Use the [Auto Builder](https://github.com/Ronnie-Reagan/BoomBox/blob/main/RemoteBuilder.py) if youre lazy, it will do everything for you including fetching ffmpeg and the most recent repo files

### 1. Dependencies

FFmpeg is required:  
[https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)

Python dependencies:

```
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
yt-dlp==2025.12.8
pygame==2.6.1
pydub==0.25.1
mutagen==1.47.0
pypresence==4.6.1
PyQt5==5.15.11
```

---

### 2. Build the App

Run the build script:

```
build_boombox.bat
```

`pyinstaller` command used:

```
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "BoomBox 2.0" ^
  --icon="favicon.ico" ^
  --add-data="THIS_FOLDER_MUST_BE_HERE;." ^
  --add-data="favicon.ico;." ^
  --noconfirm ^
  --clean ^
main.py
```

Output:  
- `dist/BoomBox.exe`  
- Fully portable, no installer required  

---

### Suggested Directory Structure

```bash
C:.
│   build_boombox.bat
│   favicon.ico
│   license.txt
│   main.py
│   README.md
│   requirements.txt
│
└───THIS_FOLDER_MUST_BE_HERE
    └───ffmpeg-full
        ├───bin
        │       ffmpeg.exe
        │       ffplay.exe
        │       ffprobe.exe
        ├───doc
        │       [FFmpeg docs]
        └───presets
                [FFmpeg preset files]
```

---

## License

No restrictions. Built by a pirate, for pirates. Use responsibly.
