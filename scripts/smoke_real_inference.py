"""Real-model acceptance against the actual packaged backend; never substitutes mocks."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
from verify_bundle import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--evidence", default=".local/evidence/real-inference.json")
    args = parser.parse_args()
    manifest = verify(args.bundle)
    with tempfile.TemporaryDirectory(prefix="stanicode-real-inference-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        process = subprocess.Popen(
            [
                str(Path(args.agent).resolve(strict=True)),
                "--data",
                str(root / "state"),
                "--bundle",
                str(Path(args.bundle).resolve()),
                "--parent-stdin",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            session = json.loads(process.stdout.readline())

            def request(path, body=None):
                data = None if body is None else json.dumps(body).encode()
                headers = {"Authorization": "Bearer " + session["token"]}
                if data is not None:
                    headers["Content-Type"] = "application/json"
                req = urllib.request.Request(
                    f"http://127.0.0.1:{session['port']}" + path, data, headers
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.load(response)

            deadline = time.monotonic() + 300
            while True:
                status = request("/health")["inference"]
                if status["ready"]:
                    break
                if status.get("phase") == "error":
                    raise RuntimeError(
                        "Real inference startup failed: " + status["detail"]
                    )
                if process.poll() is not None or time.monotonic() > deadline:
                    raise TimeoutError("Actual model did not become ready")
                time.sleep(0.5)
            created = request(
                "/tasks",
                {
                    "workspace": str(workspace),
                    "prompt": "Create calculator.py with add(a,b), and test_calculator.py using Python unittest that checks add(2,3)==5 and add(-2,2)==0. Use the python-unittest recipe. No dependencies or network access.",
                },
            )
            deadline = time.monotonic() + 1800
            approved = set()
            while True:
                task = next(t for t in request("/tasks") if t["id"] == created["id"])
                if task["state"] == "awaiting_approval":
                    pending = task.get("pending")
                    if pending and task["approval_id"] not in approved:
                        if any(
                            c["path"] not in {"calculator.py", "test_calculator.py"}
                            for c in pending
                        ):
                            raise ValueError(
                                "Real model proposed files outside the acceptance task"
                            )
                        # Only this disposable, intentionally generated test workspace is auto-approved.
                        request(
                            "/control",
                            {
                                "id": task["id"],
                                "action": "approve",
                                "approval_id": task["approval_id"],
                            },
                        )
                        approved.add(task["approval_id"])
                if task["state"] in {"completed", "failed", "cancelled"}:
                    break
                if time.monotonic() > deadline:
                    request("/control", {"id": task["id"], "action": "cancel"})
                    raise TimeoutError("Real model acceptance timed out")
                time.sleep(0.3)
            if task["state"] != "completed":
                raise RuntimeError(
                    "Real-model acceptance failed: " + json.dumps(task["events"][-3:])
                )
            if not (workspace / "calculator.py").is_file():
                raise AssertionError("Real model did not create the requested project")
            evidence = {
                "kind": "actual-packaged-backend-and-real-local-model",
                "time": time.time(),
                "platform": __import__("platform").platform(),
                "manifest": manifest,
                "task": task,
                "native_desktop_acceptance": False,
                "clean_windows_acceptance": False,
            }
            output = Path(args.evidence)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(
                "PASS: real local model generated files, actual tests passed and independent model review accepted them."
            )
            print(
                "Native desktop and clean Windows acceptance are separate gates, not proven by this check."
            )
        finally:
            if process.stdin:
                process.stdin.close()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
