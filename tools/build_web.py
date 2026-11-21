"""
Builds the web (browser) version of the game with pygbag.

    python tools/build_web.py           build, then serve it at http://localhost:8000 to test
    python tools/build_web.py --zip     build build_web/ExperimentalWizard/build/web.zip for itch.io
    python tools/build_web.py --build   only build build_web/ExperimentalWizard/build/web (used by GitHub Pages)

Only what the browser needs is copied into build_web/ (the game, sounds, and a few music styles),
so the download stays small. Needs:  pip install pygbag
"""
import os
import shutil
import subprocess
import sys

GAMEFILES = ["music.py", "audio.py", "display.py", "panel.py", "welcome.py"]
WEBSTYLES = ["arcane", "alchemy"]  # music styles to include on the web (each is ~4 MB)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STAGE = os.path.join(ROOT, "build_web", "ExperimentalWizard")


def main():
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(os.path.join(STAGE, "music"))
    shutil.copy(os.path.join(ROOT, "example.py"), os.path.join(STAGE, "main.py"))  # pygbag starts main.py
    for part in GAMEFILES:  # the game's other source files sit next to main.py
        shutil.copy(os.path.join(ROOT, part), os.path.join(STAGE, part))
    shutil.copytree(os.path.join(ROOT, "sounds"), os.path.join(STAGE, "sounds"))
    for style in WEBSTYLES:
        shutil.copytree(os.path.join(ROOT, "music", style), os.path.join(STAGE, "music", style))
    args = [sys.executable, "-m", "pygbag", "--title", "Experimental Wizard", "--width", "1030", "--height", "630"]
    if "--zip" in sys.argv:
        args += ["--archive"]
    elif "--build" in sys.argv:
        args += ["--build"]
    args.append(STAGE)
    print("running:", " ".join(args))
    subprocess.run(args, check=True)


if __name__ == "__main__":
    main()
