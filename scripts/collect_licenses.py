"""Stage actual dependency notices and a versioned CycloneDX inventory.

Inventories the production npm tree, target-resolved Cargo graph, Python
runtime/build closure and bundled inference/runtime components. Missing
upstream license texts fail packaging instead of producing placeholder terms.
"""

import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
import tomllib
import urllib.request
import urllib.parse
from packaging.requirements import Requirement
from prepare_model import digest, download

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / ".local/package"
LICENSES = PAYLOAD / "dependency-licenses"


def license_files(root):
    result = []
    for path in root.rglob("*"):
        if len(path.relative_to(root).parts) > 3:
            continue
        if path.is_file() and (root.name.lower() == "licenses" or re.search(r"licen[cs]e|copying|copyright|notice|unlicense", path.name, re.I)):
            if path.suffix.lower() not in {".py", ".pyc", ".rs", ".js", ".ts", ".h", ".c", ".pyd", ".dll"}:
                result.append(path)
    return result


def upstream_crate_licenses(package, directory):
    """Recover omitted notices from the crate's recorded immutable VCS commit."""
    vcs = directory / ".cargo_vcs_info.json"
    repository = package.get("repository") or ""
    match = re.fullmatch(r"https://github.com/([^/]+/[^/]+?)(?:\.git)?/?", repository)
    if not vcs.is_file() or not match:
        return []
    info = json.loads(vcs.read_text(encoding="utf-8"))
    commit = info["git"]["sha1"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Invalid source commit for omitted crate license")
    repo = match[1]
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "STANICODE-license-build"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1", headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        tree = json.load(response)
    ancestors = {"", *[p.as_posix().strip(".") for p in [Path(info.get("path_in_vcs", "")), *Path(info.get("path_in_vcs", "")).parents]]}
    paths = []
    for item in tree["tree"]:
        relative = Path(item["path"])
        if item["type"] == "blob" and relative.parent.as_posix().strip(".") in ancestors and re.search(r"license|copying|notice|copyright", relative.name, re.I):
            source = ROOT / ".local/downloads/licenses" / commit / relative
            url = f"https://raw.githubusercontent.com/{repo}/{commit}/" + urllib.parse.quote(item["path"])
            download(url, source)
            paths.append(source)
    return paths


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
    rust_licenses = license_files(rust_root / "share/doc/rust/licenses")
    rust_licenses += list((rust_root / "share/doc/rust").glob("COPYRIGHT*.html"))
    if not rust_licenses:
        details = subprocess.check_output(["rustc", "-vV"], text=True, encoding="utf-8")
        commit = re.search(r"^commit-hash: ([a-f0-9]{40})$", details, re.M).group(1)
        for name in ("LICENSE-MIT", "LICENSE-APACHE", "COPYRIGHT"):
            rust_licenses.append(download(f"https://raw.githubusercontent.com/rust-lang/rust/{commit}/{name}", ROOT / ".local/downloads/licenses/rust" / commit / name))
    component("runtime", "Rust-standard-library", rust_version, "MIT OR Apache-2.0", rust_licenses)
    cargo = json.loads(subprocess.check_output(["cargo", "metadata", "--locked", "--format-version", "1", "--filter-platform", "x86_64-pc-windows-msvc", "--manifest-path", str(ROOT / "apps/desktop/src-tauri/Cargo.toml")], text=True, encoding="utf-8"))
    nodes = {node["id"]: node for node in cargo["resolve"]["nodes"]}
    reachable, pending = set(), [cargo["resolve"]["root"]]
    while pending:
        identifier = pending.pop()
        if identifier in reachable:
            continue
        reachable.add(identifier)
        pending.extend(dep["pkg"] for dep in nodes[identifier]["deps"] if any(kind["kind"] != "dev" for kind in dep["dep_kinds"]))
    lock_entries = tomllib.loads((ROOT / "apps/desktop/src-tauri/Cargo.lock").read_text(encoding="utf-8"))["package"]
    checksums = {(p["name"], p["version"], p.get("source")): p.get("checksum") for p in lock_entries}
    for package in cargo["packages"]:
        if package["id"] not in reachable or not package["source"]:
            continue
        directory = Path(package["manifest_path"]).parent
        files = license_files(directory)
        if package.get("license_file"):
            files.append(directory / package["license_file"])
        if not files:
            files = upstream_crate_licenses(package, directory)
        if not files and package["license"] == "MPL-2.0":
            # MPL is a standard unmodified license, with individual copyright
            # notices in the original covered source included below.
            files = [download("https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/MPL-2.0.txt", ROOT / ".local/downloads/licenses/MPL-2.0.txt", "66a3107d5ad6a058aab753eaac2047ccb2ed0e39465dd0fe5844da3e300d5172")]
        # Preserve the original covered source, including MPL components,
        # instead of offering just a license and an eventually stale web URL.
        archive = directory.parent.parent.parent / "cache" / directory.parent.name / f"{package['name']}-{package['version']}.crate"
        if archive.is_file() and files:
            expected = checksums[(package["name"], package["version"], package["source"])]
            if digest(archive) != expected:
                raise ValueError("Original crate checksum mismatch")
            files.append(archive)
        component("cargo", package["name"], package["version"], package["license"], files, f"https://crates.io/crates/{package['name']}/{package['version']}")
    manifest = json.loads((PAYLOAD / "models/manifest.json").read_text())
    for kind in ("runtime", "model"):
        entry = manifest[kind]
        component(kind, entry["file"], entry["version"], entry["license"], [PAYLOAD / "models" / entry["license_file"]], entry["source"])
    source_entry = manifest["runtime"]["source_archive"]
    source_archive = PAYLOAD / "models" / source_entry["file"]
    if digest(source_archive) != source_entry["sha256"]:
        raise ValueError("Pinned llama.cpp source archive checksum mismatch")
    upstream_notices = []
    with zipfile.ZipFile(source_archive) as archive:
        for member in archive.infolist():
            relative = Path(*Path(member.filename).parts[1:])
            if member.is_dir() or not relative.parts or ".." in relative.parts:
                continue
            named_license = bool(re.search(r"license|copying|notice", relative.name, re.I))
            vendor_header = relative.parts[0] == "vendor" and relative.suffix in {".h", ".hpp"}
            if not (named_license or vendor_header):
                continue
            destination = ROOT / ".local/downloads/llama-notices" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(member))
            upstream_notices.append(destination)
    component("runtime", "llama.cpp-upstream-and-vendored-sources", manifest["runtime"]["version"], "See individual upstream source notices", upstream_notices + [source_archive], source_entry["url"])
    llvm = PAYLOAD / "models/LICENSE-LLVM-OpenMP"
    component("runtime", "LLVM-OpenMP", manifest["runtime"]["version"], "Apache-2.0 WITH LLVM-exception", [llvm] if llvm.exists() else [])
    for name, source, version in (
        ("Microsoft-WebView2-Runtime", PAYLOAD / "WebView2-runtime-terms.txt", "155.0.4283.62"),
        ("Microsoft-Visual-C-Runtime", PAYLOAD / "Visual-C-runtime-terms.txt", manifest["crt"]["version"]),
    ):
        if name == "Microsoft-Visual-C-Runtime" and not source.exists():
            source = next(iter(sorted(PAYLOAD.glob("Visual-C-runtime-terms*.rtf"))), next(iter(PAYLOAD.glob("Visual-C-runtime-terms.pdf")), source))
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
