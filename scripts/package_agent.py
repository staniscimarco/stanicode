"""Build the standalone backend. Run on the target OS; no cross-compilation claim."""

from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root / ".local" / "package"
out.mkdir(parents=True, exist_ok=True)
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "stanicode-agent",
        "--paths",
        str(root / "services" / "agent"),
        "--distpath",
        str(out),
        "--workpath",
        str(root / ".local" / "pyinstaller"),
        "--specpath",
        str(root / ".local"),
        str(root / "services" / "agent" / "server.py"),
    ],
    check=True,
)
models = root / "models"
if (models / "manifest.json").exists():
    shutil.copytree(
        models,
        out / "models",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("README.md"),
    )
else:
    (out / "models").mkdir(exist_ok=True)
    print(
        "WARNING: model payload absent. Output is NOT a self-contained offline release."
    )
