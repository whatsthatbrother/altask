# -*- coding: utf-8 -*-
"""
AlTask Setup 5.0 — custom installer / uninstaller / updater.
Designed & built by Diar F.

Installs AlTask into  C:\\Program Files\\AlTask, adds Desktop + Start menu shortcuts,
registers in  Settings > Apps  (with an uninstaller), optional start with Windows.

The same exe is copied into the install folder as "Uninstall AlTask.exe";
started from there (or with --uninstall) it runs as the uninstaller.
Started by the app with --update it updates in place and restarts AlTask.
An older "Tasks" install (4.x) is moved over to AlTask automatically.
"""
import ctypes
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import zipfile
import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont

APP = "AlTask"
VERSION = "5.0"
AUTHOR = "Diar F."
EXE = "AlTask.exe"
UNINST_EXE = "Uninstall AlTask.exe"
IS_WIN = sys.platform == "win32"
TEST_DIR = os.environ.get("TASKS_SETUP_TEST")          # dev only: fake install target

UNINST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AlTask"
OLD_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Tasks"      # 4.x, before the rename
OLD_APP, OLD_EXE = "Tasks", "Tasks.exe"
OLD_INNO_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{8E5B3C2A-6F1D-4B7A-9C3E-2D4F5A6B7C8D}_is1"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Detyrat"
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DetyratNote")
NO_WINDOW = 0x08000000

# palette — Albanian red on near-black
RED, RED_HOVER, RED_DARK = "#E41E20", "#C9161A", "#8E0F14"
BG, SURFACE, SURFACE_2 = "#0E0E10", "#18181B", "#222226"
LINE, TEXT, MUTED, FAINT = "#2C2C31", "#F4F4F5", "#A9A9B2", "#73737C"
GREEN = "#22C55E"


def res(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def has_font(root, family):
    try:
        return tkfont.Font(root=root, family=family, size=10).actual("family").lower() == family.lower()
    except Exception:
        return False


# ───────────────────────── Windows helpers ─────────────────────────
def reg_hklm(path, write=False):
    import winreg
    access = (winreg.KEY_ALL_ACCESS if write else winreg.KEY_READ) | winreg.KEY_WOW64_64KEY
    if write:
        return winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, access)
    return winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, access)


def reg_read(path, name):
    if not IS_WIN:
        return None
    import winreg
    try:
        with reg_hklm(path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def shell_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf)
    return buf.value


def common_desktop():
    return shell_folder(0x19)          # CSIDL_COMMON_DESKTOPDIRECTORY


def common_programs():
    return shell_folder(0x17)          # CSIDL_COMMON_PROGRAMS


def desktop_shortcut_exists():
    try:
        return any(os.path.exists(os.path.join(common_desktop(), n + ".lnk")) for n in (APP, OLD_APP))
    except Exception:
        return True


def startup_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def close_splash():
    """Close the PyInstaller splash (shown instantly while the setup unpacks)."""
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass


def default_dir():
    if TEST_DIR:
        return os.path.join(TEST_DIR, APP)
    prev = reg_read(UNINST_KEY, "InstallLocation")
    if prev:
        return prev
    old = reg_read(OLD_KEY, "InstallLocation")          # upgrading from "Tasks" 4.x
    if old:
        parent = os.path.dirname(os.path.normpath(old))
        return os.path.join(parent, APP)
    pf = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or r"C:\Program Files"
    return os.path.join(pf, APP)


def run_hidden(args, **kw):
    return subprocess.run(args, creationflags=NO_WINDOW, capture_output=True, **kw)


def kill_app():
    if IS_WIN and not TEST_DIR:
        for name in (EXE, OLD_EXE):
            run_hidden(["taskkill", "/f", "/im", name])
        time.sleep(0.4)


def remove_old_tasks():
    """Move a 4.x install that was still called "Tasks" over to AlTask:
    remove its files, shortcuts and Settings > Apps entry. The user's tasks are kept."""
    old = reg_read(OLD_KEY, "InstallLocation")
    if not old:
        return
    for folder in (common_desktop(), common_programs()):
        try:
            os.remove(os.path.join(folder, OLD_APP + ".lnk"))
        except OSError:
            pass
    if os.path.isfile(os.path.join(old, OLD_EXE)):        # only ever delete a real Tasks folder
        shutil.rmtree(old, ignore_errors=True)
    import winreg
    try:
        winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, OLD_KEY, winreg.KEY_WOW64_64KEY, 0)
    except OSError:
        pass


def remove_old_inno():
    """Silently remove a 3.0 / 4.0 install made with the old Inno Setup installer."""
    s = reg_read(OLD_INNO_KEY, "UninstallString")
    if not s:
        return
    exe = s.strip().strip('"')
    if os.path.exists(exe):
        run_hidden([exe, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        for _ in range(60):                 # its uninstaller finishes from a temp copy
            if not os.path.exists(exe):
                break
            time.sleep(0.25)


def make_shortcuts(items):
    """items: list of (lnk_path, target, description)."""
    q = lambda p: "'" + p.replace("'", "''") + "'"
    lines = ["$w = New-Object -ComObject WScript.Shell"]
    for lnk, target, desc in items:
        lines += [f"$s = $w.CreateShortcut({q(lnk)})",
                  f"$s.TargetPath = {q(target)}",
                  f"$s.WorkingDirectory = {q(os.path.dirname(target))}",
                  f"$s.IconLocation = {q(target + ',0')}",
                  f"$s.Description = {q(desc)}",
                  "$s.Save()"]
    run_hidden(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "; ".join(lines)])


def refresh_icon_cache():
    """Windows caches icons per file path — make it drop the old (purple) icon."""
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)   # SHCNE_ASSOCCHANGED
    except Exception:
        pass
    try:
        run_hidden(["ie4uinit.exe", "-show"], timeout=15)
    except Exception:
        pass


def set_startup(on, exe_path=None):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def register_uninstaller(dest, size_kb):
    import winreg
    vals = {
        "DisplayName": APP, "DisplayVersion": VERSION, "Publisher": AUTHOR,
        "DisplayIcon": os.path.join(dest, EXE), "InstallLocation": dest,
        "UninstallString": f'"{os.path.join(dest, UNINST_EXE)}"',
        "QuietUninstallString": f'"{os.path.join(dest, UNINST_EXE)}" --quiet',
        "Comments": f"A clean task panel for Windows — by {AUTHOR}",
    }
    with reg_hklm(UNINST_KEY, write=True) as k:
        for n, v in vals.items():
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def unregister_uninstaller():
    import winreg
    try:
        winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, UNINST_KEY, winreg.KEY_WOW64_64KEY, 0)
    except OSError:
        pass


def launch_unelevated(path):
    """Start the app as the normal (non-admin) user, not as this elevated installer."""
    try:
        subprocess.Popen(["explorer.exe", path], creationflags=NO_WINDOW)
    except Exception:
        try:
            os.startfile(path)
        except Exception:
            pass


# ───────────────────────── install / uninstall work ─────────────────────────
def do_install(dest, desktop, startup, report):
    report(0.02, "Preparing…")
    kill_app()
    if IS_WIN and not TEST_DIR:
        report(0.05, "Removing the previous version…")
        remove_old_inno()
        remove_old_tasks()
    os.makedirs(dest, exist_ok=True)
    old_internal = os.path.join(dest, "_internal")
    if os.path.isdir(old_internal):
        shutil.rmtree(old_internal, ignore_errors=True)

    with zipfile.ZipFile(res("payload.zip")) as zf:
        items = zf.infolist()
        total = sum(i.file_size for i in items) or 1
        done = 0
        for i in items:
            zf.extract(i, dest)
            done += i.file_size
            report(0.08 + 0.77 * done / total, "Copying  " + i.filename.split("/")[-1])
        size_kb = total // 1024

    exe_path = os.path.join(dest, EXE)
    if getattr(sys, "frozen", False):
        report(0.87, "Adding the uninstaller…")
        shutil.copy2(sys.executable, os.path.join(dest, UNINST_EXE))

    if IS_WIN and not TEST_DIR:
        report(0.90, "Creating shortcuts…")
        sc = [(os.path.join(common_programs(), APP + ".lnk"), exe_path, f"AlTask — by {AUTHOR}")]
        if desktop:
            sc.append((os.path.join(common_desktop(), APP + ".lnk"), exe_path, f"AlTask — by {AUTHOR}"))
        make_shortcuts(sc)
        report(0.96, "Registering…")
        register_uninstaller(dest, size_kb)
        set_startup(startup, exe_path)
        refresh_icon_cache()
    for p in (0.97, 0.99, 1.0):
        report(p, "Finishing…")
        time.sleep(0.12)


def do_uninstall(dest, remove_data, report):
    report(0.05, "Closing AlTask…")
    kill_app()
    if IS_WIN and not TEST_DIR:
        report(0.2, "Removing shortcuts…")
        for folder in (common_desktop(), common_programs()):
            try:
                os.remove(os.path.join(folder, APP + ".lnk"))
            except OSError:
                pass
        set_startup(False)
        unregister_uninstaller()
    report(0.4, "Removing files…")
    me = os.path.abspath(sys.executable).lower()
    entries = os.listdir(dest) if os.path.isdir(dest) else []
    for n, name in enumerate(entries, 1):
        p = os.path.join(dest, name)
        if os.path.abspath(p).lower() == me:
            continue
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
        report(0.4 + 0.5 * n / max(1, len(entries)), "Removing  " + name)
    if remove_data:
        report(0.93, "Deleting your tasks…")
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    report(1.0, "Done")


def schedule_self_delete(folder):
    """The running uninstaller can't delete itself — let cmd do it a moment after we exit."""
    if not IS_WIN or TEST_DIR:
        return
    cmd = f'ping 127.0.0.1 -n 4 > nul & rmdir /s /q "{folder}"'
    subprocess.Popen(["cmd", "/c", cmd], creationflags=NO_WINDOW | 0x00000008,   # DETACHED_PROCESS
                     cwd=os.environ.get("TEMP", "C:\\"), close_fds=True)


# ───────────────────────── UI widgets ─────────────────────────
def round_rect(c, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Button(tk.Canvas):
    def __init__(self, parent, ui, text, command, kind="primary", width=None):
        self.ui, self.command, self.kind = ui, command, kind
        f = ui.f_btn
        w = width or (f.measure(text) + ui.px(44))
        h = ui.px(40)
        super().__init__(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.w, self.h, self.text, self.enabled = w, h, text, True
        self.bind("<Enter>", lambda e: self.draw(True))
        self.bind("<Leave>", lambda e: self.draw(False))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())
        self.draw(False)

    def set_enabled(self, on):
        self.enabled = on
        self.config(cursor="hand2" if on else "arrow")
        self.draw(False)

    def draw(self, hover):
        self.delete("all")
        ui = self.ui
        if self.kind == "primary":
            fill = RED_HOVER if hover and self.enabled else RED
            if not self.enabled:
                fill = RED_DARK
            fg, outline = "#ffffff", fill
        else:
            fill = SURFACE_2 if hover and self.enabled else self["bg"]
            fg, outline = (TEXT if self.enabled else FAINT), LINE
        round_rect(self, 1, 1, self.w - 1, self.h - 1, ui.px(9), fill=fill, outline=outline)
        self.create_text(self.w / 2, self.h / 2, text=self.text, font=ui.f_btn, fill=fg)


class Check(tk.Frame):
    def __init__(self, parent, ui, text, value=True, sub=None):
        super().__init__(parent, bg=parent["bg"], cursor="hand2")
        self.ui, self.value = ui, value
        s = ui.px(22)
        self.c = tk.Canvas(self, width=s, height=s, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.c.pack(side="left", anchor="n", pady=(ui.px(1), 0))
        col = tk.Frame(self, bg=parent["bg"])
        col.pack(side="left", padx=(ui.px(12), 0))
        lbl = tk.Label(col, text=text, font=ui.f_body, bg=parent["bg"], fg=TEXT, anchor="w")
        lbl.pack(fill="x")
        widgets = [self, self.c, col, lbl]
        if sub:
            sl = tk.Label(col, text=sub, font=ui.f_small, bg=parent["bg"], fg=FAINT, anchor="w")
            sl.pack(fill="x")
            widgets.append(sl)
        for w in widgets:
            w.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, _=None):
        self.value = not self.value
        self.draw()

    def draw(self):
        c, ui = self.c, self.ui
        c.delete("all")
        s = ui.px(22)
        if self.value:
            round_rect(c, 1, 1, s - 1, s - 1, ui.px(6), fill=RED, outline=RED)
            c.create_line(ui.px(6), ui.px(11.5), ui.px(9.5), ui.px(15), ui.px(16), ui.px(7.5),
                          fill="#ffffff", width=max(2, ui.px(2.2)), capstyle="round", joinstyle="round")
        else:
            round_rect(c, 1, 1, s - 1, s - 1, ui.px(6), fill=SURFACE, outline="#4a4a52",
                       width=max(1, ui.px(1.4)))


class Progress(tk.Canvas):
    def __init__(self, parent, ui):
        super().__init__(parent, height=ui.px(8), bg=parent["bg"], highlightthickness=0)
        self.ui, self.v = ui, 0.0
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, v):
        self.v = max(0.0, min(1.0, v))
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.ui.px(8)
        round_rect(self, 0, 0, w, h, h / 2, fill=SURFACE_2, outline=SURFACE_2)
        if self.v > 0:
            round_rect(self, 0, 0, max(h, w * self.v), h, h / 2, fill=RED, outline=RED)


# ───────────────────────── the window ─────────────────────────
class SetupUI:
    W, H = 820, 520

    def __init__(self, uninstall=False, quiet=False, update=False):
        if IS_WIN:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
        self.uninstall = uninstall
        self.update = update
        self.root = tk.Tk()
        self.root.withdraw()
        self.s = self.root.winfo_fpixels("1i") / 96.0
        self.q = queue.Queue()
        self.busy = False
        self.dest = os.path.dirname(os.path.abspath(sys.executable)) if (uninstall and getattr(sys, "frozen", False)) \
            else default_dir()
        if quiet:
            close_splash()
            self.root.after(10, self.quiet_run)
            return
        self._fonts()
        self._images()
        self._window()
        if uninstall:
            self.page_uninstall()
        elif update:
            self.root.after(150, self.start_update)
            self.page_progress(f"Updating {APP.upper()} to {VERSION}…", "Your tasks stay exactly where they are.")
        else:
            self.page_welcome()

    def px(self, n):
        return int(round(n * self.s))

    def _fonts(self):
        base = "Segoe UI" if has_font(self.root, "Segoe UI") else tkfont.nametofont("TkDefaultFont").actual("family")
        semi = "Segoe UI Semibold" if has_font(self.root, "Segoe UI Semibold") else None
        strong = (lambda sz: tkfont.Font(family=semi, size=sz)) if semi else \
            (lambda sz: tkfont.Font(family=base, size=sz, weight="bold"))
        self.f_h1 = strong(21)
        self.f_title = strong(12)
        self.f_btn = strong(10)
        self.f_label = strong(9)
        self.f_body = tkfont.Font(family=base, size=10)
        self.f_small = tkfont.Font(family=base, size=9)

    def _images(self):
        scales = [100, 125, 150, 175, 200]
        k = min(scales, key=lambda v: abs(v - self.s * 100))
        self.hero = tk.PhotoImage(file=res("assets", f"hero-{k}.png"))
        ew = min((40, 50, 60, 70, 80), key=lambda v: abs(v - 40 * self.s))
        self.eagle = tk.PhotoImage(file=res("assets", f"eagle-red-{ew}.png"))
        ew2 = min((40, 50, 60, 70, 80), key=lambda v: abs(v - 64 * self.s))
        self.eagle_big = tk.PhotoImage(file=res("assets", f"eagle-red-{ew2}.png"))
        try:
            self.icon = tk.PhotoImage(file=res("assets", "icon-64.png"))
            self.root.iconphoto(True, self.icon)
        except Exception:
            pass

    def _window(self):
        r = self.root
        r.title(f"{APP} Setup" if not self.uninstall else f"Uninstall {APP}")
        r.overrideredirect(True)
        r.configure(bg=LINE)
        w, h = self.hero.width() + self.px(520), self.hero.height()
        x = (r.winfo_screenwidth() - w) // 2
        y = (r.winfo_screenheight() - h) // 2
        r.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(r, bg=BG)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        hero = tk.Label(frame, image=self.hero, bd=0, bg=BG)
        hero.pack(side="left", fill="y")
        self.right = tk.Frame(frame, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)

        top = tk.Frame(self.right, bg=BG)
        top.pack(fill="x")
        self.close_btn = tk.Label(top, text="✕", font=self.f_title, bg=BG, fg=MUTED,
                                  padx=self.px(16), pady=self.px(8), cursor="hand2")
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(bg=RED, fg="#fff"))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(bg=BG, fg=MUTED))
        self.close_btn.bind("<Button-1>", lambda e: self.cancel())

        self.body = tk.Frame(self.right, bg=BG)
        self.body.pack(fill="both", expand=True, padx=(self.px(44), self.px(44)), pady=(0, self.px(30)))

        for w in (hero, top, self.right):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
        r.bind("<Escape>", lambda e: self.cancel())
        close_splash()
        r.deiconify()
        if IS_WIN:
            r.after(10, self._taskbar_fix)
        r.after(50, r.focus_force)

    def _taskbar_fix(self):
        try:
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.root.winfo_id())
            st = u.GetWindowLongW(hwnd, -20)
            u.SetWindowLongW(hwnd, -20, (st & ~0x80) | 0x40000)
            self.root.withdraw()
            self.root.deiconify()
        except Exception:
            pass

    def _drag_start(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def cancel(self):
        if not self.busy:
            self.root.destroy()

    # ---------- page helpers ----------
    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def heading(self, eyebrow, title, text=None):
        b = self.body
        row = tk.Frame(b, bg=BG)
        row.pack(fill="x", pady=(self.px(6), 0))
        tk.Label(row, image=self.eagle, bg=BG).pack(side="left")
        tk.Label(row, text=eyebrow.upper(), font=self.f_label, bg=BG, fg=RED).pack(
            side="left", padx=(self.px(12), 0))
        tk.Label(b, text=title, font=self.f_h1, bg=BG, fg=TEXT, anchor="w", justify="left").pack(
            fill="x", pady=(self.px(18), self.px(8)))
        if text:
            tk.Label(b, text=text, font=self.f_body, bg=BG, fg=MUTED, anchor="w", justify="left",
                     wraplength=self.px(430)).pack(fill="x")

    def footer(self, buttons, note=None):
        bar = tk.Frame(self.body, bg=BG)
        bar.pack(side="bottom", fill="x")
        if note:
            tk.Label(bar, text=note, font=self.f_small, bg=BG, fg=FAINT).pack(side="left")
        out = []
        for b in reversed(buttons):
            btn = Button(bar, self, *b)
            btn.pack(side="right", padx=(self.px(10), 0))
            out.append(btn)
        return out[::-1]

    # ---------- pages: install ----------
    def page_welcome(self):
        self.clear()
        self.heading(f"{APP} {VERSION} setup", f"Install {APP.upper()} on this PC",
                     "A clean, always-there task panel on the right side of your screen. "
                     "Write down what needs to be done — tick it off when it's done.")

        tk.Label(self.body, text="INSTALL LOCATION", font=self.f_label, bg=BG, fg=FAINT, anchor="w").pack(
            fill="x", pady=(self.px(26), self.px(8)))
        box = tk.Frame(self.body, bg=SURFACE, highlightthickness=1, highlightbackground=LINE,
                       highlightcolor=RED)
        box.pack(fill="x")
        self.path = tk.Entry(box, font=self.f_body, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, highlightthickness=0)
        self.path.insert(0, self.dest)
        self.path.pack(side="left", fill="x", expand=True, padx=(self.px(12), self.px(6)), ipady=self.px(9))
        br = tk.Label(box, text="Browse", font=self.f_label, bg=SURFACE_2, fg=TEXT, cursor="hand2",
                      padx=self.px(14), pady=self.px(6))
        br.pack(side="right", padx=self.px(5))
        br.bind("<Button-1>", lambda e: self.browse())
        br.bind("<Enter>", lambda e: br.config(bg=LINE))
        br.bind("<Leave>", lambda e: br.config(bg=SURFACE_2))

        opts = tk.Frame(self.body, bg=BG)
        opts.pack(fill="x", pady=(self.px(22), 0))
        self.c_desktop = Check(opts, self, "Create a desktop shortcut", True)
        self.c_desktop.pack(fill="x", pady=(0, self.px(12)))
        self.c_startup = Check(opts, self, "Start AlTask when Windows starts", False,
                               sub="Opens the panel automatically after you sign in")
        self.c_startup.pack(fill="x")

        self.footer([("Cancel", self.cancel, "ghost"), ("Install", self.start_install, "primary",
                                                       self.px(130))],
                    note=f"Made by {AUTHOR}")
        self.root.bind("<Return>", lambda e: self.start_install())

    def browse(self):
        d = filedialog.askdirectory(parent=self.root, initialdir=os.path.dirname(self.path.get()) or "C:\\",
                                    title="Choose where to install AlTask")
        if d:
            d = os.path.normpath(d)
            if os.path.basename(d).lower() != APP.lower():
                d = os.path.join(d, APP)
            self.path.delete(0, "end")
            self.path.insert(0, d)

    def start_install(self):
        if self.busy:
            return
        self.dest = os.path.normpath(self.path.get().strip() or default_dir())
        desktop, startup = self.c_desktop.value, self.c_startup.value
        self.root.unbind("<Return>")
        self.page_progress(f"Installing {APP.upper()}…", "This only takes a few seconds.")
        self.run_job(lambda rep: do_install(self.dest, desktop, startup, rep), self.page_done)

    # ---------- update (started by the app) ----------
    def start_update(self):
        desktop = desktop_shortcut_exists() if IS_WIN and not TEST_DIR else True
        startup = startup_enabled() if IS_WIN and not TEST_DIR else False
        self.run_job(lambda rep: do_install(self.dest, desktop, startup, rep), self.page_updated)

    def page_updated(self):
        self.clear()
        self.success_mark(self.body).pack(anchor="w", pady=(self.px(10), 0))
        tk.Label(self.body, text=f"Updated to {VERSION}", font=self.f_h1, bg=BG, fg=TEXT, anchor="w").pack(
            fill="x", pady=(self.px(20), self.px(8)))
        tk.Label(self.body, text=f"Opening {APP}…", font=self.f_body, bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        tk.Label(self.body, text=f"— {AUTHOR}", font=self.f_title, bg=BG, fg=TEXT).pack(side="bottom", anchor="w")
        if not TEST_DIR:
            launch_unelevated(os.path.join(self.dest, EXE))
        self.root.after(1600, self.root.destroy)

    # ---------- pages: progress / done ----------
    def page_progress(self, title, text):
        self.clear()
        self.busy = True
        self.close_btn.config(fg=SURFACE_2)
        self.heading("Please wait", title, text)
        self.pct = tk.Label(self.body, text="0%", font=self.f_h1, bg=BG, fg=TEXT, anchor="w")
        self.pct.pack(fill="x", pady=(self.px(40), self.px(10)))
        self.bar = Progress(self.body, self)
        self.bar.pack(fill="x")
        self.status = tk.Label(self.body, text="", font=self.f_small, bg=BG, fg=FAINT, anchor="w")
        self.status.pack(fill="x", pady=(self.px(10), 0))
        tk.Label(self.body, text=f"{APP} {VERSION}  ·  by {AUTHOR}", font=self.f_small, bg=BG,
                 fg=FAINT).pack(side="bottom", anchor="w")

    def run_job(self, job, on_done):
        def worker():
            try:
                job(lambda v, msg: self.q.put(("p", v, msg)))
                self.q.put(("ok", None, None))
            except Exception as ex:
                self.q.put(("err", None, str(ex)))
        threading.Thread(target=worker, daemon=True).start()
        self._shown = 0.0
        self._target = 0.0
        self._finish = None
        self._poll(on_done)

    def _poll(self, on_done):
        try:
            while True:
                kind, v, msg = self.q.get_nowait()
                if kind == "p":
                    self._target = v
                    self.status.config(text=msg)
                elif kind == "ok":
                    self._finish = ("ok", None)
                else:
                    self._finish = ("err", msg)
        except queue.Empty:
            pass
        # smooth animation toward the real progress
        self._shown += (self._target - self._shown) * 0.25 + 0.002
        self._shown = min(self._shown, self._target)
        self.bar.set(self._shown)
        self.pct.config(text=f"{int(self._shown * 100)}%")
        if self._finish and (self._finish[0] == "err" or self._shown >= 0.995):
            self.busy = False
            self.close_btn.config(fg=MUTED)
            if self._finish[0] == "ok":
                self.root.after(250, on_done)
            else:
                self.page_error(self._finish[1])
            return
        self.root.after(16, lambda: self._poll(on_done))

    def success_mark(self, parent):
        c = tk.Canvas(parent, width=self.px(64), height=self.px(64), bg=BG, highlightthickness=0)
        c.create_oval(2, 2, self.px(62), self.px(62), fill=RED, outline=RED)
        c.create_line(self.px(19), self.px(33), self.px(28), self.px(42), self.px(45), self.px(23),
                      fill="#ffffff", width=self.px(5), capstyle="round", joinstyle="round")
        return c

    def page_done(self):
        self.clear()
        self.success_mark(self.body).pack(anchor="w", pady=(self.px(10), 0))
        tk.Label(self.body, text=f"{APP.upper()} is ready", font=self.f_h1, bg=BG, fg=TEXT, anchor="w").pack(
            fill="x", pady=(self.px(20), self.px(8)))
        tk.Label(self.body, text="You'll find it on your Desktop and in the Start menu.\n"
                                 "Your tasks are kept safe across updates.",
                 font=self.f_body, bg=BG, fg=MUTED, anchor="w", justify="left").pack(fill="x")
        self.c_launch = Check(self.body, self, f"Open {APP} now", True)
        self.c_launch.pack(fill="x", pady=(self.px(28), 0))

        sig = tk.Frame(self.body, bg=BG)
        sig.pack(side="bottom", fill="x")
        Button(sig, self, "Finish", self.finish, "primary", self.px(130)).pack(side="right")
        left = tk.Frame(sig, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="Thanks for installing!", font=self.f_small, bg=BG, fg=FAINT, anchor="w").pack(fill="x")
        tk.Label(left, text=f"— {AUTHOR}", font=self.f_title, bg=BG, fg=TEXT, anchor="w").pack(fill="x")
        self.root.bind("<Return>", lambda e: self.finish())

    def finish(self):
        if getattr(self, "c_launch", None) and self.c_launch.value and not TEST_DIR:
            launch_unelevated(os.path.join(self.dest, EXE))
        self.root.destroy()

    def page_error(self, msg):
        self.clear()
        self.heading("Something went wrong", "Setup could not finish",
                     f"{msg}\n\nClose any open AlTask window and run Setup again. "
                     "If it keeps failing, right-click Setup and choose “Run as administrator”.")
        self.footer([("Close", self.root.destroy, "primary", self.px(120))])

    # ---------- pages: uninstall ----------
    def page_uninstall(self):
        self.clear()
        self.heading(f"{APP} {VERSION}", f"Uninstall {APP.upper()}?",
                     f"This removes {APP} from this PC, including its shortcuts.")
        box = tk.Frame(self.body, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="x", pady=(self.px(26), 0))
        tk.Label(box, text=self.dest, font=self.f_small, bg=SURFACE, fg=MUTED, anchor="w").pack(
            fill="x", padx=self.px(14), pady=self.px(12))
        self.c_data = Check(self.body, self, "Also delete my tasks", False,
                            sub="Leave this off to keep your list for a future install")
        self.c_data.pack(fill="x", pady=(self.px(22), 0))
        self.footer([("Cancel", self.cancel, "ghost"), ("Uninstall", self.start_uninstall, "primary",
                                                        self.px(140))],
                    note=f"Made by {AUTHOR}")

    def start_uninstall(self):
        remove_data = self.c_data.value
        self.page_progress(f"Removing {APP}…", "Just a moment.")
        self.run_job(lambda rep: do_uninstall(self.dest, remove_data, rep), self.page_removed)

    def page_removed(self):
        self.clear()
        self.success_mark(self.body).pack(anchor="w", pady=(self.px(10), 0))
        tk.Label(self.body, text=f"{APP.upper()} was removed", font=self.f_h1, bg=BG, fg=TEXT, anchor="w").pack(
            fill="x", pady=(self.px(20), self.px(8)))
        tk.Label(self.body, text="Thanks for using it.", font=self.f_body, bg=BG, fg=MUTED,
                 anchor="w").pack(fill="x")
        sig = tk.Frame(self.body, bg=BG)
        sig.pack(side="bottom", fill="x")
        Button(sig, self, "Close", self.close_removed, "primary", self.px(120)).pack(side="right")
        tk.Label(sig, text=f"— {AUTHOR}", font=self.f_title, bg=BG, fg=TEXT).pack(side="left")

    def close_removed(self):
        schedule_self_delete(self.dest)
        self.root.destroy()

    # ---------- silent mode (Settings > Apps "quiet" uninstall) ----------
    def quiet_run(self):
        try:
            if self.uninstall:
                do_uninstall(self.dest, False, lambda *a: None)
                schedule_self_delete(self.dest)
            else:
                do_install(self.dest, True, False, lambda *a: None)
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]
    exe_name = os.path.basename(sys.executable).lower() if getattr(sys, "frozen", False) else ""
    uninstall = "--uninstall" in args or exe_name.startswith("uninstall")
    SetupUI(uninstall=uninstall, quiet="--quiet" in args, update="--update" in args).run()
