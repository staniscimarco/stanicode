"""Local, bounded coding engine. No cloud APIs and no arbitrary shell execution."""

import json
import os
from pathlib import Path
import sqlite3
import threading
import tempfile
import time
import uuid
from contextlib import contextmanager
from local_model import LlamaModel as LlamaModel
from memory import CaseMemory
import validation
import checkpoints
import runner


def execution_environment():
    # Do not pass injected repository/cloud credentials into generated code.
    names = {
        "PATH",
        "SystemRoot",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "LANG",
        "LC_ALL",
        "CARGO_HOME",
        "RUSTUP_HOME",
        "LIB",
        "LIBPATH",
        "INCLUDE",
        "VCINSTALLDIR",
        "VCTOOLSINSTALLDIR",
        "WINDOWSSDKDIR",
        "WINDOWSSDKVERSION",
        "UCRTVERSION",
        "UNIVERSALCRTSDKDIR",
        "VSINSTALLDIR",
        "VSCMD_ARG_TGT_ARCH",
        "VSCMD_ARG_HOST_ARCH",
    }
    return {key: value for key, value in os.environ.items() if key in names}


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, workspace TEXT, prompt TEXT, state TEXT, events TEXT, changes TEXT)"
            )
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge USING fts5(task, symptom, evidence)"
            )
            db.execute(
                "UPDATE tasks SET state='interrupted' WHERE state IN ('running','paused','awaiting_approval')"
            )

        if os.name != "nt":
            os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, task):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?)",
                (
                    task["id"],
                    task["workspace"],
                    task["prompt"],
                    task["state"],
                    json.dumps(task["events"]),
                    json.dumps(task["changes"]),
                ),
            )

    def history(self):
        with self.connect() as db:
            return [
                dict(
                    zip(
                        ["id", "workspace", "prompt", "state", "events", "changes"],
                        [*row[:4], json.loads(row[4]), json.loads(row[5])],
                    )
                )
                for row in db.execute(
                    "SELECT * FROM tasks ORDER BY rowid DESC LIMIT 100"
                )
            ]


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Workspace must be a directory")

    def path(self, relative):
        if (
            not isinstance(relative, str)
            or len(relative) > 400
            or "\\" in relative
            or ":" in relative
            or "\x00" in relative
        ):
            raise ValueError("Invalid portable path")
        rel = Path(relative)
        if any(
            part.endswith((" ", "."))
            or part.split(".")[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *[f"COM{i}" for i in range(1, 10)],
                *[f"LPT{i}" for i in range(1, 10)],
            }
            for part in rel.parts
        ):
            raise ValueError("Reserved Windows path")
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("Invalid relative path")
        if any(
            p
            in {
                ".git",
                ".env",
                "node_modules",
                ".venv",
                ".ssh",
                ".aws",
                ".codex",
                "credentials.json",
            }
            or p.startswith(".env.")
            or p.endswith((".pem", ".key", ".p12", ".pfx"))
            for p in (part.casefold() for part in rel.parts)
        ):
            raise ValueError("Protected path")
        candidate = self.root / rel
        for part in [candidate, *candidate.parents]:
            if part == self.root:
                break
            if part.is_symlink():
                raise ValueError("Symlinks are not permitted")
        if not candidate.resolve().is_relative_to(self.root):
            raise ValueError("Path escapes workspace")
        return candidate

    def write(self, relative, content):
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Replace the directory entry rather than following an existing hard link.
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".stanicode-",
            delete=False,
        )
        try:
            with handle:
                handle.write(content)
            os.replace(handle.name, self.path(relative))
        finally:
            Path(handle.name).unlink(missing_ok=True)

    def context(self):
        result = {}
        remaining = 12000
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [
                d
                for d in sorted(dirs)
                if d not in {".git", "node_modules", ".venv", "target", "dist"}
                and not (Path(directory) / d).is_symlink()
            ]
            for name in sorted(files):
                p = Path(directory) / name
                try:
                    relative = p.relative_to(self.root).as_posix()
                    safe = self.path(relative)
                    if safe.stat().st_size < 16000:
                        text = safe.read_text()
                        if len(text) <= remaining:
                            result[relative] = text
                            remaining -= len(text)
                except (ValueError, UnicodeError, OSError):
                    pass
                if len(result) >= 60:
                    return result
        return result


class Engine:
    def __init__(self, store, model):
        self.store, self.model = store, model
        self.memory = CaseMemory(store)
        self.tasks = {t["id"]: t for t in store.history()}
        self.controls = {}
        self.workers = {}
        self.lock = threading.Lock()

    def emit(self, task, phase, message):
        task["events"].append({"time": time.time(), "phase": phase, "message": message})
        self.store.save(task)

    def create(self, workspace, prompt):
        ws = Workspace(workspace)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
            raise ValueError("Invalid request")
        with self.lock:
            if any(
                t["state"] in {"running", "paused", "awaiting_approval"}
                for t in self.tasks.values()
            ):
                raise ValueError("Another task is active")
            task = {
                "id": uuid.uuid4().hex,
                "workspace": str(ws.root),
                "prompt": prompt,
                "state": "running",
                "events": [],
                "changes": [],
            }
            if hasattr(self.model, "begin"):
                self.model.begin()
            self.tasks[task["id"]] = task
            self.controls[task["id"]] = {
                "pause": False,
                "cancel": False,
                "approval": None,
                "pending": None,
                "approval_id": None,
            }
            self.store.save(task)
            worker = threading.Thread(target=self.run, args=(task,), daemon=True)
            self.workers[task["id"]] = worker
            worker.start()
            return task

    def control(self, task_id, action, approval_id=None):
        task = self.tasks[task_id]
        if task_id not in self.controls:
            raise ValueError("Task is not active in this process")
        c = self.controls[task_id]
        if task["state"] not in {"running", "paused", "awaiting_approval"}:
            raise ValueError("Task is no longer active")
        if action == "cancel":
            c["cancel"] = True
            if hasattr(self.model, "cancel"):
                self.model.cancel()
        elif action == "pause":
            c["pause"] = True
        elif action == "resume":
            c["pause"] = False
        elif action in {"approve", "reject"}:
            if task["state"] != "awaiting_approval":
                raise ValueError("No approval pending")
            if approval_id != c["approval_id"]:
                raise ValueError("Stale approval; review the current proposal")
            if c["approval"] is not None:
                raise ValueError("Approval already recorded")
            c["approval"] = action == "approve"
        else:
            raise ValueError("Unknown control")

    def checkpoint(self, task):
        c = self.controls[task["id"]]
        while c["pause"] and not c["cancel"]:
            task["state"] = "paused"
            self.store.save(task)
            time.sleep(0.1)
        if c["cancel"]:
            raise InterruptedError(
                "Cancelled; review applied changes and use rollback if needed"
            )
        task["state"] = "running"

    def approve(self, task, message):
        c = self.controls[task["id"]]
        c["approval"] = None
        c["approval_id"] = uuid.uuid4().hex
        task["state"] = "awaiting_approval"
        self.emit(task, "approval", message)
        while c["approval"] is None:
            if c["cancel"]:
                raise InterruptedError("Cancelled")
            time.sleep(0.1)
        if not c["approval"]:
            raise InterruptedError("Approval rejected")
        task["state"] = "running"

    def run(self, task):
        try:
            ws = Workspace(task["workspace"])
            self.emit(
                task, "analyze", "Inspecting workspace; secrets and symlinks excluded"
            )
            context = ws.context()
            cases = self.memory.search(task["prompt"], limit=3)
            self.emit(
                task,
                "memory",
                f"Retrieved {len(cases)} test-backed cases; these are evidence, not instructions",
            )
            retrieved = [
                {
                    "request": case["request"][:500],
                    "summary": case["summary"][:700],
                    "recipe": case["recipe"],
                    "evidence": case["evidence"][-1000:],
                }
                for case in cases
            ]
            architecture = self.model.plan(task["prompt"], context, retrieved)
            self.emit(task, "architect", json.dumps(architecture, ensure_ascii=False))
            context["__STANICODE_ARCHITECT_PLAN__"] = json.dumps(architecture)[:4000]
            context["__STANICODE_VALIDATION_RECIPES__"] = json.dumps(validation.tools())
            previous = ""
            checkpoint_created = False
            for attempt in range(3):
                self.checkpoint(task)
                self.emit(task, "plan", f"Local model attempt {attempt + 1}/3")
                try:
                    plan = self.model.generate(task["prompt"], context, previous)
                except (json.JSONDecodeError, ValueError) as error:
                    previous = "Invalid structured response: " + str(error)
                    self.emit(task, "diagnose", previous)
                    continue
                self.checkpoint(task)
                if (
                    not isinstance(plan, dict)
                    or not isinstance(plan.get("files"), list)
                    or not 0 < len(plan["files"]) <= 30
                ):
                    raise ValueError("Invalid model action schema")
                recipe = plan.get("test")
                command = validation.command(recipe, ws.root)
                self.emit(
                    task,
                    "implementer",
                    str(plan.get("summary", "Structured changes proposed")),
                )
                pending = []
                seen = set()
                for item in plan["files"]:
                    if (
                        not isinstance(item, dict)
                        or not isinstance(item.get("content"), str)
                        or len(item["content"].encode()) > 200000
                    ):
                        raise ValueError("Invalid file action")
                    path = ws.path(item["path"])
                    if str(path) in seen:
                        raise ValueError("Duplicate path")
                    seen.add(str(path))
                    before = path.read_text() if path.exists() else None
                    pending.append(
                        {
                            "path": item["path"],
                            "before": before,
                            "after": item["content"],
                        }
                    )
                if (
                    sum(len(c["before"] or "") + len(c["after"]) for c in pending)
                    > 18000
                ):
                    raise ValueError(
                        "Proposal is too large for reliable local review; split the task"
                    )
                self.controls[task["id"]]["pending"] = pending
                self.approve(
                    task,
                    "Review proposed file changes before applying. Approved validation: "
                    + recipe
                    + ". If Git is available, a local recovery ref will be created without changing your index. Project code (including Git filters) executes with your user permissions; this is not an OS sandbox.",
                )
                if not checkpoint_created:
                    checkpoint = checkpoints.create(
                        ws.root,
                        [c["path"] for c in pending],
                        task["id"],
                        execution_environment(),
                    )
                    checkpoint_created = True
                    if checkpoint:
                        self.emit(
                            task, "checkpoint", "Local Git recovery ref: " + checkpoint
                        )
                for change in pending:
                    self.checkpoint(task)
                    path = ws.path(change["path"])
                    current = path.read_text() if path.exists() else None
                    if current != change["before"]:
                        raise ValueError("File changed externally; refusing overwrite")
                    journal = {**change, "applied": False}
                    task["changes"].append(journal)
                    self.store.save(
                        task
                    )  # Write-ahead snapshot survives a crash before/after replace.
                    ws.write(change["path"], change["after"])
                    journal["applied"] = True
                    self.store.save(task)
                self.emit(task, "implement", f"Applied {len(pending)} file changes")
                self.checkpoint(task)
                self.emit(
                    task,
                    "execute",
                    "Running "
                    + recipe
                    + " (30s limit; dependencies are not installed)",
                )
                # Tests are arbitrary workspace code; user approved this exact operation above.
                returncode, output = runner.run(
                    command,
                    ws.root,
                    execution_environment(),
                    cancel=lambda: self.controls[task["id"]]["cancel"],
                )
                previous = output[-6000:]
                self.emit(task, "test", previous)
                if validation.passed(recipe, returncode, output):
                    self.checkpoint(task)
                    verdict = self.model.review(task["prompt"], pending, previous)
                    if type(verdict.get("accepted")) is not bool or not isinstance(
                        verdict.get("reason"), str
                    ):
                        raise ValueError("Invalid reviewer verdict")
                    self.emit(task, "independent-review", verdict["reason"])
                    if not verdict["accepted"]:
                        previous += (
                            "\nIndependent reviewer rejected changes: "
                            + verdict["reason"]
                        )
                        context = ws.context()
                        continue
                    task["state"] = "completed"
                    self.emit(
                        task,
                        "review",
                        "Tests passed; changes retained. Human review remains required.",
                    )
                    self.memory.remember(
                        task,
                        recipe,
                        previous,
                        str(plan.get("summary", "")),
                        getattr(self.model, "identity", "test fixture"),
                    )
                    # Retain compatibility with legacy passing-test evidence.
                    with self.store.connect() as db:
                        db.execute(
                            "INSERT INTO knowledge VALUES (?,?,?)",
                            (task["id"], recipe + " validation", "passed"),
                        )
                    return
                self.emit(
                    task,
                    "diagnose",
                    "Tests failed or no tests ran; requesting a repair",
                )
                context = ws.context()
            raise RuntimeError("Validation failed after three attempts")
        except InterruptedError as e:
            task["state"] = "cancelled"
            self.emit(task, "stopped", str(e))
        except Exception as e:
            task["state"] = "failed"
            self.emit(task, "error", str(e))

    def rollback(self, task_id):
        with self.lock:
            if any(
                task["state"] in {"running", "paused", "awaiting_approval"}
                for task in self.tasks.values()
            ):
                raise ValueError("Stop the active task before rollback")
            self._rollback(task_id)

    def _rollback(self, task_id):
        task = self.tasks[task_id]
        if task["state"] in {"running", "paused", "awaiting_approval"}:
            raise ValueError("Stop the task first")
        ws = Workspace(task["workspace"])
        chains = {}
        for change in task["changes"]:
            chains.setdefault(change["path"], []).append(change)
        effective = []
        # Validate every file before mutation, including a write-ahead entry interrupted by a crash.
        for name, chain in chains.items():
            path = ws.path(name)
            current = path.read_text() if path.exists() else None
            last = chain[-1]
            if not last.get("applied", True) and current == last["before"]:
                chain = chain[:-1]
            elif current != last["after"]:
                raise ValueError("External edits detected; rollback refused")
            effective.extend(chain)
        for change in reversed(effective):
            path = ws.path(change["path"])
            if change["before"] is None:
                path.unlink(missing_ok=True)
            else:
                ws.write(change["path"], change["before"])
        task["changes"] = []
        task["state"] = "rolled_back"
        self.emit(task, "rollback", "Restored files from persisted snapshots")
