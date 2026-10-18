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
CAB_HASH = "cf54aa717a0ebd05b40e87620724583cb6eb0a5b8b64764cc11e42822f68bf6c"


def acquire_webview_terms(payload):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page()
            page.goto("https://developer.microsoft.com/en-us/microsoft-edge/webview2/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            page.get_by_role("button", name="Download", exact=True).last.click(force=True)
            page.wait_for_timeout(3000)
            candidates = []
            for frame in page.frames:
                text = frame.locator("body").inner_text(timeout=10000)
                if re.search(r"MICROSOFT SOFTWARE LICENSE TERMS", text, re.I):
                    candidates.append({"url": frame.url, "text": text})
            (payload / "webview-eula-page.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
            for candidate in candidates:
                print("::notice title=Microsoft download license dialog::" + json.dumps(candidate)[-13000:].replace("%", "%25"))
            return candidates
        finally:
            browser.close()


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
    cab = download(SOURCE, ".local/downloads/webview2-x64.cab", CAB_HASH)
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
    inspection["license_display_command"] = (destination / "show_third_party_software_licenses.bat").read_text(errors="replace")
    try:
        candidates = acquire_webview_terms(payload)
        inspection["webview_eula_candidates"] = [{"url": c["url"], "text_length": len(c["text"])} for c in candidates]
        # Runtime-specific heading and redistribution clause are both required.
        for candidate in candidates:
            text = candidate["text"]
            start = re.search(r"MICROSOFT SOFTWARE LICENSE TERMS", text, re.I).start()
            text = text[start:]
            if re.search(r"MICROSOFT EDGE WEBVIEW2 RUNTIME", text, re.I) and re.search(r"distribut", text, re.I):
                (payload / "WebView2-runtime-terms.txt").write_text(text, encoding="utf-8")
    except Exception as error:
        inspection["eula_dialog_error"] = str(error)
    for label, url in {
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
    for key, value in inspection.items():
        note = json.dumps(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::notice title=Microsoft runtime " + key + "::" + note)
    # No distributable manifest is created until the actual runtime licensing
    # terms have been identified. An SDK license is not a substitute.


if __name__ == "__main__":
    main()
