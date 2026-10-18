"""Exercise real packaged backend startup, HTTP auth, bundled unittest and shutdown."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("executable")
args = parser.parse_args()
exe = Path(args.executable).resolve(strict=True)
research_help = subprocess.run([str(exe), "--research", "--help"], capture_output=True, text=True, timeout=30)
if research_help.returncode or "prepare-merge" not in research_help.stdout:
    raise RuntimeError("Packaged experimental preparation command missing: " + research_help.stderr)
print("Packaged research preparation entry point: OK; no training executed")
tools_help = subprocess.run([str(exe), "--project-tools", "--help"], capture_output=True, text=True, timeout=30)
if tools_help.returncode or "approve-setup" not in tools_help.stdout:
    raise RuntimeError("Packaged approved project SDK setup command missing: " + tools_help.stderr)
print("Packaged project SDK entry point: OK; no download requested")
with tempfile.TemporaryDirectory(prefix="stanicode-packaged-smoke-") as directory:
    root = Path(directory)
    project = root / "project"
    project.mkdir()
    (project / "maths.py").write_text("def add(a,b):\n    return a+b\n")
    (project / "test_maths.py").write_text(
        "import unittest\nfrom maths import add\nclass Maths(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(2,3),5)\n"
    )
    result = subprocess.run(
        [str(exe), "--run-tests", str(project)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode or "Ran 1 test" not in result.stderr:
        raise RuntimeError(result.stdout + result.stderr)
    print("Packaged interpreter: project test executed successfully")
    server = subprocess.Popen(
        [
            str(exe),
            "--data",
            str(root / "state"),
            "--bundle",
            str(root / "absent-model"),
            "--parent-stdin",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        session = json.loads(server.stdout.readline())
        url = f"http://127.0.0.1:{session['port']}/health"
        req = urllib.request.Request(
            url, headers={"Authorization": "Bearer " + session["token"]}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.load(response)
            assert data["backend"] is True and data["inference"]["ready"] is False
        print("Authenticated backend health: OK; missing model does not report ready")
        server.stdin.close()
        server.wait(timeout=10)
        if server.returncode:
            raise RuntimeError(server.stderr.read())
        print("Parent-close shutdown: OK")
    finally:
        if server.poll() is None:
            server.kill()
            server.wait()
