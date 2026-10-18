"""Assemble a ZIP64 Windows candidate only from verified real release payloads."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
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
        if p.is_file() and p != root / "webview2-manifest.json"
    }
    if names != expected:
        raise ValueError(
            "Every fixed WebView2 file, including its license, must be hashed"
        )
    if manifest["license_file"] not in names:
        raise ValueError("WebView2 license must be included")
    windows_x64(root / "msedgewebview2.exe")
    return manifest


def verify_notices(payload):
    sbom = json.loads((payload / "SBOM.cdx.json").read_text(encoding="utf-8"))
    if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
        raise ValueError("A populated CycloneDX dependency inventory is required")
    seen = set()
    for component in sbom["components"]:
        reference = component.get("bom-ref")
        if not reference or reference in seen or not component.get("name") or not component.get("version"):
            raise ValueError("Invalid or duplicated dependency identity")
        seen.add(reference)
        records = next((json.loads(p["value"]) for p in component.get("properties", []) if p.get("name") == "stanicode:license-files"), [])
        if not records:
            raise ValueError("Dependency has no actual license text: " + reference)
        for entry in records:
            path = (payload / entry["file"]).resolve(strict=True)
            if not path.is_relative_to(payload / "dependency-licenses") or sha256(path) != entry["sha256"]:
                raise ValueError("Dependency license integrity mismatch: " + reference)


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
    verify_notices(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stream original payload files directly into ZIP64. Copying a 4.7 GB
    # model into another staging tree can exhaust the Windows build disk.
    # The native Rust executable also needs app-local CRT DLLs beside it;
    # placing them only beside llama-server would rely on the owner's system.
    crt = [p for p in (payload / "models").glob("*.dll") if p.name.lower().startswith(("vcruntime", "msvcp", "concrt"))]
    entries = [(executable, "STANICODE.exe")] + [(p, p.name) for p in crt] + [
        (path, "payload/" + path.relative_to(payload).as_posix())
        for path in sorted(payload.rglob("*")) if path.is_file()
    ]
    checksums = [sha256(path) + "  " + name for path, name in entries]
    readme = (
        "STANICODE — candidato di sviluppo, non release collaudata.\n"
        "Estrai tutta questa cartella e apri STANICODE.exe.\n"
        "Scegli un progetto, descrivi la richiesta e controlla le modifiche proposte prima di approvarle.\n"
        "I test eseguono codice con i tuoi permessi.\n"
        "Questa build non e firmata: Windows puo mostrare SmartScreen.\n"
    ).encode("utf-8")
    checksums.append(hashlib.sha256(readme).hexdigest() + "  LEGGIMI.txt")
    pending = output.with_suffix(output.suffix + ".tmp")
    try:
        with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1, allowZip64=True) as archive:
            for path, name in entries:
                # Quantized weights scarcely compress; storing them saves CPU.
                kind = zipfile.ZIP_STORED if path.suffix == ".gguf" else zipfile.ZIP_DEFLATED
                archive.write(path, "STANICODE/" + name, compress_type=kind)
            archive.writestr("STANICODE/LEGGIMI.txt", readme)
            archive.writestr("STANICODE/SHA256SUMS.txt", "\n".join(checksums) + "\n")
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
