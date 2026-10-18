"""Fail closed on absent/modified runtime or model, and incomplete license metadata."""

import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    for key in ("runtime", "model"):
        entry = manifest[key]
        for field in ("file", "sha256", "license", "source", "version"):
            if not entry.get(field):
                raise ValueError(f"{key}: missing {field}")
        p = (root / entry["file"]).resolve(strict=True)
        if not p.is_relative_to(root):
            raise ValueError("Bundle escape")
        with p.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"{key}: checksum mismatch")
        license_path = (root / entry["license_file"]).resolve(strict=True)
        if not license_path.is_relative_to(root) or not license_path.is_file():
            raise ValueError("License file missing")
        print(f"{key}: {p.name}, {p.stat().st_size} bytes, SHA256 {digest}")
    if not list(root.rglob("*.dll")) and __import__("sys").platform == "win32":
        print(
            "Check whether the chosen Windows inference build requires companion DLLs."
        )
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("bundle")
    verify(p.parse_args().bundle)
