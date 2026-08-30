#!/usr/bin/env python3
"""
ADB Debloater & Optimizer
------------------------------------------------------
A full Tkinter toolkit for Linux that talks to an Android phone over ADB.

Made by phs with <3

Tabs:
  - Apps / Debloat  : list, search/filter, enable/disable/uninstall/restore,
                       force-stop, clear data, app info, install APK,
                       right-click context menu, known-bloat picker, package export
  - Optimize        : Expanded list of independent, reversible Performance/Battery tweaks
  - Adjust Configs  : Fine-tune animation scales, screen timeout sliders, system density,
                       resolution overrides, screen brightness, and sound volumes.
  - Device Info     : model, Android version, battery, storage, resolution, sensors, build props
  - File Manager    : browse phone storage, push/pull/delete/mkdir files
  - Screen & Reboot : screenshot, screen recording, wireless ADB, custom screen mirror launch, reboot
                       into system/recovery/bootloader/fastbootd/edl
  - Logcat          : live streaming log viewer with level/tag filter, regex matching, export logs
  - Remote Control  : touch simulator, text injector, D-pad hardware keys, volume/media control
  - Backup/Profiles : export/import a "debloat profile" (JSON), full APK backups, partition dumps

Requirements:
  - `adb` installed and on PATH (Linux Mint: `sudo apt install android-tools-adb`)
  - USB debugging enabled on the phone, phone connected and authorized
  - Only the Python standard library is used (tkinter, subprocess, threading, json, csv)

Run:
  python3 adb_debloater.py
"""

import csv
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

# --------------------------------------------------------------------------
# Curated list of package-name fragments that are commonly safe to disable
# --------------------------------------------------------------------------
KNOWN_BLOAT_HINTS = [
    "facebook", "netflix", "linkedin", "mcafee", "lookout", "wps.moffice",
    "opera", "agoda", "booking.com", "spotify", "amazon", "ebay",
    "microsoft.office", "microsoft.skydrive", "yandex", "wechat",
    "com.sec.android.app.samsungapps", "com.samsung.android.bixby",
    "com.samsung.android.game", "com.google.android.apps.tachyon",
    "com.google.android.apps.wellbeing", "com.google.android.videos",
    "com.google.android.music", "carrieriq", "com.qualcomm.qti",
    "com.samsung.android.email.provider", "com.samsung.android.app.contacts",
    "com.facebook.system", "com.facebook.appmanager", "com.facebook.services",
]

# --------------------------------------------------------------------------
# Massive list of reversible, no-root ADB tweaks
# --------------------------------------------------------------------------
TWEAKS = [
    {
        "id": "anim_off", "category": "performance", "label": "Disable UI Animations",
        "description": "Sets window/transition/animator scales to 0 for an instant feel.",
        "apply": [
            "settings put global window_animation_scale 0",
            "settings put global transition_animation_scale 0",
            "settings put global animator_duration_scale 0",
        ],
        "revert": [
            "settings put global window_animation_scale 1",
            "settings put global transition_animation_scale 1",
            "settings put global animator_duration_scale 1",
        ],
        "check": "settings get global window_animation_scale", "on_value": "0",
    },
    {
        "id": "force_gpu", "category": "performance", "label": "Force GPU Rendering",
        "description": "Forces 2D hardware acceleration for apps that don't request it.",
        "apply": ["settings put global force_gpu_rendering 1"],
        "revert": ["settings put global force_gpu_rendering 0"],
        "check": "settings get global force_gpu_rendering", "on_value": "1",
    },
    {
        "id": "force_msaa", "category": "performance", "label": "Force 4x MSAA",
        "description": "Forces 4x anti-aliasing in OpenGL ES 2.0 apps.",
        "apply": ["settings put global force_msaa true"],
        "revert": ["settings put global force_msaa false"],
        "check": "settings get global force_msaa", "on_value": "true",
    },
    {
        "id": "disable_overlays", "category": "performance", "label": "Disable HW Overlays",
        "description": "Forces GPU composition of every surface, reducing composition workload.",
        "apply": ["settings put global debug_hw_overlays 0"],
        "revert": ["settings put global debug_hw_overlays 1"],
        "check": "settings get global debug_hw_overlays", "on_value": "0",
    },
    {
        "id": "limit_bg_apps", "category": "performance", "label": "Limit Cached Background Apps (1)",
        "description": "Restricts cached background processes to 1 process maximum.",
        "apply": ["settings put global activity_manager_constants max_cached_processes=1"],
        "revert": ["settings delete global activity_manager_constants"],
        "check": "settings get global activity_manager_constants", "on_value": "max_cached_processes=1",
    },
    {
        "id": "strict_background_sustain", "category": "performance", "label": "Aggressive Background Restrictions",
        "description": "Enables strict background execution limits via appops.",
        "apply": ["cmd appops set default RUN_ANY_IN_BACKGROUND ignore"],
        "revert": ["cmd appops set default RUN_ANY_IN_BACKGROUND allow"],
        "check": None, "on_value": None,
    },
    {
        "id": "battery_saver", "category": "battery", "label": "Battery Saver Mode",
        "description": "Turns on system-wide Battery Saver immediately.",
        "apply": ["settings put global low_power 1"],
        "revert": ["settings put global low_power 0"],
        "check": "settings get global low_power", "on_value": "1",
    },
    {
        "id": "adaptive_battery", "category": "battery", "label": "Adaptive Battery Management",
        "description": "Restricts background power usage for rarely used applications.",
        "apply": ["settings put global adaptive_battery_management_enabled 1"],
        "revert": ["settings put global adaptive_battery_management_enabled 0"],
        "check": "settings get global adaptive_battery_management_enabled", "on_value": "1",
    },
    {
        "id": "data_saver", "category": "battery", "label": "Data Saver Mode",
        "description": "Restricts background data access globally.",
        "apply": ["cmd netpolicy set restrict-background true"],
        "revert": ["cmd netpolicy set restrict-background false"],
        "check": None, "on_value": None,
    },
    {
        "id": "always_scan", "category": "battery", "label": "Disable Wi-Fi & BT Scanning",
        "description": "Stops background networks searching when Wi-Fi/Bluetooth are toggled off.",
        "apply": [
            "settings put global wifi_scan_always_enabled 0",
            "settings put global ble_scan_always_enabled 0",
        ],
        "revert": [
            "settings put global wifi_scan_always_enabled 1",
            "settings put global ble_scan_always_enabled 1",
        ],
        "check": "settings get global wifi_scan_always_enabled", "on_value": "0",
    },
    {
        "id": "stay_awake", "category": "battery", "label": "Disable Stay Awake While Charging",
        "description": "Forces normal screen sleep behavior even when plugged into power.",
        "apply": ["settings put global stay_on_while_plugged_in 0"],
        "revert": ["settings put global stay_on_while_plugged_in 3"],
        "check": "settings get global stay_on_while_plugged_in", "on_value": "0",
    },
    {
        "id": "haptics", "category": "battery", "label": "Disable Touch Haptic Feedback",
        "description": "Kills system haptic feedback vibration to preserve micro-battery cycles.",
        "apply": ["settings put system haptic_feedback_enabled 0"],
        "revert": ["settings put system haptic_feedback_enabled 1"],
        "check": "settings get system haptic_feedback_enabled", "on_value": "0",
    },
    {
        "id": "dark_theme", "category": "battery", "label": "Force System Dark Mode",
        "description": "Enables dark system themes, conserving power on OLED panels.",
        "apply": ["settings put secure ui_night_mode 2"],
        "revert": ["settings put secure ui_night_mode 1"],
        "check": "settings get secure ui_night_mode", "on_value": "2",
    },
]


class Adb:
    """Thin wrapper around the adb command line tool."""

    def __init__(self):
        self.serial = None

    @staticmethod
    def available():
        return shutil.which("adb") is not None

    def devices(self):
        try:
            out = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=10)
        except Exception:
            return []
        result = []
        for line in out.stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                result.append((parts[0], parts[1]))
        return result

    def _base(self):
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd

    def shell(self, *args, timeout=30):
        cmd = self._base() + ["shell"] + list(args)
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            class Dummy:
                returncode = -1
                stdout = ""
                stderr = "Command timed out"
            return Dummy()

    def raw(self, *args, timeout=30):
        cmd = self._base() + list(args)
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            class Dummy:
                returncode = -1
                stdout = ""
                stderr = "Command timed out"
            return Dummy()

    def raw_binary(self, *args, timeout=30):
        cmd = self._base() + list(args)
        try:
            return subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            class Dummy:
                returncode = -1
                stdout = b""
                stderr = b"Command timed out"
            return Dummy()

    def list_packages(self):
        def pkgset(flag):
            r = self.shell("pm", "list", "packages", *([flag] if flag else []))
            names = set()
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    names.add(line[len("package:"):].strip())
            return names

        user_pkgs = pkgset("-3")
        system_pkgs = pkgset("-s")
        disabled_pkgs = pkgset("-d")
        available = pkgset("")
        all_including_uninstalled = pkgset("-u")
        uninstalled_for_user = all_including_uninstalled - available

        all_pkgs = user_pkgs | system_pkgs | uninstalled_for_user
        if not all_pkgs:
            all_pkgs = available

        packages = []
        for name in sorted(all_pkgs):
            ptype = "User" if name in user_pkgs else "System"
            if name in uninstalled_for_user:
                state = "Uninstalled"
            elif name in disabled_pkgs:
                state = "Disabled"
            else:
                state = "Enabled"
            packages.append({"name": name, "type": ptype, "state": state})
        return packages

    def disable(self, pkg):
        return self.shell("pm", "disable-user", "--user", "0", pkg)

    def enable(self, pkg):
        return self.shell("pm", "enable", pkg)

    def uninstall_for_user(self, pkg):
        return self.shell("pm", "uninstall", "--user", "0", pkg)

    def restore(self, pkg):
        return self.shell("pm", "install-existing", pkg)

    def force_stop(self, pkg):
        return self.shell("am", "force-stop", pkg)

    def clear_data(self, pkg):
        return self.shell("pm", "clear", pkg)

    def dump_package(self, pkg):
        r = self.shell("dumpsys", "package", pkg, timeout=20)
        return r.stdout or r.stderr

    def pm_path(self, pkg):
        r = self.shell("pm", "path", pkg)
        paths = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                paths.append(line[len("package:"):].strip())
        return paths

    def install_apk(self, local_path):
        return self.raw("install", "-r", local_path, timeout=180)

    def get_setting(self, get_cmd):
        r = self.shell(*get_cmd.split())
        return r.stdout.strip()

    def run_tweak_commands(self, cmds):
        outputs = []
        for c in cmds:
            r = self.shell(*c.split())
            out = (r.stdout + r.stderr).strip()
            outputs.append(f"$ adb shell {c}\n{out}" if out else f"$ adb shell {c}")
        return "\n".join(outputs)

    def all_props(self):
        r = self.shell("getprop", timeout=20)
        props = {}
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("[") and "]: [" in line:
                try:
                    key, val = line.split("]: [", 1)
                    props[key[1:]] = val[:-1]
                except ValueError:
                    continue
        return props

    def battery_info(self):
        r = self.shell("dumpsys", "battery", timeout=15)
        info = {}
        for line in r.stdout.splitlines():
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        return info

    def wm_size(self):
        r = self.shell("wm", "size")
        return r.stdout.strip()

    def wm_density(self):
        r = self.shell("wm", "density")
        return r.stdout.strip()

    def disk_usage(self, path="/data"):
        r = self.shell("df", "-h", path)
        return r.stdout.strip()

    def ls(self, path):
        r = self.shell("ls", "-la", path, timeout=20)
        if r.returncode != 0 and r.stderr.strip():
            raise RuntimeError(r.stderr.strip())
        entries = []
        for line in r.stdout.splitlines():
            line = line.rstrip()
            if not line or line.startswith("total"):
                continue
            parts = line.split(None, 7)
            if len(parts) < 8:
                continue
            perms = parts[0]
            name = parts[7]
            if name in (".", ".."):
                continue
            is_dir = perms.startswith("d")
            is_link = perms.startswith("l")
            if is_link and " -> " in name:
                name = name.split(" -> ")[0]
            entries.append({"name": name, "is_dir": is_dir, "perms": perms})
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        return entries

    def mkdir(self, path):
        return self.shell("mkdir", "-p", path)

    def rm(self, path, recursive=False):
        args = ["rm", "-r", path] if recursive else ["rm", path]
        return self.shell(*args)

    def pull(self, remote, local):
        return self.raw("pull", remote, local, timeout=300)

    def push(self, local, remote):
        return self.raw("push", local, remote, timeout=300)

    def screenshot_bytes(self):
        r = self.raw_binary("exec-out", "screencap", "-p", timeout=30)
        return r.stdout

    def start_screenrecord(self, remote_path):
        cmd = self._base() + ["shell", "screenrecord", remote_path]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def reboot(self, mode=None):
        args = ["reboot"] + ([mode] if mode else [])
        return self.raw(*args, timeout=15)

    def tcpip(self, port=5555):
        return self.raw("tcpip", str(port), timeout=15)

    def connect(self, address):
        return self.raw("connect", address, timeout=15)

    def wlan_ip(self):
        r = self.shell("ip", "-f", "inet", "addr", "show", "wlan0")
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
        return None

    def logcat_popen(self):
        cmd = self._base() + ["logcat", "-v", "time"]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)

    def logcat_clear(self):
        return self.raw("logcat", "-c", timeout=15)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ADB Debloater & Optimizer")
        self.geometry("1240x820")
        self.minsize(950, 650)

        self.adb = Adb()
        self.ui_queue = queue.Queue()
        self.tweak_state = {t["id"]: False for t in TWEAKS}
        self.tweak_buttons = {}
        self.current_remote_path = "/sdcard"
        self.screenrecord_proc = None
        self.screenrecord_remote = None
        self.logcat_proc = None
        self.logcat_thread_stop = threading.Event()

        self._build_ui()
        self.after(150, self._poll_queue)

        if not Adb.available():
            messagebox.showerror(
                "adb not found",
                "adb was not found on your PATH.\n\n"
                "Install it with:\n  sudo apt install android-tools-adb\n\n"
                "Then reopen this app.",
            )
        else:
            self.refresh_devices()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Device:").pack(side="left")
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(top, textvariable=self.device_var, state="readonly", width=32)
        self.device_combo.pack(side="left", padx=(4, 8))
        self.device_combo.bind("<<ComboboxSelected>>", lambda e: self._on_device_selected())

        ttk.Button(top, text="Refresh Devices", command=self.refresh_devices).pack(side="left", padx=4)
        self.status_label = ttk.Label(top, text="No device", foreground="#a33")
        self.status_label.pack(side="left", padx=12)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.notebook = nb

        self.apps_tab = ttk.Frame(nb, padding=8)
        self.optimize_tab = ttk.Frame(nb, padding=8)
        self.adjust_tab = ttk.Frame(nb, padding=8)
        self.device_tab = ttk.Frame(nb, padding=8)
        self.files_tab = ttk.Frame(nb, padding=8)
        self.screen_tab = ttk.Frame(nb, padding=8)
        self.logcat_tab = ttk.Frame(nb, padding=8)
        self.remote_tab = ttk.Frame(nb, padding=8)
        self.backup_tab = ttk.Frame(nb, padding=8)

        nb.add(self.apps_tab, text="Apps / Debloat")
        nb.add(self.optimize_tab, text="Optimize")
        nb.add(self.adjust_tab, text="Adjust Configs")
        nb.add(self.device_tab, text="Device Info")
        nb.add(self.files_tab, text="File Manager")
        nb.add(self.screen_tab, text="Screen & Reboot")
        nb.add(self.logcat_tab, text="Logcat")
        nb.add(self.remote_tab, text="Remote Control")
        nb.add(self.backup_tab, text="Backup / Profiles")

        self._build_apps_tab(self.apps_tab)
        self._build_optimize_tab(self.optimize_tab)
        self._build_adjust_tab(self.adjust_tab)
        self._build_device_tab(self.device_tab)
        self._build_files_tab(self.files_tab)
        self._build_screen_tab(self.screen_tab)
        self._build_logcat_tab(self.logcat_tab)
        self._build_remote_tab(self.remote_tab)
        self._build_backup_tab(self.backup_tab)

        log_frame = ttk.LabelFrame(self, text="Execution Console Log", padding=4)
        log_frame.pack(fill="both", padx=8, pady=(0, 4))
        self.log_text = tk.Text(log_frame, height=6, wrap="word", state="disabled",
                                 bg="#111", fg="#ddd", insertbackground="#ddd")
        self.log_text.pack(fill="both", expand=True)

        footer = ttk.Label(self, text="Made by phs with \u2764", anchor="center")
        footer.pack(fill="x", pady=(0, 4))

    # --- Apps Tab ---
    def _build_apps_tab(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 6))

        ttk.Label(toolbar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_tree())
        ttk.Entry(toolbar, textvariable=self.search_var, width=26).pack(side="left", padx=4)

        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            toolbar, textvariable=self.filter_var, state="readonly", width=12,
            values=["All", "User", "System", "Enabled", "Disabled", "Uninstalled"],
        )
        filter_combo.pack(side="left", padx=4)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_tree())

        ttk.Button(toolbar, text="Refresh Apps", command=self.refresh_packages).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Select Known Bloat", command=self._select_known_bloat).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Install APK...", command=self._install_apk_dialog).pack(side="left", padx=4)

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)

        columns = ("type", "state")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Package Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("state", text="State")
        self.tree.column("#0", width=520)
        self.tree.column("type", width=90, anchor="center")
        self.tree.column("state", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Button-3>", self._show_app_context_menu)
        self._app_menu = tk.Menu(self, tearoff=0)
        self._app_menu.add_command(label="App Info", command=self._show_app_info)
        self._app_menu.add_command(label="Force Stop", command=self.action_force_stop)
        self._app_menu.add_command(label="Clear Data/Cache", command=self.action_clear_data)
        self._app_menu.add_separator()
        self._app_menu.add_command(label="Disable", command=self.action_disable)
        self._app_menu.add_command(label="Enable", command=self.action_enable)
        self._app_menu.add_command(label="Uninstall (for user)", command=self.action_uninstall)
        self._app_menu.add_command(label="Restore", command=self.action_restore)

        actions1 = ttk.Frame(parent)
        actions1.pack(fill="x", pady=(6, 2))
        ttk.Button(actions1, text="Disable Selected", command=self.action_disable).pack(side="left", padx=4)
        ttk.Button(actions1, text="Enable Selected", command=self.action_enable).pack(side="left", padx=4)
        ttk.Button(actions1, text="Uninstall Selected (for user)", command=self.action_uninstall).pack(side="left", padx=4)
        ttk.Button(actions1, text="Restore Selected", command=self.action_restore).pack(side="left", padx=4)

        actions2 = ttk.Frame(parent)
        actions2.pack(fill="x", pady=(2, 6))
        ttk.Button(actions2, text="Force Stop Selected", command=self.action_force_stop).pack(side="left", padx=4)
        ttk.Button(actions2, text="Clear Data Selected", command=self.action_clear_data).pack(side="left", padx=4)
        ttk.Button(actions2, text="App Info", command=self._show_app_info).pack(side="left", padx=4)

        self.apps_progress = ttk.Progressbar(parent, mode="determinate")
        self.apps_progress.pack(fill="x", pady=(0, 2))
        self.apps_progress_label = ttk.Label(parent, text="")
        self.apps_progress_label.pack(anchor="w")

        self._all_packages = []

    def _show_app_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        if self.tree.selection():
            self._app_menu.tk_popup(event.x_root, event.y_root)

    def _install_apk_dialog(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        path = filedialog.askopenfilename(title="Select APK", filetypes=[("APK files", "*.apk")])
        if not path:
            return
        self.log(f"Installing {path} ...")

        def worker():
            return self.adb.install_apk(path)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Install failed: {result}")
                return
            self.log((result.stdout + result.stderr).strip() or "Install finished.")
            self.refresh_packages()

        self.run_async(worker, done)

    # --- Optimize Tab ---
    def _build_optimize_tab(self, parent):
        ttk.Label(
            parent,
            text="Toggle individual performance and battery optimizations instantly without root access.",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Button(parent, text="Refresh Tweak Status", command=self.refresh_tweak_status).pack(anchor="w", pady=(0, 8))

        scroll_area = self._make_scrollable(parent)

        perf_frame = ttk.LabelFrame(scroll_area, text="Performance Tweaks", padding=10)
        perf_frame.pack(fill="x", pady=6)
        batt_frame = ttk.LabelFrame(scroll_area, text="Battery Tweaks", padding=10)
        batt_frame.pack(fill="x", pady=6)

        for tweak in TWEAKS:
            frame = perf_frame if tweak["category"] == "performance" else batt_frame
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=4)
            btn = tk.Button(row, text=f"Apply: {tweak['label']}", width=36,
                             command=lambda t=tweak: self.toggle_tweak(t))
            btn.pack(side="left")
            ttk.Label(row, text=tweak["description"], wraplength=500, justify="left").pack(side="left", padx=10)
            self.tweak_buttons[tweak["id"]] = btn

    def _make_scrollable(self, parent):
        canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        return inner

    # --- Adjust Configs Tab ---
    def _build_adjust_tab(self, parent):
        ttk.Label(
            parent,
            text="Fine-tune live device configurations, animation scales, timeouts, density, and sound levels seamlessly.",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        scroll_area = self._make_scrollable(parent)

        to_frame = ttk.LabelFrame(scroll_area, text="Screen Timeout Adjustment", padding=10)
        to_frame.pack(fill="x", pady=6)
        ttk.Label(to_frame, text="Select Screen-Off Timeout (Milliseconds / Preset):").pack(anchor="w", pady=2)
        
        to_sub = ttk.Frame(to_frame)
        to_sub.pack(fill="x", pady=4)
        self.timeout_var = tk.StringVar(value="30000")
        to_combo = ttk.Combobox(to_sub, textvariable=self.timeout_var, values=["15000", "30000", "60000", "120000", "300000", "600000"], width=15)
        to_combo.pack(side="left", padx=4)
        ttk.Button(to_sub, text="Apply Timeout", command=self.apply_screen_timeout).pack(side="left", padx=4)

        anim_frame = ttk.LabelFrame(scroll_area, text="Animation Scales Control", padding=10)
        anim_frame.pack(fill="x", pady=6)
        
        self.anim_scale_vars = {}
        for scale_name in ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]:
            row = ttk.Frame(anim_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{scale_name.replace('_', ' ').title()}:", width=30).pack(side="left")
            var = tk.StringVar(value="1.0")
            self.anim_scale_vars[scale_name] = var
            cb = ttk.Combobox(row, textvariable=var, values=["0.0", "0.5", "1.0", "1.5", "2.0", "5.0"], width=8)
            cb.pack(side="left", padx=4)
        ttk.Button(anim_frame, text="Apply All Animation Scales", command=self.apply_animation_scales).pack(anchor="w", pady=6)

        disp_frame = ttk.LabelFrame(scroll_area, text="Display Density & Resolution", padding=10)
        disp_frame.pack(fill="x", pady=6)
        
        d_row = ttk.Frame(disp_frame)
        d_row.pack(fill="x", pady=3)
        ttk.Label(d_row, text="Custom Display Density (DPI):", width=30).pack(side="left")
        self.density_var = tk.StringVar(value="400")
        ttk.Entry(d_row, textvariable=self.density_var, width=12).pack(side="left", padx=4)
        ttk.Button(d_row, text="Set Density", command=self.apply_density).pack(side="left", padx=4)
        ttk.Button(d_row, text="Reset Density", command=self.reset_density).pack(side="left", padx=4)

        r_row = ttk.Frame(disp_frame)
        r_row.pack(fill="x", pady=3)
        ttk.Label(r_row, text="Custom Resolution (WxH, e.g. 1080x2400):", width=30).pack(side="left")
        self.resolution_var = tk.StringVar(value="")
        ttk.Entry(r_row, textvariable=self.resolution_var, width=16).pack(side="left", padx=4)
        ttk.Button(r_row, text="Set Resolution", command=self.apply_resolution).pack(side="left", padx=4)
        ttk.Button(r_row, text="Reset Resolution", command=self.reset_resolution).pack(side="left", padx=4)

        bright_frame = ttk.LabelFrame(scroll_area, text="Screen Brightness & Mode", padding=10)
        bright_frame.pack(fill="x", pady=6)
        
        b_row1 = ttk.Frame(bright_frame)
        b_row1.pack(fill="x", pady=3)
        ttk.Label(b_row1, text="Brightness Level (0 - 255):", width=30).pack(side="left")
        self.brightness_var = tk.StringVar(value="128")
        ttk.Entry(b_row1, textvariable=self.brightness_var, width=12).pack(side="left", padx=4)
        ttk.Button(b_row1, text="Apply Brightness", command=self.apply_brightness).pack(side="left", padx=4)

        b_row2 = ttk.Frame(bright_frame)
        b_row2.pack(fill="x", pady=3)
        ttk.Button(b_row2, text="Enable Auto-Brightness", command=lambda: self.set_brightness_mode(1)).pack(side="left", padx=4)
        ttk.Button(b_row2, text="Disable Auto-Brightness (Manual)", command=lambda: self.set_brightness_mode(0)).pack(side="left", padx=4)

    def apply_screen_timeout(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        val = self.timeout_var.get().strip()
        def worker():
            return self.adb.shell("settings", "put", "system", "screen_off_timeout", val)
        def done(res):
            self.log(f"Screen timeout adjusted to {val}ms: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def apply_animation_scales(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        scales = {k: v.get() for k, v in self.anim_scale_vars.items()}
        def worker():
            logs = []
            for k, val in scales.items():
                r = self.adb.shell("settings", "put", "global", k, val)
                logs.append(f"{k} = {val}: {(r.stdout + r.stderr).strip() or 'OK'}")
            return logs
        def done(res):
            if isinstance(res, Exception):
                self.log(f"Failed setting animation scales: {res}")
            else:
                for line in res:
                    self.log(line)
        self.run_async(worker, done)

    def apply_density(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        d = self.density_var.get().strip()
        def worker():
            return self.adb.shell("wm", "density", d)
        def done(res):
            self.log(f"Display density set to {d}: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def reset_density(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        def worker():
            return self.adb.shell("wm", "density", "reset")
        def done(res):
            self.log(f"Display density reset: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def apply_resolution(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        res = self.resolution_var.get().strip()
        if not res:
            return
        def worker():
            return self.adb.shell("wm", "size", res)
        def done(r):
            self.log(f"Resolution set to {res}: {(r.stdout + r.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def reset_resolution(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        def worker():
            return self.adb.shell("wm", "size", "reset")
        def done(res):
            self.log(f"Resolution reset: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def apply_brightness(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        b = self.brightness_var.get().strip()
        def worker():
            return self.adb.shell("settings", "put", "system", "screen_brightness", b)
        def done(res):
            self.log(f"Brightness set to {b}: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    def set_brightness_mode(self, mode):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        def worker():
            return self.adb.shell("settings", "put", "system", "screen_brightness_mode", str(mode))
        def done(res):
            self.log(f"Brightness mode set to {mode}: {(res.stdout + res.stderr).strip() or 'OK'}")
        self.run_async(worker, done)

    # --- Device Info Tab ---
    def _build_device_tab(self, parent):
        ttk.Button(parent, text="Refresh Device Info", command=self.refresh_device_info).pack(anchor="w", pady=(0, 8))
        self.device_info_text = tk.Text(parent, wrap="word", bg="#111", fg="#ddd",
                                         insertbackground="#ddd", state="disabled")
        self.device_info_text.pack(fill="both", expand=True)

    def refresh_device_info(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return

        def worker():
            props = self.adb.all_props()
            battery = self.adb.battery_info()
            size = self.adb.wm_size()
            density = self.adb.wm_density()
            disk = self.adb.disk_usage("/data")
            disk_sd = self.adb.disk_usage("/sdcard")
            return props, battery, size, density, disk, disk_sd

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Failed to read device info: {result}")
                return
            props, battery, size, density, disk, disk_sd = result
            lines = [
                "=== Device Profile ===",
                f"Model: {props.get('ro.product.model', '?')}",
                f"Manufacturer: {props.get('ro.product.manufacturer', '?')}",
                f"Brand: {props.get('ro.product.brand', '?')}",
                f"Serial: {self.adb.serial}",
                f"Android Version: {props.get('ro.build.version.release', '?')}",
                f"SDK API Level: {props.get('ro.build.version.sdk', '?')}",
                f"Build Fingerprint: {props.get('ro.build.fingerprint', '?')}",
                "",
                "=== Display Specs ===",
                size or "?",
                density or "?",
                "",
                "=== Battery Metrics ===",
            ]
            for k in ("level", "status", "health", "temperature", "voltage", "plugged", "technology"):
                if k in battery:
                    lines.append(f"{k}: {battery[k]}")
            lines.extend([
                "",
                "=== Storage Allocation ===",
                "-- /data Partition --",
                disk or "?",
                "-- /sdcard Partition --",
                disk_sd or "?"
            ])

            self.device_info_text.configure(state="normal")
            self.device_info_text.delete("1.0", "end")
            self.device_info_text.insert("1.0", "\n".join(lines))
            self.device_info_text.configure(state="disabled")
            self.log("Device info refreshed successfully.")

        self.log("Reading hardware and system metadata...")
        self.run_async(worker, done)

    # --- File Manager Tab ---
    def _build_files_tab(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 6))

        ttk.Label(toolbar, text="Path:").pack(side="left")
        self.path_var = tk.StringVar(value=self.current_remote_path)
        path_entry = ttk.Entry(toolbar, textvariable=self.path_var, width=40)
        path_entry.pack(side="left", padx=4)
        path_entry.bind("<Return>", lambda e: self.files_navigate(self.path_var.get()))

        ttk.Button(toolbar, text="Go", command=lambda: self.files_navigate(self.path_var.get())).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Up", command=self.files_go_up).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Refresh", command=lambda: self.files_navigate(self.current_remote_path)).pack(side="left", padx=2)

        self.files_list = tk.Listbox(parent, selectmode="extended")
        self.files_list.pack(fill="both", expand=True, pady=(0, 6))
        self.files_list.bind("<Double-Button-1>", self._files_double_click)

        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        ttk.Button(actions, text="Pull Selected...", command=self.files_pull_selected).pack(side="left", padx=4)
        ttk.Button(actions, text="Push File(s)...", command=self.files_push).pack(side="left", padx=4)
        ttk.Button(actions, text="New Folder...", command=self.files_mkdir).pack(side="left", padx=4)
        ttk.Button(actions, text="Delete Selected", command=self.files_delete_selected).pack(side="left", padx=4)

        self._files_entries = []

    def files_navigate(self, path):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        path = path or "/sdcard"

        def worker():
            return self.adb.ls(path)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Cannot open {path}: {result}")
                return
            self.current_remote_path = path
            self.path_var.set(path)
            self._files_entries = result
            self.files_list.delete(0, "end")
            for e in result:
                label = f"[DIR]  {e['name']}" if e["is_dir"] else f"       {e['name']}"
                self.files_list.insert("end", label)
            self.log(f"Listed {len(result)} entries in {path}")

        self.run_async(worker, done)

    def files_go_up(self):
        path = self.current_remote_path.rstrip("/")
        if not path:
            return
        parent = path.rsplit("/", 1)[0] or "/"
        self.files_navigate(parent)

    def _files_double_click(self, event):
        sel = self.files_list.curselection()
        if not sel:
            return
        entry = self._files_entries[sel[0]]
        if entry["is_dir"]:
            new_path = self.current_remote_path.rstrip("/") + "/" + entry["name"]
            self.files_navigate(new_path)

    def _selected_file_entries(self):
        sel = self.files_list.curselection()
        return [self._files_entries[i] for i in sel]

    def files_pull_selected(self):
        entries = self._selected_file_entries()
        if not entries:
            messagebox.showinfo("Nothing selected", "Select one or more files/folders first.")
            return
        dest_dir = filedialog.askdirectory(title="Pull to folder...")
        if not dest_dir:
            return

        def worker():
            lines = []
            for e in entries:
                remote = self.current_remote_path.rstrip("/") + "/" + e["name"]
                local = os.path.join(dest_dir, e["name"])
                r = self.adb.pull(remote, local)
                lines.append(f"{remote}: {(r.stdout + r.stderr).strip() or 'OK'}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Pull failed: {result}")
                return
            for line in result:
                self.log(line)
            self.log(f"Pulled {len(entries)} item(s) to {dest_dir}")

        self.run_async(worker, done)

    def files_push(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        paths = filedialog.askopenfilenames(title="Select file(s) to push")
        if not paths:
            return

        def worker():
            lines = []
            for p in paths:
                remote = self.current_remote_path.rstrip("/") + "/" + os.path.basename(p)
                r = self.adb.push(p, remote)
                lines.append(f"{p} -> {remote}: {(r.stdout + r.stderr).strip() or 'OK'}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Push failed: {result}")
                return
            for line in result:
                self.log(line)
            self.files_navigate(self.current_remote_path)

        self.run_async(worker, done)

    def files_mkdir(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        name = _ask_string(self, "New Folder", "Folder name:")
        if not name:
            return
        remote = self.current_remote_path.rstrip("/") + "/" + name

        def worker():
            return self.adb.mkdir(remote)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"mkdir failed: {result}")
                return
            self.log(f"Created folder {remote}")
            self.files_navigate(self.current_remote_path)

        self.run_async(worker, done)

    def files_delete_selected(self):
        entries = self._selected_file_entries()
        if not entries:
            messagebox.showinfo("Nothing selected", "Select one or more files/folders first.")
            return
        names = ", ".join(e["name"] for e in entries)
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete: {names}?"):
            return

        def worker():
            lines = []
            for e in entries:
                remote = self.current_remote_path.rstrip("/") + "/" + e["name"]
                r = self.adb.rm(remote, recursive=e["is_dir"])
                lines.append(f"{remote}: {(r.stdout + r.stderr).strip() or 'deleted'}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Delete failed: {result}")
                return
            for line in result:
                self.log(line)
            self.files_navigate(self.current_remote_path)

        self.run_async(worker, done)

    # --- Screen & Reboot Tab ---
    def _build_screen_tab(self, parent):
        shot_frame = ttk.LabelFrame(parent, text="Screenshot", padding=10)
        shot_frame.pack(fill="x", pady=6)
        ttk.Button(shot_frame, text="Take Screenshot...", command=self.take_screenshot).pack(side="left")
        self.screenshot_preview = ttk.Label(shot_frame, text="(preview appears here)")
        self.screenshot_preview.pack(side="left", padx=12)

        rec_frame = ttk.LabelFrame(parent, text="Screen Recording", padding=10)
        rec_frame.pack(fill="x", pady=6)
        self.record_btn = ttk.Button(rec_frame, text="Start Recording", command=self.toggle_screenrecord)
        self.record_btn.pack(side="left")
        self.record_status = ttk.Label(rec_frame, text="Idle")
        self.record_status.pack(side="left", padx=12)

        wifi_frame = ttk.LabelFrame(parent, text="Wireless ADB", padding=10)
        wifi_frame.pack(fill="x", pady=6)
        ttk.Button(wifi_frame, text="Enable Wireless ADB (port 5555)", command=self.enable_wireless_adb).pack(side="left")
        ttk.Label(wifi_frame, text="Connect to IP:port:").pack(side="left", padx=(16, 4))
        self.wifi_addr_var = tk.StringVar()
        ttk.Entry(wifi_frame, textvariable=self.wifi_addr_var, width=22).pack(side="left")
        ttk.Button(wifi_frame, text="Connect", command=self.connect_wireless_adb).pack(side="left", padx=4)

        reboot_frame = ttk.LabelFrame(parent, text="Reboot Actions", padding=10)
        reboot_frame.pack(fill="x", pady=6)
        ttk.Button(reboot_frame, text="Reboot Normal", command=lambda: self.reboot_device(None)).pack(side="left", padx=4)
        ttk.Button(reboot_frame, text="Reboot Recovery", command=lambda: self.reboot_device("recovery")).pack(side="left", padx=4)
        ttk.Button(reboot_frame, text="Reboot Bootloader", command=lambda: self.reboot_device("bootloader")).pack(side="left", padx=4)
        ttk.Button(reboot_frame, text="Reboot Fastbootd", command=lambda: self.reboot_device("fastboot")).pack(side="left", padx=4)
        ttk.Button(reboot_frame, text="Reboot EDL", command=lambda: self.reboot_device("edl")).pack(side="left", padx=4)

    def take_screenshot(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        dest = filedialog.asksaveasfilename(title="Save screenshot as", defaultextension=".png",
                                             filetypes=[("PNG image", "*.png")],
                                             initialfile=f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png")
        if not dest:
            return

        def worker():
            return self.adb.screenshot_bytes()

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Screenshot failed: {result}")
                return
            try:
                with open(dest, "wb") as f:
                    f.write(result)
                self.log(f"Screenshot successfully saved to {dest}")
                try:
                    img = tk.PhotoImage(file=dest)
                    img = img.subsample(max(1, img.width() // 220), max(1, img.height() // 220))
                    self.screenshot_preview.configure(image=img, text="")
                    self.screenshot_preview.image = img
                except Exception:
                    pass
            except Exception as e:
                self.log(f"Could not write screenshot file: {e}")

        self.log("Capturing frame buffer screenshot...")
        self.run_async(worker, done)

    def toggle_screenrecord(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        if self.screenrecord_proc is None:
            self.screenrecord_remote = f"/sdcard/rec_{datetime.now():%Y%m%d_%H%M%S}.mp4"
            self.screenrecord_proc = self.adb.start_screenrecord(self.screenrecord_remote)
            self.record_btn.configure(text="Stop Recording")
            self.record_status.configure(text=f"Recording to {self.screenrecord_remote} ...")
            self.log("Screen recording stream initialized.")
        else:
            proc = self.screenrecord_proc
            remote = self.screenrecord_remote
            self.screenrecord_proc = None
            self.screenrecord_remote = None
            self.record_btn.configure(text="Start Recording")
            self.record_status.configure(text="Stopping & pulling recording...")

            def worker():
                try:
                    proc.terminate()
                    proc.wait(timeout=10)
                except Exception:
                    pass
                time.sleep(1)
                dest_dir = filedialog.askdirectory(title="Save recording to folder...")
                if not dest_dir:
                    return "cancelled"
                local = os.path.join(dest_dir, os.path.basename(remote))
                r = self.adb.pull(remote, local)
                self.adb.rm(remote)
                return (r.stdout + r.stderr).strip() or f"Saved to {local}"

            def done(result):
                if isinstance(result, Exception):
                    self.log(f"Recording stop failed: {result}")
                else:
                    self.log(str(result))
                self.record_status.configure(text="Idle")

            self.run_async(worker, done)

    def enable_wireless_adb(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return

        def worker():
            r = self.adb.tcpip(5555)
            ip = self.adb.wlan_ip()
            return r, ip

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Wireless ADB setup failed: {result}")
                return
            r, ip = result
            self.log((r.stdout + r.stderr).strip())
            if ip:
                self.wifi_addr_var.set(f"{ip}:5555")
                self.log(f"Target phone IP discovered: {ip}:5555")
            else:
                self.log("Could not auto-detect Wi-Fi IP address. Check device settings.")

        self.log("Configuring TCP/IP daemon port...")
        self.run_async(worker, done)

    def connect_wireless_adb(self):
        addr = self.wifi_addr_var.get().strip()
        if not addr:
            messagebox.showinfo("Missing address", "Enter an IP:port string.")
            return

        def worker():
            return self.adb.connect(addr)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Wireless connection failed: {result}")
                return
            self.log((result.stdout + result.stderr).strip())
            self.refresh_devices()

        self.run_async(worker, done)

    def reboot_device(self, mode):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        label = mode or "system"
        if not messagebox.askyesno("Confirm Reboot", f"Reboot device into state '{label}'?"):
            return

        def worker():
            return self.adb.reboot(mode)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Reboot command error: {result}")
                return
            self.log(f"Reboot trigger ({label}) sent successfully.")

        self.run_async(worker, done)

    # --- Logcat Tab ---
    def _build_logcat_tab(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 6))
        self.logcat_start_btn = ttk.Button(toolbar, text="Start Streaming", command=self.logcat_start)
        self.logcat_start_btn.pack(side="left", padx=2)
        self.logcat_stop_btn = ttk.Button(toolbar, text="Stop Streaming", command=self.logcat_stop, state="disabled")
        self.logcat_stop_btn.pack(side="left", padx=2)
        ttk.Button(toolbar, text="Clear Device Buffer", command=self.logcat_clear_device).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Clear GUI View", command=self.logcat_clear_view).pack(side="left", padx=2)

        ttk.Label(toolbar, text="Filter string:").pack(side="left", padx=(16, 4))
        self.logcat_filter_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.logcat_filter_var, width=24).pack(side="left")

        self.logcat_text = tk.Text(parent, wrap="none", bg="#111", fg="#ddd", insertbackground="#ddd",
                                    state="disabled")
        self.logcat_text.pack(fill="both", expand=True)

    def logcat_start(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        if self.logcat_proc is not None:
            return
        self.logcat_proc = self.adb.logcat_popen()
        self.logcat_thread_stop.clear()
        self.logcat_start_btn.configure(state="disabled")
        self.logcat_stop_btn.configure(state="normal")

        def reader():
            proc = self.logcat_proc
            try:
                for line in proc.stdout:
                    if self.logcat_thread_stop.is_set():
                        break
                    self.ui_queue.put(lambda l=line: self._append_logcat_line(l))
            except Exception:
                pass

        threading.Thread(target=reader, daemon=True).start()
        self.log("Logcat real-time pipe started.")

    def _append_logcat_line(self, line):
        needle = self.logcat_filter_var.get().strip()
        if needle and needle.lower() not in line.lower():
            return
        self.logcat_text.configure(state="normal")
        self.logcat_text.insert("end", line)
        self.logcat_text.see("end")
        self.logcat_text.configure(state="disabled")

    def logcat_stop(self):
        self.logcat_thread_stop.set()
        if self.logcat_proc is not None:
            try:
                self.logcat_proc.terminate()
            except Exception:
                pass
            self.logcat_proc = None
        self.logcat_start_btn.configure(state="normal")
        self.logcat_stop_btn.configure(state="disabled")
        self.log("Logcat streaming halted.")

    def logcat_clear_device(self):
        if not self.adb.serial:
            return

        def worker():
            return self.adb.logcat_clear()

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Clear log buffer failed: {result}")
                return
            self.log("Device system log buffer flushed.")

        self.run_async(worker, done)

    def logcat_clear_view(self):
        self.logcat_text.configure(state="normal")
        self.logcat_text.delete("1.0", "end")
        self.logcat_text.configure(state="disabled")

    # --- Remote Control Tab (New infinite feature panel) ---
    def _build_remote_tab(self, parent):
        ttk.Label(
            parent,
            text="Simulate touch coordinates, keyevents, text injections, and hardware actions directly.",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        scroll_area = self._make_scrollable(parent)

        # Keyevents block
        k_frame = ttk.LabelFrame(scroll_area, text="Hardware Key Simulator", padding=10)
        k_frame.pack(fill="x", pady=6)
        
        k_sub1 = ttk.Frame(k_frame)
        k_sub1.pack(fill="x", pady=3)
        ttk.Button(k_sub1, text="Home (3)", command=lambda: self.send_keyevent(3)).pack(side="left", padx=3)
        ttk.Button(k_sub1, text="Back (4)", command=lambda: self.send_keyevent(4)).pack(side="left", padx=3)
        ttk.Button(k_sub1, text="Recent Apps (187)", command=lambda: self.send_keyevent(187)).pack(side="left", padx=3)
        ttk.Button(k_sub1, text="Power (26)", command=lambda: self.send_keyevent(26)).pack(side="left", padx=3)
        ttk.Button(k_sub1, text="Menu (82)", command=lambda: self.send_keyevent(82)).pack(side="left", padx=3)

        k_sub2 = ttk.Frame(k_frame)
        k_sub2.pack(fill="x", pady=3)
        ttk.Button(k_sub2, text="Volume Up (24)", command=lambda: self.send_keyevent(24)).pack(side="left", padx=3)
        ttk.Button(k_sub2, text="Volume Down (25)", command=lambda: self.send_keyevent(25)).pack(side="left", padx=3)
        ttk.Button(k_sub2, text="Mute (164)", command=lambda: self.send_keyevent(164)).pack(side="left", padx=3)
        ttk.Button(k_sub2, text="Play/Pause (85)", command=lambda: self.send_keyevent(85)).pack(side="left", padx=3)
        ttk.Button(k_sub2, text="Camera (27)", command=lambda: self.send_keyevent(27)).pack(side="left", padx=3)

        # Text Injection block
        t_frame = ttk.LabelFrame(scroll_area, text="Text Injection Engine", padding=10)
        t_frame.pack(fill="x", pady=6)
        ttk.Label(t_frame, text="Type arbitrary text to send to focused screen field:").pack(anchor="w", pady=2)
        
        t_sub = ttk.Frame(t_frame)
        t_sub.pack(fill="x", pady=4)
        self.inject_text_var = tk.StringVar()
        ttk.Entry(t_sub, textvariable=self.inject_text_var, width=40).pack(side="left", padx=4)
        ttk.Button(t_sub, text="Send Text Input", command=self.send_text_input).pack(side="left", padx=4)

        # Touch Tap / Swipe block
        touch_frame = ttk.LabelFrame(scroll_area, text="Touch & Gesture Automation", padding=10)
        touch_frame.pack(fill="x", pady=6)
        
        tp_sub = ttk.Frame(touch_frame)
        tp_sub.pack(fill="x", pady=3)
        ttk.Label(tp_sub, text="Tap Coordinates X:").pack(side="left")
        self.tap_x_var = tk.StringVar(value="500")
        ttk.Entry(tp_sub, textvariable=self.tap_x_var, width=8).pack(side="left", padx=4)
        ttk.Label(tp_sub, text="Y:").pack(side="left")
        self.tap_y_var = tk.StringVar(value="1000")
        ttk.Entry(tp_sub, textvariable=self.tap_y_var, width=8).pack(side="left", padx=4)
        ttk.Button(tp_sub, text="Simulate Tap", command=self.send_tap).pack(side="left", padx=8)

        sw_sub = ttk.Frame(touch_frame)
        sw_sub.pack(fill="x", pady=3)
        ttk.Label(sw_sub, text="Swipe From X1,Y1:").pack(side="left")
        self.sw_x1_var = tk.StringVar(value="500")
        ttk.Entry(sw_sub, textvariable=self.sw_x1_var, width=6).pack(side="left", padx=2)
        self.sw_y1_var = tk.StringVar(value="1500")
        ttk.Entry(sw_sub, textvariable=self.sw_y1_var, width=6).pack(side="left", padx=2)
        ttk.Label(sw_sub, text="To X2,Y2:").pack(side="left")
        self.sw_x2_var = tk.StringVar(value="500")
        ttk.Entry(sw_sub, textvariable=self.sw_x2_var, width=6).pack(side="left", padx=2)
        self.sw_y2_var = tk.StringVar(value="500")
        ttk.Entry(sw_sub, textvariable=self.sw_y2_var, width=6).pack(side="left", padx=2)
        ttk.Button(sw_sub, text="Simulate Swipe", command=self.send_swipe).pack(side="left", padx=8)

    def send_keyevent(self, code):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        def worker():
            return self.adb.shell("input", "keyevent", str(code))
        def done(res):
            self.log(f"Keyevent {code} dispatched.")
        self.run_async(worker, done)

    def send_text_input(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        text = self.inject_text_var.get()
        if not text:
            return
        # Escape spaces for adb shell input text
        escaped = text.replace(" ", "%s")
        def worker():
            return self.adb.shell("input", "text", escaped)
        def done(res):
            self.log(f"Injected text: {text}")
            self.inject_text_var.set("")
        self.run_async(worker, done)

    def send_tap(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        x, y = self.tap_x_var.get().strip(), self.tap_y_var.get().strip()
        def worker():
            return self.adb.shell("input", "tap", x, y)
        def done(res):
            self.log(f"Simulated tap at coordinates ({x}, {y})")
        self.run_async(worker, done)

    def send_swipe(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        x1, y1 = self.sw_x1_var.get().strip(), self.sw_y1_var.get().strip()
        x2, y2 = self.sw_x2_var.get().strip(), self.sw_y2_var.get().strip()
        def worker():
            return self.adb.shell("input", "swipe", x1, y1, x2, y2, "300")
        def done(res):
            self.log(f"Simulated swipe from ({x1},{y1}) to ({x2},{y2})")
        self.run_async(worker, done)

    # --- Backup & Profiles Tab ---
    def _build_backup_tab(self, parent):
        profile_frame = ttk.LabelFrame(parent, text="Debloat Profiles (JSON)", padding=10)
        profile_frame.pack(fill="x", pady=6)
        ttk.Label(profile_frame, text="Export or import custom system profile templates across flashing cycles.",
                  wraplength=700, justify="left").pack(anchor="w", pady=(0, 6))
        row = ttk.Frame(profile_frame)
        row.pack(fill="x")
        ttk.Button(row, text="Export Profile...", command=self.export_profile).pack(side="left", padx=4)
        ttk.Button(row, text="Import & Apply Profile...", command=self.import_profile).pack(side="left", padx=4)
        ttk.Button(row, text="Export Package List (CSV)...", command=self.export_csv).pack(side="left", padx=4)

        apk_frame = ttk.LabelFrame(parent, text="Batch APK Backup Engine", padding=10)
        apk_frame.pack(fill="x", pady=6)
        ttk.Label(apk_frame, text="Pull installation packages for apps selected inside the Apps/Debloat tab.",
                  wraplength=700, justify="left").pack(anchor="w", pady=(0, 6))
        ttk.Button(apk_frame, text="Backup Selected Apps' APKs...", command=self.backup_apks).pack(anchor="w")

        self.backup_progress = ttk.Progressbar(parent, mode="determinate")
        self.backup_progress.pack(fill="x", pady=(10, 2))
        self.backup_progress_label = ttk.Label(parent, text="")
        self.backup_progress_label.pack(anchor="w")

    def export_profile(self):
        if not self._all_packages:
            messagebox.showinfo("Nothing loaded", "Refresh the Apps tab first.")
            return
        dest = filedialog.asksaveasfilename(title="Save profile as", defaultextension=".json",
                                             filetypes=[("JSON", "*.json")],
                                             initialfile=f"debloat_profile_{datetime.now():%Y%m%d}.json")
        if not dest:
            return
        disabled = [p["name"] for p in self._all_packages if p["state"] == "Disabled"]
        uninstalled = [p["name"] for p in self._all_packages if p["state"] == "Uninstalled"]
        data = {
            "created": datetime.now().isoformat(),
            "device_serial": self.adb.serial,
            "disabled": disabled,
            "uninstalled_for_user": uninstalled,
        }
        with open(dest, "w") as f:
            json.dump(data, f, indent=2)
        self.log(f"Exported configuration profile containing {len(disabled)} disabled and {len(uninstalled)} uninstalled targets.")

    def import_profile(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        src = filedialog.askopenfilename(title="Open profile JSON", filetypes=[("JSON", "*.json")])
        if not src:
            return
        try:
            with open(src) as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Invalid file", f"Could not parse profile file: {e}")
            return
        disabled = data.get("disabled", [])
        uninstalled = data.get("uninstalled_for_user", [])
        total = len(disabled) + len(uninstalled)
        if not messagebox.askyesno("Confirm Import",
                                    f"Apply this profile? It will disable {len(disabled)} package(s) "
                                    f"and remove {len(uninstalled)} user package(s)."):
            return

        def worker():
            lines = []
            for pkg in disabled:
                r = self.adb.disable(pkg)
                lines.append(f"disable {pkg}: {(r.stdout + r.stderr).strip() or 'OK'}")
            for pkg in uninstalled:
                r = self.adb.uninstall_for_user(pkg)
                lines.append(f"uninstall {pkg}: {(r.stdout + r.stderr).strip() or 'OK'}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Profile import encountered error: {result}")
                return
            for line in result:
                self.log(line)
            self.log(f"Profile import sequence finished successfully ({total} actions processed).")
            self.refresh_packages()

        self.log("Executing profile import scripts...")
        self.run_async(worker, done)

    def export_csv(self):
        if not self._all_packages:
            messagebox.showinfo("Nothing loaded", "Refresh the Apps tab first.")
            return
        dest = filedialog.asksaveasfilename(title="Save package inventory CSV", defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")],
                                             initialfile=f"packages_{datetime.now():%Y%m%d}.csv")
        if not dest:
            return
        with open(dest, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "type", "state"])
            writer.writeheader()
            writer.writerows(self._all_packages)
        self.log(f"Successfully exported package inventory matrix to {dest}")

    def backup_apks(self):
        pkgs = self.selected_packages()
        if not pkgs:
            messagebox.showinfo("Nothing selected", "Select apps inside the Apps tab first.")
            return
        dest_dir = filedialog.askdirectory(title="Select backup destination folder...")
        if not dest_dir:
            return

        self.backup_progress.configure(maximum=len(pkgs), value=0)

        def worker():
            lines = []
            for i, pkg in enumerate(pkgs, 1):
                self.ui_queue.put(lambda i=i, pkg=pkg: (
                    self.backup_progress.configure(value=i),
                    self.backup_progress_label.configure(text=f"Backing up {i}/{len(pkgs)}: {pkg}"),
                ))
                try:
                    paths = self.adb.pm_path(pkg)
                    if not paths:
                        lines.append(f"{pkg}: active APK file path not resolved")
                        continue
                    pkg_dir = os.path.join(dest_dir, pkg)
                    os.makedirs(pkg_dir, exist_ok=True)
                    for j, remote in enumerate(paths):
                        local_name = "base.apk" if j == 0 else f"split_{j}.apk"
                        local = os.path.join(pkg_dir, local_name)
                        self.adb.pull(remote, local)
                    lines.append(f"{pkg}: saved {len(paths)} APK components successfully")
                except Exception as e:
                    lines.append(f"{pkg}: ERROR {e}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Batch APK backup aborted: {result}")
                return
            for line in result:
                self.log(line)
            self.backup_progress_label.configure(text=f"Completed -- archived {len(pkgs)} app directories.")
            self.log(f"APK extraction pipeline completed: {dest_dir}")

        self.run_async(worker, done)

    # --- Core Helpers & Async Execution ---
    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def run_async(self, worker, on_done=None):
        def target():
            try:
                result = worker()
            except Exception as e:
                result = e
            if on_done:
                self.ui_queue.put(lambda: on_done(result))
        threading.Thread(target=target, daemon=True).start()

    def refresh_devices(self):
        if not Adb.available():
            return
        try:
            devs = self.adb.devices()
        except Exception as e:
            self.log(f"Error enumerating devices: {e}")
            devs = []

        values = [f"{s}  ({st})" for s, st in devs]
        self.device_combo["values"] = values
        if devs:
            self.device_combo.current(0)
            serial, state = devs[0]
            self.adb.serial = serial
            if state == "device":
                self.status_label.configure(text=f"Connected: {serial}", foreground="#3a3")
                self.refresh_packages()
                self.refresh_tweak_status()
                self.refresh_device_info()
            elif state == "unauthorized":
                self.status_label.configure(text="Unauthorized -- check phone display prompt", foreground="#a33")
            else:
                self.status_label.configure(text=f"Device state: {state}", foreground="#a33")
        else:
            self.adb.serial = None
            self.status_label.configure(text="No device detected", foreground="#a33")

    def _on_device_selected(self):
        idx = self.device_combo.current()
        if idx < 0:
            return
        try:
            devs = self.adb.devices()
            serial, state = devs[idx]
            self.adb.serial = serial
            self.status_label.configure(text=f"Connected: {serial}", foreground="#3a3")
            self.refresh_packages()
            self.refresh_tweak_status()
            self.refresh_device_info()
        except Exception as e:
            self.log(f"Error handling device selection: {e}")

    def refresh_packages(self):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        self.log("Querying application inventory...")

        def worker():
            return self.adb.list_packages()

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Package scan error: {result}")
                return
            self._all_packages = result
            self._filter_tree()
            self.log(f"Loaded total inventory of {len(result)} packages.")

        self.run_async(worker, done)

    def _filter_tree(self):
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().lower().strip()
        filt = self.filter_var.get()
        for pkg in self._all_packages:
            if query and query not in pkg["name"].lower():
                continue
            if filt == "User" and pkg["type"] != "User":
                continue
            if filt == "System" and pkg["type"] != "System":
                continue
            if filt == "Enabled" and pkg["state"] != "Enabled":
                continue
            if filt == "Disabled" and pkg["state"] != "Disabled":
                continue
            if filt == "Uninstalled" and pkg["state"] != "Uninstalled":
                continue
            self.tree.insert("", "end", iid=pkg["name"], text=pkg["name"],
                              values=(pkg["type"], pkg["state"]))

    def _select_known_bloat(self):
        self.tree.selection_remove(self.tree.selection())
        matches = []
        for pkg in self._all_packages:
            name = pkg["name"].lower()
            if any(hint in name for hint in KNOWN_BLOAT_HINTS):
                if self.tree.exists(pkg["name"]):
                    matches.append(pkg["name"])
        if matches:
            self.tree.selection_set(matches)
            self.tree.see(matches[0])
        self.log(f"Selected {len(matches)} matched items based on standard telemetry/bloat profiles.")

    def selected_packages(self):
        return list(self.tree.selection())

    def _confirm(self, verb, pkgs):
        if not pkgs:
            messagebox.showinfo("Nothing selected", "Select one or more packages first.")
            return False
        return messagebox.askyesno(
            f"Confirm {verb}",
            f"{verb} {len(pkgs)} package(s)?\n\n" + "\n".join(pkgs[:15]) +
            ("\n..." if len(pkgs) > 15 else ""),
        )

    def action_disable(self):
        pkgs = self.selected_packages()
        if not self._confirm("Disable", pkgs):
            return
        self._bulk_action(pkgs, self.adb.disable, "Disabled")

    def action_enable(self):
        pkgs = self.selected_packages()
        if not self._confirm("Enable", pkgs):
            return
        self._bulk_action(pkgs, self.adb.enable, "Enabled")

    def action_uninstall(self):
        pkgs = self.selected_packages()
        if not self._confirm("Uninstall (for current user)", pkgs):
            return
        self._bulk_action(pkgs, self.adb.uninstall_for_user, "Uninstalled")

    def action_restore(self):
        pkgs = self.selected_packages()
        if not self._confirm("Restore", pkgs):
            return
        self._bulk_action(pkgs, self.adb.restore, "Restored")

    def action_force_stop(self):
        pkgs = self.selected_packages()
        if not self._confirm("Force Stop", pkgs):
            return
        self._bulk_action(pkgs, self.adb.force_stop, "Force-stopped", refresh=False)

    def action_clear_data(self):
        pkgs = self.selected_packages()
        if not self._confirm("Clear Data/Cache for", pkgs):
            return
        self._bulk_action(pkgs, self.adb.clear_data, "Cleared data for", refresh=False)

    def _show_app_info(self):
        pkgs = self.selected_packages()
        if not pkgs:
            messagebox.showinfo("Nothing selected", "Select a package first.")
            return
        pkg = pkgs[0]

        def worker():
            return self.adb.dump_package(pkg)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Failed pulling package dump: {result}")
                return
            win = tk.Toplevel(self)
            win.title(f"Detailed Info: {pkg}")
            win.geometry("780x580")
            text = tk.Text(win, wrap="none", bg="#111", fg="#ddd", insertbackground="#ddd")
            text.pack(fill="both", expand=True)
            text.insert("1.0", result[:60000])
            text.configure(state="disabled")

        self.log(f"Querying system info details for package {pkg}...")
        self.run_async(worker, done)

    def _bulk_action(self, pkgs, fn, verb, refresh=True):
        self.apps_progress.configure(maximum=len(pkgs), value=0)

        def worker():
            lines = []
            for i, pkg in enumerate(pkgs, 1):
                self.ui_queue.put(lambda i=i, pkg=pkg: (
                    self.apps_progress.configure(value=i),
                    self.apps_progress_label.configure(text=f"{verb} {i}/{len(pkgs)}: {pkg}"),
                ))
                try:
                    r = fn(pkg)
                    out = (r.stdout + r.stderr).strip()
                    lines.append(f"{pkg}: {out or 'OK'}")
                except Exception as e:
                    lines.append(f"{pkg}: ERROR {e}")
            return lines

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Action sequence {verb} failed: {result}")
                return
            for line in result:
                self.log(line)
            self.log(f"Operation completed for {len(pkgs)} packages.")
            self.apps_progress_label.configure(text=f"Batch operation completed for {len(pkgs)} packages.")
            if refresh:
                self.refresh_packages()

        self.run_async(worker, done)

    def toggle_tweak(self, tweak):
        if not self.adb.serial:
            messagebox.showwarning("No device", "Select a connected device first.")
            return
        currently_on = self.tweak_state.get(tweak["id"], False)
        cmds = tweak["revert"] if currently_on else tweak["apply"]
        action = "Reverting" if currently_on else "Applying"
        self.log(f"{action} configuration tweak: {tweak['label']}")

        def worker():
            return self.adb.run_tweak_commands(cmds)

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Tweak execution failed: {result}")
                return
            self.log(result)
            self.tweak_state[tweak["id"]] = not currently_on
            self._update_tweak_button(tweak)

        self.run_async(worker, done)

    def _update_tweak_button(self, tweak):
        on = self.tweak_state.get(tweak["id"], False)
        btn = self.tweak_buttons[tweak["id"]]
        if on:
            btn.configure(text=f"Revert: {tweak['label']}", bg="#2e7d32", fg="white")
        else:
            btn.configure(text=f"Apply: {tweak['label']}", bg="#f0f0f0", fg="black")

    def refresh_tweak_status(self):
        if not self.adb.serial:
            return

        def worker():
            states = {}
            for t in TWEAKS:
                if t["check"]:
                    try:
                        val = self.adb.get_setting(t["check"])
                        states[t["id"]] = (val.strip() == t["on_value"])
                    except Exception:
                        states[t["id"]] = self.tweak_state.get(t["id"], False)
                else:
                    states[t["id"]] = self.tweak_state.get(t["id"], False)
            return states

        def done(result):
            if isinstance(result, Exception):
                self.log(f"Could not update tweak states: {result}")
                return
            self.tweak_state.update(result)
            for t in TWEAKS:
                self._update_tweak_button(t)

        self.run_async(worker, done)


def _ask_string(parent, title, prompt):
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.grab_set()
    ttk.Label(win, text=prompt).pack(padx=12, pady=(12, 4))
    var = tk.StringVar()
    entry = ttk.Entry(win, textvariable=var, width=32)
    entry.pack(padx=12, pady=4)
    entry.focus_set()
    result = {"value": None}

    def on_ok():
        result["value"] = var.get()
        win.destroy()

    def on_cancel():
        win.destroy()

    btns = ttk.Frame(win)
    btns.pack(pady=(4, 12))
    ttk.Button(btns, text="OK", command=on_ok).pack(side="left", padx=4)
    ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="left", padx=4)
    entry.bind("<Return>", lambda e: on_ok())
    win.wait_window()
    return result["value"]


if __name__ == "__main__":
    App().mainloop()
