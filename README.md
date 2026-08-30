> ### ⚠️ CRITICAL WARNING & LIABILITY DISCLAIMER
> **DEBLOATING AND SYSTEM MODIFICATION UTILITIES CAN CAUSE DEVICE BOOTLOOPS OR CRASHES IF CRITICAL SYSTEM PACKAGES ARE UNINSTALLED.**
> Always make a full data backup of your mobile device before modifying system-level package states. 
> **I AM NOT RESPONSIBLE FOR ANY BRICKED PHONES, LOST DATA, BOOTLOOPS, OR SYSTEM CONFLICTS CAUSED BY THIS SOFTWARE.**
> Use this utility entirely at your own risk. You break it, you buy it!

---

# 📱 ADB Debloater & Optimizer — "GOATED" Edition

A universal, high-performance Tkinter graphical toolkit for Linux that lets you easily manage, debloat, and optimize Android devices over ADB without ever touching a terminal. 

This application operates completely asynchronously, executing shell routines in isolated worker threads to guarantee your desktop interface never hitches, stutters, or freezes during massive package dumps or live log streaming.

---

## 🛠️ Project Origin & Transparency

**Development Method:** This project is vibe-coded by Claude, however the prompt was human-made and I've spotted all the bugs and told AI to patch it.

Unlike low-effort AI projects built to farm subscription money, this tool is 100% free, open-source, and intentionally designed to run light. Every visual edge-case, thread block, and sub-process execution bug was manually audited and patched via targeted human guidance.

Experienced developers are highly encouraged to look over the code, audit the Python subprocess handlers, and submit optimizations via Pull Requests!

---

## ✨ Features Checklist

- **Apps / Debloat Suite:** Real-time search and filter systems to disable, uninstall, clear data, or restore packages. Includes a built-in curation selector to instantly track down known carrier bloatware, a right-click context menu, and a local APK installer.
- **Tweak Manager:** 15 safe, fully reversible optimizations to adjust system animation scales, force GPU rendering, configure cached background limitations, and toggle power-saving architectures.
- **Device Info Panel:** Real-time hardware status metrics parsing model identity, Android version, live battery health, storage allocation, and display resolution.
- **File System Manager:** Complete directory tree layout browsing with fluid push, pull, delete, and folder generation configurations.
- **Screen & Reboot Tools:** Instant wireless ADB pairing, desktop screenshots, screen recording workflows, and one-click system reboots into recovery, bootloader, or fastbootd.
- **Live Logcat Stream:** Async streaming terminal viewer that pulls real-time device logs with fast level and tag search filters.
- **Backup & Profiles:** Export or import your specific debloat layouts as clean JSON profiles, and back up physical APKs of selected apps straight to your local drive.

---

## 📦 Zero-Dependency Architecture

```text
adb-manager/
├── adb_debloater.py        # The entire application (UI and logic in one file)
├── requirements.txt         # Empty / documentation-only manifest
└── LICENSE                  # Apache 2.0 License ledger
```

Because this utility is engineered using the Python Standard Library exclusively (`tkinter`, `subprocess`, `threading`, `json`, `csv`), there are **zero external libraries to install.** No virtual environments or heavy pip compilations are required to keep this app running safely.

---

## 🚀 Full Installation & Configuration Guide

Getting this setup is straightforward, but since we are dealing with hardware interfaces, order matters. Follow these steps to map the hardware connections cleanly.

### Step 1: Initialize Local ADB Tooling
Before booting the interface, your host machine must have the Android Debug Bridge client ready. Install it using your distribution's standard package manager:

```bash
# On Linux Mint / Ubuntu / Debian:
sudo apt install android-tools-adb
```
*Note: For other operating systems, use your native package manager (like `pacman` or `dnf`) to install `adb` or standard Android platform tools.*

Verify the binary is correctly mapped to your execution path by running:
```bash
adb version
```

### Step 2: Configure Your Mobile Device
1. Open your Android phone's settings dashboard, navigate to **About Phone**, and tap **Build Number** 7 times to reveal Developer Options.
2. Enter the new Developer Options submenu and toggle **USB Debugging** to ON.
3. Connect your device to your computer via a data-capable USB cable.
4. Unlock your phone screen. A prompt will appear asking to **Allow USB Debugging**. Check *"Always allow from this computer"* and tap Accept.

Verify the handshake is clean via your terminal:
```bash
adb devices
```
*Make sure it lists your device serial number followed by `device`. If it reads `unauthorized`, unlock your phone screen and accept the pairing prompt!*

---

### Step 3: Launch the Suite
With your phone authorized, simply run the entry script directly from your terminal inside the project directory:

```bash
python3 adb_debloater.py
```

---

### Step 4: Create a One-Click Desktop Icon
Typing terminal paths whenever you want to clean up a device gets old fast. You can create a native application menu shortcut that points directly to your script's relative location. Run this single command inside your project folder:

```bash
mkdir -p ~/.local/share/applications && echo -e "[Desktop Entry]\nType=Application\nName=ADB Optimizer\nComment=Android Optimization Dashboard\nExec=python3 \$(pwd)/adb_debloater.py\nIcon=phone\nCategories=System;Settings;\nTerminal=false" > ~/.local/share/applications/adb-optimizer.desktop
```

**What this did:** This drops a launch icon directly into your desktop system menu. You can now tap your super key, type **ADB Optimizer**, and click to boot the interface instantly without keeping a terminal shell open.

---

## ⚖️ License (The Short Version)

This application is proudly licensed under the **Apache License 2.0**. 

In short: **Do whatever you want with it, I don't care.** Fork it, copy it, alter the themes, or strip the logic blocks. Just do not try to track me down or complain if you delete a critical boot service and have to factory-reset your device. You are completely in the driver's seat!

### Open Source Compliance Notice
This graphical suite functions explicitly as an external UI shell wrapper communicating entirely through standard inter-process execution pipelines. It contains no copy-pasted source fragments or embedded binaries belonging to Google's Android SDK platform tools. It operates completely independently of the upstream command-line tools.
