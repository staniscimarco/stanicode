"""Shared offline-payload integrity contract for startup and distribution."""

import hashlib
import json
from pathlib import Path


def verified_file(root, entry):
    path = (root / entry["file"]).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Bundle path escapes its directory")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(entry["file"] + " checksum mismatch")
    return path


def verify(root):
    root = Path(root).resolve(strict=True)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    covered = set()
    for key in ("runtime", "model"):
        entry = manifest[key]
        verified_file(root, entry)
        for field in ("license", "source", "version", "license_file"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(key + " license/source/version metadata missing")
        license_file = (root / entry["license_file"]).resolve(strict=True)
        if not license_file.is_relative_to(root) or not license_file.is_file():
            raise ValueError("License file is outside bundle")
        covered.add(Path(entry["file"]).as_posix())
    minimum = manifest["model"].get("minimum_available_ram_bytes")
    if type(minimum) is not int or minimum <= 0:
        raise ValueError("Model RAM requirement is missing")
    for entry in manifest.get("support_files", []):
        verified_file(root, entry)
        covered.add(Path(entry["file"]).as_posix())
    for file in root.rglob("*"):
        if (
            file.is_file()
            and file.suffix.lower() in {".dll", ".exe", ".so", ".dylib"}
            and file.relative_to(root).as_posix() not in covered
        ):
            raise ValueError("Unverified runtime companion: " + file.name)
    return manifest
