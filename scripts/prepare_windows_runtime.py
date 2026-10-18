"""Acquire Microsoft's complete fixed WebView2, verify publisher and inventory it."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.parse
import html
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


def acquire_credits(destination):
    """Read credits from the exact fixed binary, never another browser version."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str((destination / "msedgewebview2.exe").resolve()), headless=True,
                                            args=["--embedded-browser-webview=show-credits"])
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("edge://credits", wait_until="domcontentloaded", timeout=30000)
            # Chromium keeps many complete license bodies in collapsed nodes.
            text = page.locator("body").text_content()
            if len(text) < 10000 or "licen" not in text.lower():
                raise ValueError("Exact runtime did not expose complete upstream credits")
            (destination / "THIRD-PARTY-CREDITS.txt").write_text(text, encoding="utf-8")
            (destination / "THIRD-PARTY-CREDITS.html").write_text(page.content(), encoding="utf-8")
        finally:
            browser.close()


def acquire_crt_terms(payload):
    """Extract the actual EULA from Microsoft's signature-verified redist."""
    archive = download("https://aka.ms/vs/17/release/vc_redist.x64.exe", ".local/downloads/vc_redist.x64.exe")
    verify_microsoft(archive)
    with tempfile.TemporaryDirectory(prefix="stanicode-crt-license-") as directory:
        wix = Path(os.environ.get("WIX", "C:/Program Files (x86)/WiX Toolset v3.14")) / "bin/dark.exe"
        dark = shutil.which("dark.exe") or (str(wix) if wix.is_file() else None)
        if dark:
            subprocess.run([dark, "-nologo", "-x", directory, str(archive.resolve()), "-o", str(Path(directory) / "bundle.wxs")], check=True, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(["7z", "x", "-y", "-o" + directory, str(archive.resolve())], check=True, stdout=subprocess.DEVNULL)
        candidates = []
        for path in Path(directory).rglob("*"):
            if not path.is_file() or path.stat().st_size > 2 * 1024**2:
                continue
            data = path.read_bytes()
            if data.startswith(b"{\\rtf") and b"MICROSOFT" in data.upper() and b"LICENSE" in data.upper():
                candidates.append((path, data))
        if not candidates:
            raise RuntimeError("Signed VC redist did not yield an actual license RTF; extracted files: " + ", ".join(p.name for p in Path(directory).rglob("*") if p.is_file())[:2000])
        for index, (_, data) in enumerate(candidates):
            (payload / f"Visual-C-runtime-terms-{index}.rtf").write_bytes(data)
        return {"source": "https://aka.ms/vs/17/release/vc_redist.x64.exe", "signed_installer_sha256": digest(archive), "license_documents": len(candidates)}


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
    try:
        acquire_credits(destination)
        inspection["credits_extracted"] = True
    except Exception as error:
        inspection["credits_extraction_error"] = str(error)[-2000:]
    for label, url in {
        "Visual-C-runtime-terms": "https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/",
    }.items():
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                text = response.read().decode("utf-8", errors="replace")
                inspection[label] = {"url": response.url, "length": len(text), "excerpt": re.sub(r"<[^>]+>", " ", text)[:1800]}
                (payload / (label + ".html")).write_text(text, encoding="utf-8")
                visible = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", text, flags=re.I | re.S)
                visible = html.unescape(re.sub(r"<[^>]+>", "\n", visible))
                visible = re.sub(r"\n\s*\n+", "\n", visible)
                heading = re.search(r"MICROSOFT\s+SOFTWARE\s+LICENSE\s+TERMS", visible, re.I)
                if heading:
                    terms = visible[heading.start():]
                    (payload / (label + ".txt")).write_text(terms, encoding="utf-8")
                    inspection[label]["actual_terms_excerpt"] = terms[:2400]
                else:
                    links = re.findall(r'(?:href|src|data)\s*=\s*["\x27]([^"\x27]+\.(?:rtf|pdf|txt)(?:[?#][^"\x27]*)?)["\x27]', text, re.I)
                    inspection[label]["license_download_links"] = links
                    inspection[label]["visible_page_excerpt"] = visible[-7000:]
                    for link in links:
                        resolved = urllib.parse.urljoin(response.url, html.unescape(link))
                        if urllib.parse.urlsplit(resolved).hostname != "visualstudio.microsoft.com":
                            continue
                        suffix = Path(urllib.parse.urlsplit(resolved).path).suffix.lower()
                        if suffix in {".rtf", ".pdf"}:
                            license_file = download(resolved, payload / ("Visual-C-runtime-terms" + suffix))
                            magic = license_file.read_bytes()[:5]
                            if (suffix == ".rtf" and not magic.startswith(b"{\\rtf")) or (suffix == ".pdf" and magic != b"%PDF-"):
                                license_file.unlink()
                                raise ValueError("Microsoft license download was not the declared document format")
                            inspection[label]["downloaded_license_sha256"] = digest(license_file)
        except Exception as error:
            inspection[label] = {"error": str(error)}
    redist = Path(os.environ["VCToolsRedistDir"])
    if not any(payload.glob("Visual-C-runtime-terms.txt")) and not any(payload.glob("Visual-C-runtime-terms.rtf")):
        try:
            inspection["signed_crt_redist_license"] = acquire_crt_terms(payload)
        except Exception as error:
            inspection["crt_redist_license_error"] = str(error)
    inspection["crt_license_candidates"] = [str(p) for p in redist.parent.rglob("*") if p.is_file() and re.search(r"license|eula", p.name, re.I)][:25]
    evidence = Path(".local/evidence/runtime-acquisition.json")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(inspection, indent=2), encoding="utf-8")
    for key, value in inspection.items():
        note = json.dumps(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::notice title=Microsoft runtime " + key + "::" + note)
    terms = payload / "WebView2-runtime-terms.txt"
    if terms.is_file():
        shutil.copy2(terms, destination / "LICENSE-WebView2-runtime.txt")
        for dll in (payload / "models").glob("*.dll"):
            if dll.name.lower().startswith(("vcruntime", "msvcp", "concrt")):
                shutil.copy2(dll, destination / dll.name)
        manifest = {"version": VERSION, "source": SOURCE, "archive_sha256": CAB_HASH,
                    "license_file": "LICENSE-WebView2-runtime.txt",
                    "files": {p.relative_to(destination).as_posix(): digest(p) for p in sorted(destination.rglob("*")) if p.is_file()}}
        (destination / "webview2-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
