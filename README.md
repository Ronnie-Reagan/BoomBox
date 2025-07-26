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
  --add-data="THIS_FOLDER_MUST_BE_HERE/." ^
  --noconfirm ^
  --clean ^
  pydubmain.py
```

This produces:  
✅ `dist/BoomBox.exe`  
✅ Fully portable  
✅ No installer required  

---

## 🏴‍☠️ License

> All rights ignored.  
> Built by a pirate, for pirates.  
> Just vibe responsibly.
