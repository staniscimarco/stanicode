"""Stage actual dependency notices and a versioned CycloneDX inventory.

Inventories the production npm tree, target-resolved Cargo graph, Python
runtime/build closure and bundled inference/runtime components. Missing
upstream license texts fail packaging instead of producing placeholder terms.
"""

import importlib.metadata as metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from packaging.requirements import Requirement
from prepare_model import digest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / ".local/package"
LICENSES = PAYLOAD / "dependency-licenses"


def license_files(root):
    result = []
    for path in root.rglob("*"):
        if len(path.relative_to(root).parts) > 3:
            continue
        if path.is_file() and re.search(r"licen[cs]e|copying|copyright|notice|unlicense", path.name, re.I):
            if path.suffix.lower() not in {".py", ".pyc", ".rs", ".js", ".ts", ".h", ".c", ".pyd", ".dll"}:
                result.append(path)
    return result


def main():
    LICENSES.mkdir(parents=True, exist_ok=True)
    components, missing = [], []

    def component(ecosystem, name, version, license_name, files, origin=None):
        key = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{ecosystem}-{name}-{version}")
        directory = LICENSES / key
        directory.mkdir(exist_ok=True)
        records = []
        for index, path in enumerate(dict.fromkeys(files)):
            destination = directory / (str(index) + "-" + path.name)
            shutil.copy2(path, destination)
            records.append({"file": destination.relative_to(PAYLOAD).as_posix(), "sha256": digest(destination)})
        if not records:
            missing.append(key)
        info = {"type": "library", "bom-ref": key, "name": name, "version": version,
                "properties": [{"name": "stanicode:ecosystem", "value": ecosystem},
                               {"name": "stanicode:license-files", "value": json.dumps(records)}]}
        if license_name:
            info["licenses"] = [{"license": {"name": str(license_name)}}]
        if origin:
            info["externalReferences"] = [{"type": "distribution", "url": origin}]
        components.append(info)

    lock = json.loads((ROOT / "package-lock.json").read_text())
    for relative, entry in lock["packages"].items():
        if not relative or entry.get("dev"):
            continue
        directory = ROOT / relative
        package = json.loads((directory / "package.json").read_text())
        # Avoid accidentally gathering nested dependencies' unrelated notices.
        files = [p for p in license_files(directory) if "node_modules" not in p.relative_to(directory).parts]
        component("npm", package["name"], package["version"], entry.get("license", package.get("license")), files, entry.get("resolved"))

    # Include PyInstaller's explicit binary-distribution exception and its build
    # closure as well as actual HTTPX runtime dependencies. Over-inclusion is
    # identified by ecosystem rather than claiming every build tool is executed.
    pending, seen = ["httpx", "pyinstaller"], set()
    while pending:
        name = pending.pop()
        dist = metadata.distribution(name)
        canonical = dist.metadata["Name"].lower().replace("_", "-")
        if canonical in seen:
            continue
        seen.add(canonical)
        files = [Path(dist.locate_file(file)).resolve() for file in (dist.files or []) if re.search(r"license|copying|notice|copyright", str(file), re.I) and str(file).lower().endswith((".txt", ".md", ".rst", "license", "copying", "notice", "license.rtf"))]
        component("python", dist.metadata["Name"], dist.version, dist.metadata.get("License-Expression") or dist.metadata.get("License"), [p for p in files if p.is_file()])
        for requirement in dist.requires or []:
            parsed = Requirement(requirement)
            if not parsed.marker or parsed.marker.evaluate({"extra": ""}):
                pending.append(parsed.name)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    component("runtime", "CPython", sys.version.split()[0], "PSF-2.0", [python_license] if python_license.is_file() else [])
    rust_root = Path(subprocess.check_output(["rustc", "--print", "sysroot"], text=True).strip())
    rust_version = subprocess.check_output(["rustc", "--version"], text=True).split()[1]
    component("runtime", "Rust-standard-library", rust_version, "MIT OR Apache-2.0", license_files(rust_root / "share/doc/rust/licenses"))
    cargo = json.loads(subprocess.check_output(["cargo", "metadata", "--locked", "--format-version", "1", "--filter-platform", "x86_64-pc-windows-msvc", "--manifest-path", str(ROOT / "apps/desktop/src-tauri/Cargo.toml")], text=True, encoding="utf-8"))
    nodes = {node["id"]: node for node in cargo["resolve"]["nodes"]}
    reachable, pending = set(), [cargo["resolve"]["root"]]
    while pending:
        identifier = pending.pop()
        if identifier in reachable:
            continue
        reachable.add(identifier)
        pending.extend(dep["pkg"] for dep in nodes[identifier]["deps"] if any(kind["kind"] != "dev" for kind in dep["dep_kinds"]))
    for package in cargo["packages"]:
        if package["id"] not in reachable or not package["source"]:
            continue
        directory = Path(package["manifest_path"]).parent
        files = license_files(directory)
        if package.get("license_file"):
            files.append(directory / package["license_file"])
        component("cargo", package["name"], package["version"], package["license"], files, f"https://crates.io/crates/{package['name']}/{package['version']}")
    manifest = json.loads((PAYLOAD / "models/manifest.json").read_text())
    for kind in ("runtime", "model"):
        entry = manifest[kind]
        component(kind, entry["file"], entry["version"], entry["license"], [PAYLOAD / "models" / entry["license_file"]], entry["source"])
    llvm = PAYLOAD / "models/LICENSE-LLVM-OpenMP"
    component("runtime", "LLVM-OpenMP", manifest["runtime"]["version"], "Apache-2.0 WITH LLVM-exception", [llvm] if llvm.exists() else [])
    for name, source, version in (
        ("Microsoft-WebView2-Runtime", PAYLOAD / "WebView2-runtime-terms.txt", "155.0.4283.62"),
        ("Microsoft-Visual-C-Runtime", PAYLOAD / "Visual-C-runtime-terms.txt", "app-local-release-CRT"),
    ):
        component("runtime", name, version, "Microsoft redistribution terms", [source] if source.exists() else [])
    credits = [PAYLOAD / "webview2/THIRD-PARTY-CREDITS.txt"] if (PAYLOAD / "webview2/THIRD-PARTY-CREDITS.txt").is_file() else []
    component("runtime", "WebView2-third-party-notices", "155.0.4283.62", "See upstream notices", credits)
    report = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": "urn:uuid:" + str(uuid.uuid4()), "version": 1,
              "metadata": {"component": {"type": "application", "name": "STANICODE", "version": "0.1.0-candidate"}},
              "components": components}
    (PAYLOAD / "SBOM.cdx.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    evidence = ROOT / ".local/evidence/license-inventory.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({"components": len(components), "missing_license_texts": missing}, indent=2))
    if missing:
        raise RuntimeError("Upstream license texts missing: " + ", ".join(missing))
    print(f"Collected actual upstream license texts for {len(components)} versioned components.")


if __name__ == "__main__":
    main()
