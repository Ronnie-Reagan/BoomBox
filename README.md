# 🎧 BoomBox

### A desktop music app for downloading and playing YouTube songs — all in one place.

---

## 🧭 Introduction

BoomBox started as a desktop version of a Discord bot... but it evolved.

It now features:

- 🔍 YouTube search with multi-result support  
- 🎵 MP3 & MP4 download options  
- 📂 Files saved directly to your system’s Music folder  
- 🎛️ Playback controls: pause, seek, volume, queue system  
- 💄 Custom punk rock + hip hop dark UI built on tkinter  
- 🧊 Fully self-contained: just one EXE + FFmpeg folder  

---

## 📦 Download

👉 [**Download the latest release here**](https://github.com/Ronnie-Reagan/BoomBox/releases/tag/BoomBox)

Just download the standalone exe: `BoomBox.exe`.

---

## 🧠 Notes for Users

- Music is saved to your Windows **Music** folder (`C:\Users\<you>\Music`)  
- Songs are named after the YouTube video title  
- If you download too many songs too fast, **YouTube may rate-limit you**  
  - Tip: Stick to **15–20 songs per hour**  
- There's **no "cancel download"** yet — close the app to stop one in progress  

---

## 🛠️ For Developers

Hey boss — this ain’t Ivy League code, but it runs clean.

The codebase is:  
- ✅ Easy to understand  
- ✅ Fully hackable  
- ✅ GUI included (no console window)  
- ✅ Tested with PyInstaller onefile build  

Pull requests welcome. Respect the code, or at least vibe with it.

---

## 🚀 Build It Yourself

- **Huge Note:** You will have to download ffmpeg and the other two binaries manually.
- You must then place the three binaries into the bin folder, a few layers inside the `THIS_FOLDER_MUS..` folder.
- Example Directory Tree Below

### 1. 📦 Dependencies

Install with:

```
pip install -r requirements.txt
```

---

### 2. 🔨 Build the App

Run the included build script:

```
build_boombox.bat
```

This uses:

```
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "BoomBox" ^
  --icon="favicon.ico" ^
  --add-data="THIS_FOLDER_MUST_BE_HERE;." ^
  --add-data="favicon.ico;." ^
  --noconfirm ^
  --clean ^
main.py
```

This produces:  
✅ `dist/BoomBox.exe`  
✅ Fully portable  
✅ No installer required  

---


#### Suggested Working Directory - Use this as a reference to ensure you have proper placement.
```
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
        │   LICENSE
        │   README.txt
        │
        ├───bin
        │       ffmpeg.exe
        │       ffplay.exe
        │       ffprobe.exe
        │
        ├───doc
        │       bootstrap.min.css
        │       community.html
        │       default.css
        │       developer.html
        │       faq.html
        │       fate.html
        │       ffmpeg-all.html
        │       ffmpeg-bitstream-filters.html
        │       ffmpeg-codecs.html
        │       ffmpeg-devices.html
        │       ffmpeg-filters.html
        │       ffmpeg-formats.html
        │       ffmpeg-protocols.html
        │       ffmpeg-resampler.html
        │       ffmpeg-scaler.html
        │       ffmpeg-utils.html
        │       ffmpeg.html
        │       ffplay-all.html
        │       ffplay.html
        │       ffprobe-all.html
        │       ffprobe.html
        │       general.html
        │       git-howto.html
        │       libavcodec.html
        │       libavdevice.html
        │       libavfilter.html
        │       libavformat.html
        │       libavutil.html
        │       libswresample.html
        │       libswscale.html
        │       mailing-list-faq.html
        │       nut.html
        │       platform.html
        │       style.min.css
        │
        └───presets
                libvpx-1080p.ffpreset
                libvpx-1080p50_60.ffpreset
                libvpx-360p.ffpreset
                libvpx-720p.ffpreset
                libvpx-720p50_60.ffpreset
```

---

## 🏴‍☠️ License

> All rights ignored.  
> Built by a pirate, for pirates.  
> Just vibe responsibly.
