
# CMPIF2100 Lab Transcriber

A small Windows python app for turning lecture recordings into text transcripts using a local Whisper model. Double-click, pick a `.wav`, pick a destination folder, click Transcribe.

**Windows only.** The setup the app does on first run is Windows-specific. It will not work on macOS or Linux. If you're on one of those, the same underlying tools exist but you'll need to wire them up yourself.

**This tool does not record audio.** It only transcribes existing `.wav` files. If you need to record a lecture in the first place, I recommend the free [Audacity](https://www.audacityteam.org). Audacity records straight to `.wav` and you can point this tool at the resulting file. See the "How to record audio" section below for a walkthrough.

By the end of this guide, you'll have:

- Python installed (if you don't already)
- The transcriber sitting in a folder on your machine
- A `.txt` transcript of whatever audio you point it at, saved next to the audio file
- The Pitt copyright notice automatically appended to every transcript you generate

The guide is written so a complete novice can follow it line-by-line, but the headings are clear enough that if you already know what you're doing, you can skim straight to the parts you need.

---

## Step 1: Install Python

The transcriber is a Python program; you need Python installed for any of this to work. If you've already got Python on your machine for another class (Anaconda counts), skip ahead to Step 2.

To check whether you already have it:

```
Press: Windows key
Type: cmd
Press: Enter
```

In the black window that opens:

```
Type: python --version
Press: Enter
You should see: Python 3.10.x (or any version 3.10 or newer)
```

If you see a version number, you're set. Skip to Step 2.

If instead you see `'python' is not recognized as an internal or external command`, you need to install Python:

1. Open a web browser and go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python 3.x.x** button.
3. Open the installer (`python-3.x.x-amd64.exe`) from your Downloads folder.
4. **Important:** at the bottom of the first installer screen, check the box that says **"Add python.exe to PATH"**. The installer does not check this for you, and you will regret it later if you skip it.
5. Click **Install Now**. Accept the UAC prompt if Windows asks.
6. When it finishes, click **Close**.
7. Close any open Command Prompt windows and reopen one. Re-run `python --version` to confirm.

---

## Step 2: Download the transcriber

At the top of this page, click the green **Code** button, then **Download ZIP**.

Extract the ZIP somewhere convenient. Your Desktop or Documents folder is fine. You'll end up with a folder containing a file called `CMPIF2100_Lab_Transcriber.pyw`. That `.pyw` file is the whole app. There's nothing else to install yet; the script handles the rest itself on first run.

---

## Step 3: First-time setup

Double-click `CMPIF2100_Lab_Transcriber.pyw`.

The very first time you launch it, a small window appears titled **"First-time setup"** with a progress bar that says "Setting things up...". This is the script installing the Python packages it needs. The list:

- **truststore** (tiny, instant)
- **faster-whisper** (the actual speech recognition library; ~30 MB)
- If you have an NVIDIA graphics card: **nvidia-cublas-cu12** and **nvidia-cudnn-cu12** (the libraries that let your GPU do the work; ~1.3 GB combined)

The first two are fast. The two NVIDIA libraries are big and can take several minutes depending on your internet speed. The progress bar visibly advances the whole time so you know it hasn't stalled.

Everything installs into your user's site-packages, so no admin rights are required and nothing on your system outside this app's dependencies is touched.

When setup finishes, the setup window closes and the main window opens. This setup only runs once. Every launch after this opens straight to the main window.

If nothing happens at all when you double-click the file, see Troubleshooting at the bottom.

---

## Step 4: Transcribe an audio file

The main window has three controls:

**Select .wav audio file.** Click this to open a file picker. Find your recording and click Open. The path appears under the button so you can confirm you picked the right file.

**Set destination.** Click this to choose a folder for the output `.txt`. By default this auto-fills to the same folder as your audio file the moment you pick one, which is usually what you want. Only click this button if you want the transcript saved somewhere else.

**Transcribe.** The big blue button on the right. Click it when both fields above are filled in.

After you click Transcribe:

1. The status text at the bottom changes to "Loading model...". The very first time you transcribe anything, the app downloads the Whisper model itself (about 1.5 GB). This is a one-time download; future transcriptions skip past it.
2. Then it changes to "Transcribing on GPU..." (or CPU, if you don't have an NVIDIA card or your GPU fails for some reason). The progress bar at the bottom animates the whole time.
3. When it finishes, a popup tells you exactly where the file was saved.

For reference: on a machine with a modern NVIDIA GPU, a six-minute lecture takes about 20 seconds. On CPU only, the same audio takes around three minutes. Either way the app runs unattended; go grab coffee.

---

## Step 5: Read your transcript

Open the `.txt` file in any text editor. Notepad will do; Notepad++ or VS Code are nicer for long files if you have them installed.

The transcript is plain text, one segment per line. At the very bottom of every file the app generates you'll find:

```
------------------------------------------------------------------------------
The contents of this transcript are the exclusive intellectual property
of the University of Pittsburgh and intended for personal use only.
They are not to be distributed, shared, sold, or otherwise transmitted
without the express permission of the University.
```

This is appended automatically to every file. Leave it there.

---

## How to record audio (Audacity)

This tool does not record. To get a `.wav` file to transcribe in the first place, the simplest free option is **Audacity**:

1. Download Audacity from **https://www.audacityteam.org**.
2. Run the installer. The defaults are all fine.
3. Open Audacity. The big red circle in the toolbar is the **Record** button. Press it before class starts. Press the square **Stop** button when you're done.
4. **File → Export Audio → Save as type: WAV**. Pick a folder you'll remember and click Save.
5. Open the transcriber and point it at the resulting `.wav` file.

Audacity is also useful for trimming silence off the start and end of a recording (drag-select the silent bit, press Delete) before transcribing, which makes the transcript a little cleaner.

A quick mic check before your first real recording is worth doing. Hit Record for a few seconds, hit Stop, hit Play. If you can hear yourself clearly, you're set. If you can't, the wrong input is selected in Audacity's toolbar (the dropdown next to the microphone icon).

---

## How to use it going forward

Once everything is set up, the workflow for every new recording is:

1. Record the lecture in Audacity and export as WAV.
2. Double-click `CMPIF2100_Lab_Transcriber.pyw`.
3. Click **Select .wav audio file**, pick your recording.
4. Click **Transcribe**.
5. Open the resulting `.txt` from the folder.

That's the whole loop. The first time it takes a minute to remember; after a week it's muscle memory.

---

## Troubleshooting

**Nothing happens when I double-click the `.pyw` file.**
Windows doesn't know what to open it with. Right-click the file → **Open with** → **Choose another app** → scroll for **Python** (click **More apps** if you don't see it). Pick `pythonw` if it's listed, otherwise `python`. Check **Always use this app to open .pyw files**, then click OK. Try again.

**The setup window appeared but failed partway through with a red error box.**
The error in the box has the actual reason. Most often this is a network issue or your antivirus blocking pip. Wait a minute and double-click the file again; the script will only try to install whatever didn't finish the first time. If it still fails, copy the error text out of the box and ask in the cohort channel.

**It says "GPU unavailable, using CPU" but I do have an NVIDIA card.**
Your NVIDIA driver is most likely too old for the CUDA libraries the app downloaded. Update your driver through GeForce Experience, or download the latest from **https://www.nvidia.com/Download/index.aspx**. The CPU fallback still produces an identical transcript; the GPU is purely a speed bonus.

**The Transcribe button does nothing when I click it.**
Both pickers need a value before the button does anything useful. If either path field still says `(none selected)`, click that button first and pick a file/folder.

**The progress bar moves but nothing seems to happen for ages.**
First-time use downloads the Whisper model (~1.5 GB) before transcription even starts. The status text says "Loading model..." while this happens. It can take a couple of minutes on a slower connection. After the first time it's instant.

**The transcript has missing parts or garbled words.**
Garbage in, garbage out. Whisper handles clean lecture audio very well. Quiet voices, heavy background noise, or rips of low-quality phone or Zoom recordings will produce uneven transcripts. Recordings made directly in Audacity at default settings are normally fine. If a specific section comes out badly, listen to that section in Audacity; if it's hard for *you* to hear, Whisper will have struggled too.

**The popup says "saved to" but I can't find the file.**
Look in the destination folder you picked (the path was shown under the Set destination button). The filename is the same as your audio file, with `.txt` instead of `.wav`.

---

## Questions or improvements

This guide and tool are maintained by Victor S. [@DatJavaClass](https://github.com/DatJavaClass). If something doesn't match what you're seeing, or you have a suggestion, open an issue on the repo or message me in cohort channels.
