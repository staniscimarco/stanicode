"""Acquire pinned upstream CPU inference payloads on the target build machine."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

REVISION = "13fb94bfda8c8cf22497dc57b78f391a9acb426a"
MODEL = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
MODEL_URL = f"https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/{REVISION}/{MODEL}"
MODEL_HASH = "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
LLAMA_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip"
LLAMA_HASH = "37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, destination, expected=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and expected and digest(destination) == expected:
        return destination
    pending = destination.with_suffix(destination.suffix + ".download")
    try:
        with urllib.request.urlopen(url, timeout=120) as source, pending.open("wb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
        if expected and digest(pending) != expected:
            raise ValueError("Upstream checksum mismatch: " + destination.name)
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    return destination


def verify_microsoft(path):
    # Paths are passed as arguments, never interpolated into PowerShell source.
    script = "& { param($file) $s=Get-AuthenticodeSignature -LiteralPath $file; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw ('Invalid Microsoft signature: '+$file) } }"
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script, str(Path(path).resolve())], check=True)


def prepare(destination, cache):
    if os.name != "nt":
        raise RuntimeError("Windows payload preparation must run on Windows")
    destination, cache = Path(destination), Path(cache)
    destination.mkdir(parents=True, exist_ok=True)
    archive = download(LLAMA_URL, cache / "llama-win.zip", LLAMA_HASH)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = Path(member.filename).name
            if member.filename != name:
                raise ValueError("Unexpected path in pinned llama.cpp archive")
            if name == "llama-server.exe" or name.lower().endswith(".dll") or name.startswith("LICENSE"):
                (destination / name).write_bytes(bundle.read(member))
    download(MODEL_URL, destination / MODEL, MODEL_HASH)
    download(
        f"https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/raw/{REVISION}/LICENSE",
        destination / "Qwen-LICENSE.txt",
        "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
    )
    download(
        "https://raw.githubusercontent.com/ggml-org/llama.cpp/b11669/LICENSE",
        destination / "llama-LICENSE.txt",
        "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d",
    )
    # App-local release CRT from Visual Studio's designated redistributable directory.
    redist = Path(os.environ["VCToolsRedistDir"])
    candidates = list((redist / "x64").glob("Microsoft.VC*.CRT"))
    if len(candidates) != 1:
        raise RuntimeError("Cannot uniquely locate the licensed x64 release CRT")
    for source in candidates[0].glob("*.dll"):
        verify_microsoft(source)
        shutil.copy2(source, destination / source.name)
    manifest = {
        "runtime": {
            "file": "llama-server.exe", "sha256": digest(destination / "llama-server.exe"),
            "version": "b11669", "source": LLAMA_URL, "license": "MIT",
            "license_file": "llama-LICENSE.txt", "archive_sha256": LLAMA_HASH,
        },
        "model": {
            "file": MODEL, "sha256": MODEL_HASH, "version": REVISION,
            "source": MODEL_URL, "license": "Apache-2.0", "license_file": "Qwen-LICENSE.txt",
            "minimum_available_ram_bytes": 7 * 1024**3,
        },
        "support_files": [
            {"file": p.name, "sha256": digest(p)}
            for p in sorted(destination.iterdir())
            if p.is_file() and p.name not in {MODEL, "llama-server.exe", "manifest.json"}
        ],
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    from verify_bundle import verify
    verify(destination)
    print("Pinned Qwen 7B Q4_K_M and Windows CPU llama.cpp verified; app-local CRT included.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", default="models")
    parser.add_argument("--cache", default=".local/downloads")
    args = parser.parse_args()
    prepare(args.destination, args.cache)
