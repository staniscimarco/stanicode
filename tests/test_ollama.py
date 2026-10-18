"""Native Ollama protocol fixture; this is not an installed-model acceptance test."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/agent"))
from ollama import OllamaModel, OllamaRuntime


class OllamaProtocol(unittest.TestCase):
    def test_all_serial_roles_use_existing_model_without_pull(self):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value):
                data = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                calls.append((self.path, None))
                self.reply({"models": [{"name": "fixture:7b", "digest": "fixture-only"}]})

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append((self.path, request))
                role = request["messages"][0]["content"]
                if "independent reviewer" in role:
                    result = {"accepted": True, "reason": "Fixture verdict"}
                elif "architect" in role:
                    result = {"steps": ["Implement and test"], "acceptance": "Actual test passes"}
                else:
                    result = {"summary": "Fixture only", "files": [{"path": "x.py", "content": "pass\n"}], "test": "python-unittest"}
                self.reply({"message": {"content": json.dumps(result)}})

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        runtime = OllamaRuntime("fixture:7b")
        runtime.endpoint = f"http://127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=runtime.start, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not runtime.status["ready"] and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(runtime.status["ready"], runtime.status)
            model = OllamaModel(runtime)
            self.assertIn("steps", model.plan("test", {}, []))
            self.assertEqual(model.generate("test", {}, "")["test"], "python-unittest")
            self.assertTrue(model.review("test", [], "Ran 1 test\nOK")["accepted"])
            posts = [body for path, body in calls if path == "/api/chat"]
            self.assertEqual(len(posts), 3)
            self.assertTrue(all(p["model"] == "fixture:7b" and p["options"]["num_ctx"] == 16384 and p["format"] == "json" and not p["stream"] for p in posts))
            self.assertTrue(all(path in {"/api/tags", "/api/chat"} for path, _ in calls))
            self.assertIn("fixture-only", model.identity)
        finally:
            runtime.stop()
            thread.join(timeout=3)
            server.shutdown()
            server.server_close()

    def test_external_server_cannot_replace_loopback(self):
        runtime = OllamaRuntime("fixture:7b")
        runtime.endpoint = "http://example.com:11434"
        with self.assertRaises(ValueError):
            OllamaModel(runtime)

    def test_invalid_model_name_is_rejected(self):
        for name in ("", "model\nsecond", "model name", "x" * 201):
            with self.assertRaises(ValueError):
                OllamaRuntime(name)
