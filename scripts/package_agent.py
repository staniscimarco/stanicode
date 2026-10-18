"""Build the standalone backend. Run on the target OS; no cross-compilation claim."""

from pathlib import Path
import os
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
    env={
        **os.environ,
        "PYINSTALLER_CONFIG_DIR": str(root / ".local" / "pyinstaller-cache"),
    },
)
# Preserve verification notices from source; no credential files are copied.
for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
    shutil.copy2(root / name, out / name)
models = root / "models"
if (models / "manifest.json").exists():
    from verify_bundle import verify

    manifest = verify(models)
    names = {"manifest.json"}
    for key in ("runtime", "model"):
        names.update([manifest[key]["file"], manifest[key]["license_file"]])
    names.update(entry["file"] for entry in manifest.get("support_files", []))
    for name in names:
        source = (models / name).resolve(strict=True)
        if not source.is_relative_to(models.resolve()):
            raise ValueError("Model payload escape")
        destination = out / "models" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

else:
    (out / "models").mkdir(exist_ok=True)
    print(
        "WARNING: model payload absent. Output is NOT a self-contained offline release."
    )
