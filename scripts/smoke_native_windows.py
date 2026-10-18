"""Actual Tauri/WebView2 UI + embedded model on Windows, with developer PATH hidden.

This is a hosted-runner acceptance test, not a claim about a clean Windows VM.
No model, native bridge, folder picker or HTTP API is replaced by a fixture.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request


def wait_for_cdp(port, process):
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError("Actual native desktop exited during startup")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError("Native WebView2 debugging endpoint did not start")


def main():
    if os.name != "nt":
        raise RuntimeError("Actual Windows desktop acceptance requires Windows")
    from playwright.sync_api import sync_playwright, expect
    from pywinauto import Desktop

    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--payload", default=".local/package")
    args = parser.parse_args()
    payload = Path(args.payload).resolve(strict=True)
    evidence = Path(".local/evidence").resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    port = 19222
    with tempfile.TemporaryDirectory(prefix="stanicode-native-") as directory:
        root = Path(directory).resolve()
        workspace = root / "workspace"
        workspace.mkdir()
        executable = root / "STANICODE.exe"
        shutil.copy2(args.executable, executable)
        for dll in (payload / "models").glob("*.dll"):
            if dll.name.lower().startswith(("vcruntime", "msvcp", "concrt")):
                shutil.copy2(dll, root / dll.name)
        # A build-only junction avoids duplicating multi-GB weights. The
        # distributable ZIP contains real files, never this junction.
        subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "payload"), str(payload)], check=True, stdout=subprocess.DEVNULL)
        environment = {
            key: value for key, value in os.environ.items()
            if key in {"SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "COMSPEC"}
        }
        environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        environment["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"--remote-debugging-port={port}"
        environment["WEBVIEW2_USER_DATA_FOLDER"] = str(root / "webview-state")
        for tool in ("python", "node", "git", "cargo", "ollama"):
            if shutil.which(tool, path=environment["PATH"]):
                raise AssertionError("Developer tool unexpectedly reachable: " + tool)
        report = {"kind": "actual-native-tauri-fixed-webview-real-model", "developer_tools_on_product_path": False,
                  "clean_windows_vm": False, "hosted_runner": True, "folder_picker": False,
                  "real_inference": False, "restart_history": False}
        firewall_group = "STANICODE acceptance " + root.name
        rules = root / "firewall.ps1"
        rules.write_text('''param([string]$mode, [string]$programs, [string]$group)
$ErrorActionPreference='Stop'
if ($mode -eq 'remove') {
  Get-NetFirewallRule -Group $group -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  exit
}
if (Get-NetFirewallProfile | Where-Object { -not $_.Enabled }) { throw 'Windows firewall is not enabled' }
# Windows rejects the IPv6 /0 prefix. Explicit ranges also avoid the
# unspecified/broadcast IPv4 endpoints while preserving IPv4 loopback.
$addresses = @('1.0.0.0-126.255.255.255','128.0.0.0-255.255.255.254','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe')
foreach ($program in (Get-Content -LiteralPath $programs -Raw | ConvertFrom-Json)) {
  foreach ($address in $addresses) {
    try {
      New-NetFirewallRule -DisplayName ($group+' '+[IO.Path]::GetFileName($program)+' '+$address) -Group $group -Direction Outbound -Action Block -Program $program -RemoteAddress $address | Out-Null
    } catch { throw "Firewall rule failed for program '$program', address '$address': $_" }
  }
}
''', encoding="utf-8")
        programs = root / "firewall-programs.json"
        programs.write_text(json.dumps([str(p) for p in (
            executable, payload / "stanicode-agent.exe", payload / "models" / "llama-server.exe",
            payload / "webview2" / "msedgewebview2.exe",
        )]), encoding="utf-8")

        def launch():
            app = subprocess.Popen([str(executable)], env=environment)
            try:
                wait_for_cdp(port, app)
            except Exception:
                subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                raise
            return app

        app = None
        browser = None
        try:
            subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File", str(rules), "add", str(programs), firewall_group], check=True)
            report["external_network_blocked_by_windows_firewall"] = True
            with sync_playwright() as playwright:
                app = launch()
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                context = browser.contexts[0]
                deadline = time.monotonic() + 60
                while not context.pages:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Native webview page missing")
                    time.sleep(0.2)
                page = context.pages[0]
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.get_by_role("button", name="Scegli cartella").click()
                # Drive the actual operating-system picker, not a patched invoke.
                dialog = Desktop(backend="win32").window(class_name="#32770")
                dialog.wait("visible", timeout=30)
                dialog.set_focus()
                from pywinauto.keyboard import send_keys
                send_keys("%d")
                send_keys(str(workspace), with_spaces=True, pause=0.01)
                send_keys("{ENTER}")
                time.sleep(0.5)
                # Folder dialogs normally expose their accept button as ID 1.
                dialog.child_window(control_id=1).click()
                expect(page.locator(".workspace code")).to_have_text(str(workspace), timeout=30000)
                report["folder_picker"] = True
                start = page.get_by_role("button", name="Avvia sviluppo", exact=False)
                page.get_by_role("textbox", name="Cosa vuoi sviluppare?").fill(
                    "Create calculator.py with add(a,b), and test_calculator.py using Python unittest checking add(2,3)==5 and add(-2,2)==0. Use python-unittest. No dependencies."
                )
                expect(start).to_be_enabled(timeout=360000)
                second = subprocess.Popen([str(executable)], env=environment)
                second.wait(timeout=15)
                if second.returncode != 0 or app.poll() is not None:
                    raise AssertionError("Second launch did not focus the existing instance")
                report["single_instance"] = True
                start.click()
                deadline = time.monotonic() + 1800
                approved = 0
                while time.monotonic() < deadline:
                    state = page.locator(".badge").get_attribute("data-state")
                    if state == "awaiting_approval":
                        paths = page.locator("details summary").all_text_contents()
                        if any(path not in {"calculator.py", "test_calculator.py"} for path in paths):
                            raise AssertionError("Native task proposed unexpected files: " + repr(paths))
                        if not approved:
                            assert not (workspace / "calculator.py").exists(), "Write before approval"
                        page.get_by_role("button", name="Approva modifiche e test").click()
                        approved += 1
                        expect(page.get_by_role("button", name="Approva modifiche e test")).not_to_be_visible(timeout=15000)
                    elif state == "completed":
                        break
                    elif state in {"failed", "cancelled", "interrupted"}:
                        raise RuntimeError("Native coding task failed: " + page.locator(".panel").inner_text())
                    time.sleep(0.5)
                else:
                    raise TimeoutError("Native real-model task timed out")
                assert approved and (workspace / "calculator.py").is_file()
                report["real_inference"] = True
                with page.expect_download() as pending:
                    page.get_by_role("button", name="Esporta rapporto").click()
                pending.value.save_as(str(evidence / "native-task-report.json"))
                report["task"] = json.loads((evidence / "native-task-report.json").read_text(encoding="utf-8"))
                page.screenshot(path=str(evidence / "native-real-model.png"), full_page=True)
                page.get_by_label("Language").select_option("en")
                page.get_by_role("button", name="Settings", exact=True).click()
                page.get_by_label("Theme").select_option("light")
                expect(page.locator("html")).to_have_attribute("data-theme", "light")
                # Close the real window through Windows, allowing owned model shutdown.
                Desktop(backend="win32").window(title="STANICODE").close()
                app.wait(timeout=30)
                browser.close()
                browser = None
                app = launch()
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                page = browser.contexts[0].pages[0]
                page.get_by_role("button", name="Sessions", exact=True).click()
                expect(page.locator(".session").first).to_contain_text("Create calculator.py", timeout=30000)
                report["restart_history"] = True
                report["javascript_errors"] = errors
                if errors:
                    raise AssertionError(errors)
                Desktop(backend="win32").window(title="STANICODE").close()
                app.wait(timeout=30)
                browser.close()
                browser = None
                print("PASS: actual Windows UI, actual folder picker, real local model, approved writes, real tests, export, locale/theme and restart history; developer PATH hidden.")
        finally:
            (evidence / "native-windows.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            if browser:
                try:
                    browser.contexts[0].pages[0].screenshot(path=str(evidence / "native-failure.png"))
                    browser.close()
                except Exception:
                    pass
            if app and app.poll() is None:
                subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File", str(rules), "remove", str(programs), firewall_group], check=True)
            # Remove only the junction, not the payload to which it points.
            os.rmdir(root / "payload")


if __name__ == "__main__":
    main()
