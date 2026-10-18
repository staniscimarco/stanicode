"""Assemble a ZIP64 Windows candidate only from verified real release payloads."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile
from verify_bundle import verify


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def windows_x64(path):
    with Path(path).open("rb") as binary:
        if binary.read(2) != b"MZ":
            raise ValueError(f"Not a Windows executable: {Path(path).name}")
        binary.seek(0x3C)
        offset = struct.unpack("<I", binary.read(4))[0]
        binary.seek(offset)
        if binary.read(4) != b"PE\0\0" or binary.read(2) != b"\x64\x86":
            raise ValueError("Windows x64 PE image required")


def verify_webview(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "webview2-manifest.json").read_text())
    for key in ("version", "source", "license_file", "files"):
        if not manifest.get(key):
            raise ValueError("Fixed WebView2 metadata missing: " + key)
    names = set()
    for name, digest in manifest["files"].items():
        p = (root / name).resolve(strict=True)
        if not p.is_relative_to(root) or sha256(p) != digest:
            raise ValueError("WebView2 checksum mismatch: " + name)
        names.add(p.relative_to(root).as_posix())
    expected = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != "webview2-manifest.json"
    }
    if names != expected:
        raise ValueError(
            "Every fixed WebView2 file, including its license, must be hashed"
        )
    if manifest["license_file"] not in names:
        raise ValueError("WebView2 license must be included")
    windows_x64(root / "msedgewebview2.exe")
    return manifest


def build(executable, payload, output):
    executable = Path(executable).resolve(strict=True)
    payload = Path(payload).resolve(strict=True)
    output = Path(output)
    windows_x64(executable)
    windows_x64(payload / "stanicode-agent.exe")
    manifest = verify(payload / "models")
    windows_x64(payload / "models" / manifest["runtime"]["file"])
    with (payload / "models" / manifest["model"]["file"]).open("rb") as model:
        if model.read(4) != b"GGUF":
            raise ValueError("The model payload must be an actual GGUF file")
    verify_webview(payload / "webview2")
    for name in (
        "THIRD_PARTY_NOTICES.md",
        "LICENSE",
        "SBOM.cdx.json",
        "dependency-licenses",
    ):
        if not (payload / name).exists():
            raise ValueError("Distribution notices missing: " + name)
    if (
        json.loads((payload / "SBOM.cdx.json").read_text()).get("bomFormat")
        != "CycloneDX"
    ):
        raise ValueError("CycloneDX SBOM required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stanicode-portable-") as directory:
        folder = Path(directory) / "STANICODE"
        folder.mkdir()
        shutil.copy2(executable, folder / "STANICODE.exe")
        shutil.copytree(payload, folder / "payload")
        (folder / "LEGGIMI.txt").write_text(
            "STANICODE — candidato di sviluppo, non release collaudata.\nEstrai tutta questa cartella e apri STANICODE.exe.\nScegli un progetto, descrivi la richiesta e controlla le modifiche proposte prima di approvarle.\nI test eseguono codice con i tuoi permessi.\nQuesta build non e firmata: Windows puo mostrare SmartScreen.\n",
            encoding="utf-8",
        )
        checksums = []
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                checksums.append(
                    sha256(path) + "  " + path.relative_to(folder).as_posix()
                )
        (folder / "SHA256SUMS.txt").write_text(
            "\n".join(checksums) + "\n", encoding="utf-8"
        )
        pending = output.with_suffix(output.suffix + ".tmp")
        try:
            # ZIP64 supports multi-GB GGUF payloads. No manual chunk assembly.
            with zipfile.ZipFile(
                pending,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=1,
                allowZip64=True,
            ) as archive:
                for path in sorted(folder.rglob("*")):
                    if path.is_file():
                        archive.write(
                            path, path.relative_to(Path(directory)).as_posix()
                        )
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Archive integrity check failed")
            pending.replace(output)
        finally:
            pending.unlink(missing_ok=True)
    output.with_suffix(output.suffix + ".sha256").write_text(
        sha256(output) + "  " + output.name + "\n"
    )
    print("Verified payload assembled as an UNACCEPTED Windows candidate:", output.name)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--payload", default=".local/package")
    parser.add_argument(
        "--output",
        default=".local/artifacts/STANICODE-Windows-x64-Portable-candidate.zip",
    )
    args = parser.parse_args()
    build(args.executable, args.payload, args.output)
