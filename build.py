"""Builds AlTask.exe and the installer dist/AlTask-Setup.exe (Windows).

    py build.py

Used both locally and by the GitHub Action (.github/workflows/release.yml).
"""
import os
import shutil
import subprocess
import sys

import tools

SEP = os.pathsep            # ';' on Windows, used by --add-data


def pyinstaller(*args):
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", *args])


def main():
    tools.config()                                   # bakes the update repo into the app

    print("\n== AlTask.exe ==")
    pyinstaller("--clean", "--onedir", "--noconsole", "--name", "AlTask",
                "--icon", "tasks.ico", "--version-file", "version_info.txt",
                "--add-data", f"tasks.ico{SEP}.", "Tasks.pyw")

    print("\n== payload ==")
    os.makedirs("build", exist_ok=True)
    shutil.make_archive("build/payload", "zip", "dist/AlTask")

    print("\n== AlTask-Setup.exe ==")
    excludes = ["unittest", "pydoc", "doctest", "xmlrpc", "sqlite3", "asyncio", "multiprocessing"]
    args = ["--onefile", "--noconsole", "--uac-admin", "--name", "AlTask-Setup",
            "--icon", "tasks.ico", "--version-file", "setup_version_info.txt",
            "--splash", "splash.png",
            "--add-data", f"build/payload.zip{SEP}.", "--add-data", f"assets{SEP}assets"]
    for m in excludes:
        args += ["--exclude-module", m]
    pyinstaller(*args, "Setup.pyw")
    print("\nDone: dist/AlTask-Setup.exe")


if __name__ == "__main__":
    main()
