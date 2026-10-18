"""Authenticated loopback HTTP API for the native desktop shell."""

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit, parse_qs
import validation
from resources import diagnostics
from engine import Engine, LlamaModel, Store
from runtime import Runtime

ALLOWED_ORIGINS = {
    "http://localhost:1420",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
}


def make_server(engine, token, runtime, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, code, body):
            payload = json.dumps(body).encode()
            self.send_response(code)
            origin = self.headers.get("Origin")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.respond(403, {"error": "Invalid host"})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in ALLOWED_ORIGINS:
                self.respond(403, {"error": "Invalid origin"})
                return False
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + token
            ):
                self.respond(401, {"error": "Unauthorized"})
                return False
            return True

        def do_OPTIONS(self):
            if self.headers.get("Origin") not in ALLOWED_ORIGINS:
                self.respond(403, {"error": "Invalid origin"})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers", "Authorization, Content-Type"
            )
            self.end_headers()

        def do_GET(self):
            if not self.allowed():
                return
            url = urlsplit(self.path)
            if url.path == "/health":
                self.respond(
                    200,
                    {
                        "backend": True,
                        "inference": runtime.status,
                        "validation_recipes": validation.tools(),
                        "resources": diagnostics(),
                    },
                )
            elif self.path == "/tasks":
                tasks = engine.store.history()
                for t in tasks:
                    c = engine.controls.get(t["id"])
                    t["approval_id"] = (
                        c["approval_id"]
                        if c and t["state"] == "awaiting_approval"
                        else None
                    )
                    t["pending"] = (
                        c["pending"]
                        if c and t["state"] == "awaiting_approval"
                        else None
                    )
                self.respond(200, tasks)
            elif url.path == "/memory":
                self.respond(
                    200, engine.memory.search(parse_qs(url.query).get("query", [""])[0])
                )
            else:
                self.respond(404, {"error": "Not found"})

        def do_POST(self):
            if not self.allowed():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 65536:
                    raise ValueError("Request too large")
                body = json.loads(self.rfile.read(length))
                if self.path == "/tasks":
                    if not runtime.status["ready"]:
                        raise ValueError(
                            "Local inference is unavailable: "
                            + runtime.status["detail"]
                        )
                    task = engine.create(body["workspace"], body["prompt"])
                    self.respond(201, {"id": task["id"]})
                    return
                if self.path == "/memory/delete":
                    engine.memory.delete()
                    self.respond(200, {"ok": True})
                    return
                if self.path == "/control":
                    engine.control(body["id"], body["action"], body.get("approval_id"))
                elif self.path == "/rollback":
                    engine.rollback(body["id"])
                else:
                    self.respond(404, {"error": "Not found"})
                    return
                self.respond(200, {"ok": True})
            except (KeyError, ValueError, TypeError) as e:
                self.respond(400, {"error": str(e)})
            except Exception:
                self.respond(
                    500, {"error": "Local operation failed; inspect local diagnostics"}
                )

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--run-tests":
        from test_runner import run

        raise SystemExit(run(sys.argv[2]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-stdin", action="store_true")
    parser.add_argument("--data", default=str(Path.home() / ".stanicode"))
    parser.add_argument(
        "--bundle", default=str(Path(__file__).resolve().parents[2] / "models")
    )
    args = parser.parse_args()
    runtime = Runtime(args.bundle, Path(args.data) / "inference.log")
    engine = Engine(
        Store(Path(args.data) / "tasks.sqlite3"),
        LlamaModel(
            endpoint=runtime.endpoint,
            api_key=runtime.api_key,
            metadata=lambda: runtime.provenance,
        ),
    )
    token = secrets.token_urlsafe(32)
    server = make_server(engine, token, runtime)
    print(json.dumps({"port": server.server_port, "token": token}), flush=True)
    threading.Thread(target=runtime.start, daemon=True).start()
    if args.parent_stdin:

        def parent_watch():
            import sys

            sys.stdin.buffer.read()
            for control in engine.controls.values():
                control["cancel"] = True
            for worker in engine.workers.values():
                worker.join(timeout=3)
            runtime.stop()
            server.shutdown()

        threading.Thread(target=parent_watch, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        runtime.stop()
        server.server_close()


if __name__ == "__main__":
    main()
