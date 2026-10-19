<p align="center"><img src="assets/icon-64.png" width="64" alt=""></p>

<h1 align="center">Tasks</h1>
<p align="center">A clean, always-there task panel docked to the right side of your Windows screen.<br>
<b>Designed &amp; built by Diar F.</b></p>

<p align="center">
  <a href="https://github.com/whatsthatbrother/tasks/releases/latest/download/Tasks-Setup.exe"><b>⬇ Download Tasks for Windows</b></a>
</p>

## Features
- Docked to the right edge of the screen, collapsible, resizable
- To do / Completed lists, edit with a double-click, undo with Ctrl+Z
- Asks before deleting
- Light and dark theme (or follow Windows), three text sizes
- Always on top, start with Windows
- Updates itself: when a new version is out, Tasks shows **Update available** and installs it with one click

Works on Windows 10 and 11. Your tasks are stored in `%APPDATA%\DetyratNote\tasks.json` and are kept across updates.

## Releasing a new version
1. Change `VERSION` in `Tasks.pyw` **and** `Setup.pyw` (e.g. `4.3`) and the numbers in `version_info.txt` / `setup_version_info.txt`
2. Write what's new in `notes.txt`
3. Commit, then tag and push: `git tag v4.3 && git push origin main v4.3`

GitHub Actions builds `Tasks-Setup.exe` on Windows and publishes the release. Every installed copy of Tasks sees it within a few hours.

## Building locally
`build.bat` (needs Python 3.10+ for Windows). Output: `dist\Tasks-Setup.exe`.
