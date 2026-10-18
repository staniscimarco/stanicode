import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "agent"))
from engine import Engine, Store, Workspace
from server import make_server
from runtime import Runtime


class MockModel:
    def generate(self, *args):
        return {
            "summary": "Create a tested sum function",
            "files": [
                {
                    "path": "calculator.py",
                    "content": "def add(a, b):\n    return a + b\n",
                },
                {
                    "path": "test_calculator.py",
                    "content": "import unittest\nfrom calculator import add\nclass SumTests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n",
                },
            ],
            "test": "python-unittest",
        }


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "workspace").mkdir()
        self.store = Store(self.root / "state" / "tasks.sqlite3")
        self.engine = Engine(self.store, MockModel())
        self.addCleanup(self.finish_workers)

    def finish_workers(self):
        for control in self.engine.controls.values():
            control["cancel"] = True
        for worker in self.engine.workers.values():
            worker.join(timeout=5)

    def wait(self, task, states):
        deadline = time.monotonic() + 10
        while task["state"] not in states and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertIn(task["state"], states, task)
        if task["state"] in {"completed", "failed", "cancelled"}:
            self.engine.workers[task["id"]].join(timeout=3)
            self.assertFalse(self.engine.workers[task["id"]].is_alive())

    def test_end_to_end_and_persistence_rollback(self):
        task = self.engine.create(
            str(self.root / "workspace"), "Create add with a test"
        )
        self.wait(task, {"awaiting_approval", "failed"})
        self.assertEqual(task["state"], "awaiting_approval")
        self.assertFalse((self.root / "workspace" / "calculator.py").exists())
        self.engine.control(task["id"], "approve")
        self.wait(task, {"completed", "failed"})
        self.assertEqual(task["state"], "completed", task)
        self.assertTrue(any("Ran 1 test" in e["message"] for e in task["events"]))
        restarted = Engine(Store(self.store.path), MockModel())
        self.assertEqual(restarted.tasks[task["id"]]["state"], "completed")
        restarted.rollback(task["id"])
        self.assertFalse((self.root / "workspace" / "calculator.py").exists())

    def test_traversal_secrets_and_symlink(self):
        ws = Workspace(self.root / "workspace")
        for name in [
            "../escape",
            "/tmp/escape",
            ".env",
            ".git/config",
            ".env.local",
            "nested/../../x",
        ]:
            with self.assertRaises(ValueError):
                ws.path(name)
        try:
            (self.root / "workspace" / "link").symlink_to(
                self.root, target_is_directory=True
            )
        except OSError:
            self.skipTest("OS does not allow test symlink")
        with self.assertRaises(ValueError):
            ws.path("link/escape")

    def test_cancel_pending(self):
        task = self.engine.create(str(self.root / "workspace"), "test")
        self.wait(task, {"awaiting_approval"})
        self.engine.control(task["id"], "cancel")
        self.wait(task, {"cancelled"})
        self.assertEqual(list((self.root / "workspace").iterdir()), [])

    def test_invalid_action(self):
        self.engine.model.generate = lambda *args: {
            "files": [{"path": "../escape", "content": "oops"}]
        }
        task = self.engine.create(str(self.root / "workspace"), "test")
        self.wait(task, {"failed"})
        self.assertFalse((self.root / "escape").exists())

    def test_rollback_preserves_external_edits(self):
        task = self.engine.create(str(self.root / "workspace"), "test")
        self.wait(task, {"awaiting_approval"})
        self.engine.control(task["id"], "approve")
        self.wait(task, {"completed"})
        p = self.root / "workspace" / "calculator.py"
        p.write_text("# user changes")
        with self.assertRaises(ValueError):
            self.engine.rollback(task["id"])
        self.assertEqual(p.read_text(), "# user changes")

    def test_http_authentication_origins_and_health(self):
        class Ready:
            status = {"ready": False, "detail": "test"}

        server = make_server(self.engine, "test-session-token", Ready())
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/health"
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(url)
        self.assertEqual(e.exception.code, 401)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer test-session-token",
                "Origin": "https://evil.example",
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 403)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer test-session-token",
                "Origin": "tauri://localhost",
            },
        )
        with urllib.request.urlopen(req) as response:
            self.assertTrue(json.load(response)["backend"])

    def test_missing_bundle_honestly_unavailable(self):
        runtime = Runtime(self.root / "missing")
        runtime.start()
        self.assertFalse(runtime.status["ready"])

    def test_injected_credentials_not_passed_to_test_process(self):
        from engine import execution_environment
        from unittest.mock import patch

        with patch.dict(
            "os.environ",
            {"GH_TOKEN": "test-placeholder", "SOME_API_KEY": "test-placeholder"},
        ):
            child_env = execution_environment()
        self.assertNotIn("GH_TOKEN", child_env)
        self.assertNotIn("SOME_API_KEY", child_env)

    def test_pause_resume_and_cancel(self):
        generated = threading.Event()
        release = threading.Event()

        def generate(*args):
            generated.set()
            release.wait(5)
            return MockModel().generate()

        self.engine.model.generate = generate
        task = self.engine.create(str(self.root / "workspace"), "test")
        self.assertTrue(generated.wait(3))
        self.engine.control(task["id"], "pause")
        release.set()
        self.wait(task, {"paused"})
        self.engine.control(task["id"], "resume")
        self.wait(task, {"awaiting_approval"})
        self.engine.control(task["id"], "cancel")
        self.wait(task, {"cancelled"})

    def test_zero_tests_never_counts_as_success(self):
        self.engine.model.generate = lambda *args: {
            "files": [{"path": "example.py", "content": "value=42"}],
            "test": "python-unittest",
        }
        task = self.engine.create(str(self.root / "workspace"), "test")
        for _ in range(3):
            self.wait(task, {"awaiting_approval"})
            self.engine.control(task["id"], "approve")
            # Wait for approval to be consumed before awaiting the next round.
            deadline = time.monotonic() + 5
            while (
                task["state"] != "failed"
                and self.engine.controls[task["id"]]["approval"] is not None
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            if task["state"] == "failed":
                break
        self.wait(task, {"failed"})
        self.assertTrue(
            any("No tests discovered" in e["message"] for e in task["events"])
        )

    def test_context_is_bounded(self):
        ws = Workspace(self.root / "workspace")
        for i in range(20):
            (ws.root / f"{i}.txt").write_text("x" * 5000)
        self.assertLessEqual(sum(map(len, ws.context().values())), 12000)

    def test_bad_hash_rejected(self):
        bundle = self.root / "bundle"
        bundle.mkdir()
        (bundle / "runtime").write_text("bad")
        (bundle / "manifest.json").write_text(
            json.dumps(
                {"runtime": {"file": "runtime", "sha256": "0" * 64, "license": "MIT"}}
            )
        )
        runtime = Runtime(bundle)
        runtime.start()
        self.assertFalse(runtime.status["ready"])
        self.assertIn("checksum mismatch", runtime.status["detail"])


if __name__ == "__main__":
    unittest.main()
