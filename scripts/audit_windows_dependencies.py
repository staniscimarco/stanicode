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
            if binary.FILE_HEADER.Machine != 0x8664:
                raise ValueError("Non-x64 PE in portable payload: " + path.name)
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
                elif (system / name).is_file():
                    resolved.append({"name": name, "kind": "Windows-System32"})
                else:
                    missing.append(str(path) + " -> " + name)
            records.append({"file": "STANICODE.exe" if path == executable else "payload/" + path.relative_to(payload).as_posix(),
                            "imports": resolved, "delay_imports": [entry.dll.decode("ascii") for entry in getattr(binary, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]})
    report = {"kind": "actual-x64-PE-import-audit", "files": records, "missing": missing, "clean_windows_vm": False}
    output = Path(".local/evidence/windows-dependencies.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if missing:
        raise RuntimeError("Missing portable DLLs: " + "; ".join(missing))
    print(f"Verified actual PE imports for {len(files)} x64 images; installed developer CRTs do not satisfy the audit.")


if __name__ == "__main__":
    main()
