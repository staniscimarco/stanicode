"""Real Chromium + real backend/file/test operations; simulated inference and native bridge."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "agent"))
from engine import Engine, Store
from server import make_server
from playwright.sync_api import sync_playwright


class FixtureModel:
    identity = "SIMULATED INFERENCE — browser test only"

    def plan(self, *a):
        return {
            "steps": ["Create calculator and test"],
            "acceptance": "Python unittest passes",
        }

    def generate(self, *a):
        return {
            "summary": "Create add function with one test",
            "test": "python-unittest",
            "files": [
                {"path": "calculator.py", "content": "def add(a,b):\n    return a+b\n"},
                {
                    "path": "test_calculator.py",
                    "content": "import unittest\nfrom calculator import add\nclass Calculator(unittest.TestCase):\n    def test_add(self):self.assertEqual(add(2,3),5)\n",
                },
            ],
        }

    def review(self, *a):
        return {"accepted": True, "reason": "Fixture reviewer: generated test passed"}


class FixtureRuntime:
    status = {"ready": True, "detail": "Simulated inference for automated browser test"}


def main():
    root = Path(__file__).resolve().parents[1]
    executable = shutil.which("chromium") or shutil.which("google-chrome")
    with tempfile.TemporaryDirectory(prefix="stanicode-browser-") as directory:
        temp = Path(directory)
        workspace = temp / "workspace"
        workspace.mkdir()
        engine = Engine(Store(temp / "state" / "tasks.sqlite3"), FixtureModel())
        token = "browser-test-only-session"
        server = make_server(engine, token, FixtureRuntime())
        threading.Thread(target=server.serve_forever, daemon=True).start()
        log = (temp / "vite.log").open("w")
        frontend = subprocess.Popen(
            [
                shutil.which("node"),
                str(root / "node_modules/vite/bin/vite.js"),
                "--config",
                str(root / "apps/desktop/vite.config.ts"),
            ],
            cwd=root,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                if frontend.poll() is not None:
                    raise RuntimeError("Vite could not start; inspect the chosen port")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:1420", timeout=1):
                        break
                except OSError:
                    time.sleep(0.1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=executable, headless=True, args=["--no-sandbox"]
                )
                page = browser.new_page(viewport={"width": 1360, "height": 1000})
                failures = []
                page.on("pageerror", lambda error: failures.append(str(error)))
                values = json.dumps(
                    {
                        "connection": {"port": server.server_port, "token": token},
                        "workspace": str(workspace),
                    }
                )
                page.add_init_script(
                    "const fixture="
                    + values
                    + '; window.__TAURI_INTERNALS__={invoke:async(command)=>{if(command==="connection")return fixture.connection;if(command==="plugin:dialog|open")return fixture.workspace;throw Error("Unexpected native command "+command);}};'
                )
                page.goto("http://localhost:1420")
                page.get_by_role("button", name="Scegli cartella").click()
                page.get_by_role("textbox", name="Cosa vuoi sviluppare?").fill(
                    "Create a tested calculator"
                )
                page.get_by_role("button", name="Avvia sviluppo", exact=False).click()
                page.get_by_role("button", name="Approva modifiche e test").wait_for(
                    timeout=15000
                )
                assert not (workspace / "calculator.py").exists(), (
                    "File was written before approval"
                )
                page.get_by_text("calculator.py", exact=True).wait_for()
                page.get_by_role("button", name="Approva modifiche e test").click()
                page.locator('.badge[data-state="completed"]').wait_for(timeout=15000)
                assert (workspace / "calculator.py").read_text().startswith("def add")
                assert engine.store.history()[0]["state"] == "completed"
                page.get_by_role("button", name="Memoria", exact=True).click()
                page.locator("summary").filter(
                    has_text="Create a tested calculator"
                ).wait_for()
                page.get_by_role("textbox", name="Cerca nella memoria").fill(
                    "calculator"
                )
                page.get_by_role("button", name="Cerca", exact=True).click()
                page.locator("summary").filter(
                    has_text="Create a tested calculator"
                ).wait_for()
                page.get_by_role("button", name="Attività", exact=True).click()
                with page.expect_download() as download:
                    page.get_by_role("button", name="Esporta rapporto").click()
                report = json.loads(Path(download.value.path()).read_text())
                assert report["state"] == "completed"
                page.get_by_role("combobox", name="Language").select_option("en")
                page.get_by_role(
                    "heading", name="What do you want to build?"
                ).wait_for()
                page.get_by_role("button", name="Settings", exact=True).click()
                page.locator("select").nth(1).select_option("light")
                assert page.locator("html").get_attribute("data-theme") == "light"
                page.get_by_role("button", name="Activity", exact=True).click()
                artifact = root / ".local" / "evidence"
                artifact.mkdir(parents=True, exist_ok=True)
                page.screenshot(
                    path=str(artifact / "browser-fixture.png"), full_page=True
                )
                page.on("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="Restore files", exact=True).click()
                page.locator('.badge[data-state="rolled_back"]').wait_for(timeout=10000)
                assert not (workspace / "calculator.py").exists()
                assert not failures, failures
                browser.close()
                print(
                    "PASS: real Chromium UI → authenticated backend → approval → file writes → real unittest → review → memory search → report export → locale/theme → rollback"
                )
                print(
                    "Inference and native folder/session bridge were simulated; this is not a Windows or real-model acceptance result."
                )
        finally:
            frontend.terminate()
            frontend.wait(timeout=10)
            log.close()
            for control in engine.controls.values():
                control["cancel"] = True
            for worker in engine.workers.values():
                worker.join(timeout=5)
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
