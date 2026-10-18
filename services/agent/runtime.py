"""Verified local model supervision. No downloads happen at application startup."""

from pathlib import Path
import subprocess
import time
import secrets
import threading
import socket
from resources import available_ram
from bundle import verify
from engine import execution_environment
import urllib.request


class Runtime:
    def __init__(self, bundle, log_path=None):
        self.bundle = Path(bundle)
        self.process = None
        self.log_path = Path(log_path) if log_path else None
        self.log = None
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.endpoint = f"http://127.0.0.1:{self.port}"
        self.api_key = secrets.token_urlsafe(32)
        self.stopped = threading.Event()
        self.provenance = {"verified": False}
        self.status = {
            "ready": False,
            "detail": "Bundled inference runtime/model not installed",
        }

    def start(self):
        try:
            self.status = {
                "ready": False,
                "phase": "verifying",
                "detail": "Verifying offline payload checksums",
            }
            manifest = verify(self.bundle)
            paths = [
                (self.bundle / manifest[key]["file"]).resolve(strict=True)
                for key in ("runtime", "model")
            ]
            self.provenance = {
                key: {
                    field: manifest[key][field]
                    for field in ("source", "version", "sha256", "license")
                }
                for key in ("runtime", "model")
            }
            minimum = manifest["model"].get("minimum_available_ram_bytes")
            if not isinstance(minimum, int) or minimum <= 0:
                raise ValueError("Model RAM requirement is missing")
            available = available_ram()
            if available is not None and available < minimum:
                raise RuntimeError("Insufficient available RAM for the bundled model")
            if self.stopped.is_set():
                return
            self.status = {
                "ready": False,
                "phase": "loading",
                "detail": "Loading the verified local coding model",
            }
            if self.log_path:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                self.log = self.log_path.open("wb")
            self.process = subprocess.Popen(
                [
                    str(paths[0]),
                    "-m",
                    str(paths[1]),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                    "-c",
                    "16384",
                    "--parallel",
                    "1",
                    "--api-key",
                    self.api_key,
                ],
                env=execution_environment(),
                stdout=self.log or subprocess.DEVNULL,
                stderr=self.log or subprocess.DEVNULL,
            )
            # CPU-only startup on a laptop can take several minutes.
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                if self.stopped.is_set():
                    self.stop()
                    return
                if self.process.poll() is not None:
                    raise RuntimeError(f"Inference process exited before readiness (code {self.process.returncode}); see inference.log")
                try:
                    with urllib.request.urlopen(
                        urllib.request.Request(
                            self.endpoint + "/v1/models",
                            headers={"Authorization": "Bearer " + self.api_key},
                        ),
                        timeout=1,
                    ) as response:
                        if response.status == 200:
                            self.status = {
                                "ready": True,
                                "phase": "ready",
                                "detail": "Verified local runtime and model loaded",
                            }
                            while not self.stopped.wait(0.5):
                                if self.process.poll() is not None:
                                    self.status = {
                                        "ready": False,
                                        "phase": "error",
                                        "detail": "Local inference process exited; restart STANICODE",
                                    }
                                    return
                            return
                except OSError:
                    time.sleep(0.5)
            raise RuntimeError("Inference readiness timeout")
        except Exception as e:
            self.stop()
            self.status = {
                "ready": False,
                "phase": "error",
                "detail": "Offline model bundle not installed"
                if isinstance(e, FileNotFoundError)
                and not (self.bundle / "manifest.json").exists()
                else str(e),
            }

    def stop(self):
        self.stopped.set()
        self.status = {"ready": False, "detail": "Local inference stopped"}
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.log:
            self.log.close()
            self.log = None
