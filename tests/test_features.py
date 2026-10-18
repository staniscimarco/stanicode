"""Integration checks for local roles, retrieval, portable paths and language recipes."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "agent"))
from engine import Engine, Store, Workspace, execution_environment
from local_model import LlamaModel
from memory import CaseMemory, redact
import checkpoints
import validation
from test_engine import MockModel


class Features(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = Store(self.root / "state" / "data.sqlite3")

    def finish(self, engine, task):
        deadline = time.monotonic() + 15
        while (
            task["state"] not in {"completed", "failed", "cancelled"}
            and time.monotonic() < deadline
        ):
            if (
                task["state"] == "awaiting_approval"
                and engine.controls[task["id"]]["approval"] is None
            ):
                engine.control(
                    task["id"], "approve", engine.controls[task["id"]]["approval_id"]
                )
            time.sleep(0.01)
        engine.workers[task["id"]].join(timeout=3)
        self.assertFalse(engine.workers[task["id"]].is_alive(), task)

    def test_node_workspace_runs_real_tests(self):
        if not shutil.which("node"):
            self.skipTest("Node not installed")
        model = MockModel()
        model.generate = lambda *a: {
            "summary": "Add function with Node test",
            "test": "node-test",
            "files": [
                {
                    "path": "add.test.cjs",
                    "content": "const {test}=require('node:test');const assert=require('node:assert/strict');test('add',()=>assert.equal(2+3,5));\n",
                }
            ],
        }
        engine = Engine(self.store, model)
        task = engine.create(self.workspace, "Create a Node add test")
        self.finish(engine, task)
        self.assertEqual(task["state"], "completed", task)
        self.assertTrue(any("# tests 1" in e["message"] for e in task["events"]))

    def test_validation_timeout_reaches_debugger_and_requires_new_approval(self):
        import runner
        actual_run = runner.run
        calls, feedback = [], []
        model = MockModel()
        generate = model.generate

        def propose(prompt, context, previous):
            feedback.append(previous)
            return generate(prompt, context, previous)

        def validate(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("Validation timed out: generated test hung")
            return actual_run(*args, **kwargs)

        model.generate = propose
        engine = Engine(self.store, model)
        with patch("runner.run", side_effect=validate):
            task = engine.create(self.workspace, "Create tested addition")
            self.finish(engine, task)
        self.assertEqual(task["state"], "completed", task)
        self.assertEqual(len(calls), 2)
        self.assertIn("timed out", feedback[1])
        self.assertEqual(sum(e["phase"] == "approval" for e in task["events"]), 2)

    def test_cargo_recipe_runs_real_rust_test(self):
        if not shutil.which("cargo"):
            self.skipTest("Rust not installed")
        (self.workspace / "src").mkdir()
        (self.workspace / "Cargo.toml").write_text(
            '[package]\nname="test_project"\nversion="0.1.0"\nedition="2021"\n'
        )
        (self.workspace / "src" / "lib.rs").write_text(
            "#[test] fn arithmetic() { assert_eq!(2+3,5); }"
        )
        result = subprocess.run(
            validation.command("cargo-test", self.workspace),
            cwd=self.workspace,
            env=execution_environment(),
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertTrue(
            validation.passed(
                "cargo-test", result.returncode, result.stdout + result.stderr
            ),
            result.stderr,
        )

    def test_empty_node_suite_not_success(self):
        self.assertFalse(validation.passed("node-test", 0, "# tests 0\n# fail 0\n"))

    def test_empty_cargo_suite_not_success(self):
        self.assertFalse(
            validation.passed("cargo-test", 0, "test result: ok. 0 passed; 0 failed")
        )

    def test_missing_tool_has_actionable_diagnostic(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "required by this project"):
                validation.command("node-test", self.workspace)

    def test_portable_path_rejections(self):
        ws = Workspace(self.workspace)
        for path in [
            ".GIT/config",
            "CON",
            "NUL.txt",
            "COM1.js",
            "folder./code",
            "path/file:secret",
            "C:/outside",
            "folder\\file",
            "folder/file ",
        ]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                ws.path(path)

    def test_atomic_write_does_not_modify_external_hardlink(self):
        external = self.root / "external"
        external.write_text("original")
        try:
            os.link(external, self.workspace / "code.txt")
        except OSError:
            self.skipTest("Hardlinks unsupported")
        Workspace(self.workspace).write("code.txt", "replacement")
        self.assertEqual(external.read_text(), "original")
        self.assertEqual((self.workspace / "code.txt").read_text(), "replacement")

    def test_memory_dedup_retrieval_and_deletion(self):
        memory = CaseMemory(self.store)
        task = {
            "id": "case",
            "prompt": "Repair calculator arithmetic api_key=secretvalue",
            "changes": [{"path": "add.py", "after": "def add(a,b):return a+b"}],
        }
        for _ in range(2):
            memory.remember(
                task,
                "python-unittest",
                "Ran 1 test\nOK",
                "Correct arithmetic",
                "fixture",
            )
        cases = memory.search("calculator")
        self.assertEqual(len(cases), 1)
        self.assertNotIn("secretvalue", cases[0]["request"])
        self.assertEqual(memory.search("unrelatedproject"), [])
        self.assertFalse(cases[0]["metadata"]["weight_training"])
        memory.delete()
        self.assertEqual(memory.search(), [])

    def test_invalid_json_is_repaired_with_bounded_retry(self):
        model = MockModel()
        calls = []

        def generate(*a):
            calls.append(1)
            if len(calls) == 1:
                raise json.JSONDecodeError("bad model JSON", "", 0)
            return MockModel().generate()

        model.generate = generate
        engine = Engine(self.store, model)
        task = engine.create(self.workspace, "Create tests")
        self.finish(engine, task)
        self.assertEqual(task["state"], "completed", task)
        self.assertEqual(len(calls), 2)

    def test_independent_reviewer_can_block_completion(self):
        model = MockModel()
        model.review = lambda *a: {"accepted": False, "reason": "Requirement missing"}
        engine = Engine(self.store, model)
        task = engine.create(self.workspace, "Create tests")
        self.finish(engine, task)
        self.assertEqual(task["state"], "failed")
        self.assertEqual(engine.memory.search(), [])

    def test_restart_marks_pending_approval_interrupted(self):
        self.store.save(
            {
                "id": "lost",
                "workspace": str(self.workspace),
                "prompt": "test",
                "state": "awaiting_approval",
                "events": [],
                "changes": [],
            }
        )
        restarted = Store(self.store.path)
        self.assertEqual(restarted.history()[0]["state"], "interrupted")

    def test_git_checkpoint_keeps_user_index_unchanged(self):
        if not shutil.which("git"):
            self.skipTest("Git unavailable")

        def git(*a):
            return subprocess.run(
                ["git", *a],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                check=True,
            )

        git("init")
        (self.workspace / "code.py").write_text("before")
        git("add", "code.py")
        before = (self.workspace / ".git" / "index").read_bytes()
        sha = checkpoints.create(
            self.workspace, ["code.py"], "fixture", execution_environment()
        )
        self.assertEqual(len(sha), 40)
        self.assertEqual((self.workspace / ".git" / "index").read_bytes(), before)
        self.assertEqual(git("show", sha + ":code.py").stdout, "before")

    def test_local_http_protocol_exercises_all_three_roles(self):
        roles = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                self.assert_auth = (
                    self.headers.get("Authorization") == "Bearer local-test-key"
                )
                if not self.assert_auth:
                    self.send_error(401)
                    return
                request = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                system = request["messages"][0]["content"]
                if "architect role" in system:
                    role = "architect"
                    result = {
                        "steps": ["Implement tested addition"],
                        "acceptance": "test passes",
                    }
                elif "independent reviewer role" in system:
                    role = "reviewer"
                    result = {"accepted": True, "reason": "test-backed changes"}
                else:
                    role = "implementer"
                    result = MockModel().generate()
                roles.append(role)
                body = json.dumps(
                    {"choices": [{"message": {"content": json.dumps(result)}}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        model = LlamaModel(f"http://127.0.0.1:{server.server_port}", "local-test-key")
        engine = Engine(self.store, model)
        task = engine.create(self.workspace, "Build a calculator")
        self.finish(engine, task)
        self.assertEqual(task["state"], "completed", task)
        self.assertEqual(roles, ["architect", "implementer", "reviewer"])

    def test_model_cannot_target_remote_service(self):
        with self.assertRaises(ValueError):
            LlamaModel("https://cloud.example.com:443")

    def test_runner_timeout_is_bounded(self):
        import runner

        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            runner.run(
                [sys.executable, "-c", "import time;time.sleep(10)"],
                self.workspace,
                execution_environment(),
                timeout=0.15,
            )
        self.assertLess(time.monotonic() - start, 3)

    def test_runner_output_is_bounded_and_exit_code_preserved(self):
        import runner

        code, output = runner.run(
            [
                sys.executable,
                "-c",
                'import sys;sys.stdout.write("x"*1000000);sys.exit(7)',
            ],
            self.workspace,
            execution_environment(),
        )
        self.assertEqual(code, 7)
        self.assertLess(len(output), 270000)
        self.assertIn("truncated", output)

    def test_runner_cancel_terminates_owned_process(self):
        import runner

        with self.assertRaises(InterruptedError):
            runner.run(
                [sys.executable, "-c", "import time;time.sleep(10)"],
                self.workspace,
                execution_environment(),
                cancel=lambda: True,
            )

    def test_cancel_interrupts_inflight_local_http(self):
        received = threading.Event()
        release = threading.Event()

        class Slow(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                received.set()
                release.wait(5)
                self.send_response(200)
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Slow)
        server.daemon_threads = True
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(release.set)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        model = LlamaModel(f"http://127.0.0.1:{server.server_port}")
        engine = Engine(self.store, model)
        task = engine.create(self.workspace, "test")
        self.assertTrue(received.wait(3))
        engine.control(task["id"], "cancel")
        engine.workers[task["id"]].join(timeout=2)
        self.assertFalse(engine.workers[task["id"]].is_alive())
        self.assertEqual(task["state"], "cancelled")

    def test_rollback_blocked_while_another_task_is_active(self):
        engine = Engine(self.store, MockModel())
        old = engine.create(self.workspace, "old")
        self.finish(engine, old)
        active = engine.create(self.workspace, "new")
        try:
            with self.assertRaisesRegex(ValueError, "active task"):
                engine.rollback(old["id"])
            with self.assertRaisesRegex(ValueError, "no longer active"):
                engine.control(old["id"], "cancel")
        finally:
            engine.control(active["id"], "cancel")
            engine.workers[active["id"]].join(timeout=3)

    def test_stale_approval_cannot_apply_another_proposal(self):
        engine = Engine(self.store, MockModel())
        task = engine.create(self.workspace, "test")
        deadline = time.monotonic() + 5
        while task["state"] != "awaiting_approval" and time.monotonic() < deadline:
            time.sleep(0.01)
        try:
            with self.assertRaisesRegex(ValueError, "Stale approval"):
                engine.control(task["id"], "approve", "old-approval")
            self.assertFalse((self.workspace / "calculator.py").exists())
        finally:
            engine.control(task["id"], "cancel")
            engine.workers[task["id"]].join(timeout=3)

    def test_write_ahead_recovery_handles_both_sides_of_a_crash(self):
        for index, actually_written in enumerate((False, True)):
            file = self.workspace / "code.py"
            file.write_text("after" if actually_written else "before")
            task = {
                "id": "crash-" + str(index),
                "workspace": str(self.workspace),
                "prompt": "test",
                "state": "running",
                "events": [],
                "changes": [
                    {
                        "path": "code.py",
                        "before": "before",
                        "after": "after",
                        "applied": False,
                    }
                ],
            }
            self.store.save(task)
            engine = Engine(Store(self.store.path), MockModel())
            engine.rollback(task["id"])
            self.assertEqual(file.read_text(), "before")

    def test_redacts_common_secret_assignments(self):
        self.assertEqual(redact("password=hunter2"), "password=[REDACTED]")


if __name__ == "__main__":
    unittest.main()
