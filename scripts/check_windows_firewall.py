"""Exercise the native acceptance firewall rules before multi-GB build work."""

import ast
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    if os.name != "nt":
        raise RuntimeError("Windows Firewall preflight requires Windows")
    # Use the exact acceptance script, without importing optional GUI packages.
    tree = ast.parse(Path("scripts/smoke_native_windows.py").read_text(encoding="utf-8"))
    source = next(ast.literal_eval(node.args[0]) for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == "write_text" and isinstance(node.func.value, ast.Name)
                  and node.func.value.id == "rules")
    curl = Path(os.environ["SystemRoot"]) / "System32" / "curl.exe"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"loopback-ok")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    class MappedServer(ThreadingHTTPServer):
        address_family = socket.AF_INET6

        def server_bind(self):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

    mapped = MappedServer(("::ffff:127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    mapped_thread = threading.Thread(target=mapped.serve_forever, daemon=True)
    thread.start()
    mapped_thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="stanicode-firewall-") as directory:
            root = Path(directory).resolve()
            rules = root / "rules.ps1"
            rules.write_text(source, encoding="utf-8")
            programs = root / "programs.json"
            # Product rules cover both clients and servers (backend/CDP).
            # Exercise response traffic with the server program blocked too.
            programs.write_text(json.dumps([str(curl), str(Path(sys.executable).resolve())]), encoding="utf-8")
            group = root.name
            command = ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(rules)]
            baseline = subprocess.run([str(curl), "--noproxy", "*", "--fail", "--max-time", "20", "-I", "https://example.com"], capture_output=True)
            if baseline.returncode:
                raise RuntimeError("External HTTPS baseline unavailable; cannot prove firewall blocking")
            try:
                subprocess.run([*command, "add", str(programs), group], check=True)
                local = subprocess.run([str(curl), "--noproxy", "*", "--fail", "--max-time", "10", f"http://127.0.0.1:{server.server_port}"], capture_output=True)
                if local.returncode or local.stdout != b"loopback-ok":
                    raise AssertionError("Acceptance firewall incorrectly blocks local backend access")
                dual = subprocess.run([str(curl), "--noproxy", "*", "--fail", "--max-time", "10", f"http://127.0.0.1:{mapped.server_port}"], capture_output=True)
                if dual.returncode or dual.stdout != b"loopback-ok":
                    raise AssertionError("Acceptance firewall blocks IPv4-mapped IPv6 loopback responses")
                external = subprocess.run([str(curl), "--noproxy", "*", "--fail", "--max-time", "10", "-I", "https://example.com"], capture_output=True)
                if external.returncode == 0:
                    raise AssertionError("Acceptance firewall did not block external HTTPS")
                print("Actual Windows Firewall: loopback allowed, external HTTPS blocked")
            finally:
                subprocess.run([*command, "remove", str(programs), group], check=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        mapped.shutdown()
        mapped.server_close()
        mapped_thread.join()


if __name__ == "__main__":
    main()
