"""Verified local model supervision. No downloads happen at application startup."""

import hashlib
import json
from pathlib import Path
import subprocess
import time
import secrets
import threading
from engine import execution_environment
import urllib.request


class Runtime:
    def __init__(self, bundle):
        self.bundle = Path(bundle)
        self.process = None
        self.api_key = secrets.token_urlsafe(32)
        self.stopped = threading.Event()
        self.status = {
            "ready": False,
            "detail": "Bundled inference runtime/model not installed",
        }

    def start(self):
        try:
            manifest = json.loads((self.bundle / "manifest.json").read_text())
            paths = []
            for key in ("runtime", "model"):
                entry = manifest[key]
                p = (self.bundle / entry["file"]).resolve(strict=True)
                if not p.is_relative_to(self.bundle.resolve()) or not p.is_file():
                    raise ValueError("Invalid bundle path")
                with p.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                if digest != entry["sha256"]:
                    raise ValueError(f"{key} checksum mismatch")
                if not entry.get("license"):
                    raise ValueError("License metadata missing")
                paths.append(p)
            if self.stopped.is_set():
                return
            self.process = subprocess.Popen(
                [
                    str(paths[0]),
                    "-m",
                    str(paths[1]),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8766",
                    "-c",
                    "16384",
                    "--parallel",
                    "1",
                    "--api-key",
                    self.api_key,
                ],
                env=execution_environment(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(120):
                if self.stopped.is_set():
                    self.stop()
                    return
                if self.process.poll() is not None:
                    raise RuntimeError("Inference process exited before readiness")
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:8766/health", timeout=1
                    ) as response:
                        if response.status == 200:
                            self.status = {
                                "ready": True,
                                "detail": "Verified local runtime and model loaded",
                            }
                            return
                except OSError:
                    time.sleep(0.5)
            raise RuntimeError("Inference readiness timeout")
        except Exception as e:
            self.stop()
            self.status = {"ready": False, "detail": str(e)}

    def stop(self):
        self.stopped.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
