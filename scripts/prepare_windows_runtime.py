"""Acquire Microsoft's complete fixed WebView2, verify publisher and inventory it."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
from prepare_model import download, digest, verify_microsoft

VERSION = "155.0.4283.62"
SOURCE = "https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/232cf50b-3980-4531-afbb-779f446d7de1/Microsoft.WebView2.FixedVersionRuntime.155.0.4283.62.x64.cab"


def main():
    if os.name != "nt":
        raise RuntimeError("Fixed Windows runtime preparation requires Windows")
    payload = Path(".local/package")
    payload.mkdir(parents=True, exist_ok=True)
    destination = payload / "webview2"
    with urllib.request.urlopen("https://developer.microsoft.com/en-us/microsoft-edge/webview2/", timeout=45) as response:
        official = response.read().decode().replace("\\u002F", "/")
    if SOURCE not in official:
        raise ValueError("Pinned fixed runtime is no longer listed on the official Microsoft page")
    cab = download(SOURCE, ".local/downloads/webview2-x64.cab")
    with tempfile.TemporaryDirectory(prefix="stanicode-webview-") as directory:
        subprocess.run(["expand.exe", "-F:*", str(cab.resolve()), directory], check=True, stdout=subprocess.DEVNULL)
        executables = list(Path(directory).rglob("msedgewebview2.exe"))
        if len(executables) != 1:
            raise ValueError("Unexpected fixed runtime layout")
        verify_microsoft(executables[0])
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(executables[0].parent, destination)
    # Preserve upstream runtime notices and obtain the runtime's actual EULA,
    # not the differently licensed WebView2 SDK's LICENSE.txt.
    inspection = {"version": VERSION, "source": SOURCE, "cab_sha256": digest(cab),
                  "upstream_notice_files": [p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file() and re.search(r"license|eula|credit|terms", p.name, re.I)]}
    for label, url in {
        "WebView2-runtime-terms": "https://aka.ms/webview2license",
        "Visual-C-runtime-terms": "https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/",
    }.items():
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                text = response.read().decode("utf-8", errors="replace")
                inspection[label] = {"url": response.url, "length": len(text), "excerpt": re.sub(r"<[^>]+>", " ", text)[:1800]}
                (payload / (label + ".html")).write_text(text, encoding="utf-8")
        except Exception as error:
            inspection[label] = {"error": str(error)}
    redist = Path(os.environ["VCToolsRedistDir"])
    inspection["crt_license_candidates"] = [str(p) for p in redist.parent.rglob("*") if p.is_file() and re.search(r"license|eula", p.name, re.I)][:25]
    evidence = Path(".local/evidence/runtime-acquisition.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(inspection, indent=2), encoding="utf-8")
    note = json.dumps(inspection).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::notice title=Actual Microsoft runtime acquisition::" + note)
    # No distributable manifest is created until the actual runtime licensing
    # terms have been identified. An SDK license is not a substitute.


if __name__ == "__main__":
    main()
