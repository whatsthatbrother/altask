"""Build helpers for AlTask (used by build.bat and publish.bat).

  py tools.py config     -> writes update_config.py from repo.txt (baked into AlTask.exe)
  py tools.py manifest   -> writes dist/latest.json (version, download url, sha256, notes)
  py tools.py version    -> prints the version from Tasks.pyw
"""
import hashlib, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent


def version():
    m = re.search(r'^VERSION = "([^"]+)"', (ROOT / "Tasks.pyw").read_text(encoding="utf-8"), re.M)
    return m.group(1)


def repo():
    r = (ROOT / "repo.txt").read_text(encoding="utf-8").strip() if (ROOT / "repo.txt").exists() else ""
    return "" if (not r or "YOUR-GITHUB" in r.upper() or "/" not in r) else r


def config():
    r = repo()
    (ROOT / "update_config.py").write_text(f'UPDATE_REPO = "{r}"\n', encoding="utf-8")
    print(f"Update repo: {r}" if r else "WARNING: repo.txt not set - this build will not check for updates.")


def manifest():
    r, v = repo(), version()
    if not r:
        sys.exit("Set your GitHub repo in repo.txt first (e.g. diarf/tasks).")
    exe = ROOT / "dist" / "AlTask-Setup.exe"
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    notes = (ROOT / "notes.txt").read_text(encoding="utf-8").strip() if (ROOT / "notes.txt").exists() else ""
    data = {"version": v, "sha256": sha, "notes": notes,
            "url": f"https://github.com/{r}/releases/download/v{v}/AlTask-Setup.exe"}
    (ROOT / "dist" / "latest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"latest.json -> v{v}  sha256 {sha[:16]}...")


if __name__ == "__main__":
    {"config": config, "manifest": manifest, "version": lambda: print(version())}[sys.argv[1]]()
