"""Inspect actual PE imports against the planned portable layout and Windows OS.

This catches missing app-local DLLs; it does not replace a clean Windows VM.
Delay imports are inventoried separately because many WebView media features
are optional and are not exercised by the local coding UI.
"""

import argparse
import json
import os
from pathlib import Path
import pefile
from prepare_model import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--payload", default=".local/package")
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("Resolve system dependencies on the target Windows build machine")
    executable = Path(args.executable).resolve(strict=True)
    payload = Path(args.payload).resolve(strict=True)
    system = Path(os.environ["SystemRoot"]) / "System32"
    crt = {p.name.lower(): p for p in (payload / "models").glob("*.dll") if p.name.lower().startswith(("vcruntime", "msvcp", "concrt"))}
    files = [executable] + [p for p in payload.rglob("*") if p.is_file() and p.suffix.lower() in {".exe", ".dll", ".pyd"}]
    missing, records = [], []
    for path in files:
        with pefile.PE(str(path), fast_load=True) as binary:
            binary.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"], pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
            # Microsoft's pinned x64 CAB also contains this x86 host loader.
            # Preserve the complete vendor distribution and audit its actual
            # OS imports against WOW64; it is not loaded by our x64 host.
            auxiliary = (path == payload / "webview2/EBWebView/x86/EmbeddedBrowserWebView.dll"
                         and binary.FILE_HEADER.Machine == 0x14C
                         and digest(path) == "1aae79b774920d3662d0b7827caa1e76e6016fdd99f0570225806fc1ee6007a0")
            if binary.FILE_HEADER.Machine != 0x8664 and not auxiliary:
                raise ValueError("Unexpected PE architecture in portable payload: " + str(path))
            image_system = system.parent / "SysWOW64" if auxiliary else system
            search = [path.parent]
            if path == executable:
                search.append(payload / "models")  # These CRTs are also copied beside STANICODE.exe.
            elif path.is_relative_to(payload / "webview2"):
                search.append(payload / "webview2")
            elif path.is_relative_to(payload / "_internal"):
                search.append(payload / "_internal")
            else:
                search.append(payload)
            resolved = []
            for entry in getattr(binary, "DIRECTORY_ENTRY_IMPORT", []):
                name = entry.dll.decode("ascii").lower()
                local = next((directory / name for directory in search if (directory / name).is_file()), None)
                is_crt = name.startswith(("vcruntime", "msvcp140", "concrt"))
                if local:
                    resolved.append({"name": name, "kind": "bundled", "sha256": digest(local)})
                    if path == executable and is_crt and name not in crt:
                        missing.append(str(path) + " -> " + name)
                elif is_crt:
                    # Never accept an installed Visual Studio CRT as OS evidence.
                    missing.append(str(path) + " -> " + name)
                elif name.startswith(("api-ms-win-", "ext-ms-win-")):
                    resolved.append({"name": name, "kind": "Windows-api-set"})
                elif (image_system / name).is_file():
                    resolved.append({"name": name, "kind": "Windows-" + image_system.name})
                else:
                    missing.append(str(path) + " -> " + name)
            records.append({"file": "STANICODE.exe" if path == executable else "payload/" + path.relative_to(payload).as_posix(),
                            "machine": hex(binary.FILE_HEADER.Machine),
                            "role": "verified-vendor-x86-host-loader" if auxiliary else "x64-runtime",
                            "imports": resolved, "delay_imports": [entry.dll.decode("ascii") for entry in getattr(binary, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]})
    report = {"kind": "actual-x64-PE-import-audit", "files": records, "missing": missing, "clean_windows_vm": False}
    output = Path(".local/evidence/windows-dependencies.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if missing:
        raise RuntimeError("Missing portable DLLs: " + "; ".join(missing))
    print(f"Verified actual PE imports for {len(files)} images, including the hash-pinned vendor x86 host loader; installed developer CRTs do not satisfy the audit.")


if __name__ == "__main__":
    main()
