"""Fixed validation recipes. Approval is required: project code is not sandboxed."""

from pathlib import Path
import re
import shutil
import sys

RECIPES = ("python-unittest", "node-test", "npm-test", "cargo-test")


def tools():
    return {
        "python-unittest": True,
        "node-test": bool(shutil.which("node")),
        "npm-test": bool(shutil.which("npm")),
        "cargo-test": bool(shutil.which("cargo")),
    }


def command(recipe, root):
    root = Path(root)
    if recipe not in RECIPES:
        raise ValueError("Unsupported validation recipe")
    if recipe == "python-unittest":
        result = [sys.executable]
        if not getattr(sys, "frozen", False):
            result.append(str(Path(__file__).with_name("server.py")))
        return result + ["--run-tests", str(root)]
    executable = {"node-test": "node", "npm-test": "npm", "cargo-test": "cargo"}[recipe]
    path = shutil.which(executable)
    if not path:
        raise ValueError(
            f"{executable} is required by this project and is not installed; STANICODE can still run"
        )
    if recipe == "node-test":
        return [path, "--test", "--test-reporter=tap"]
    if recipe == "npm-test":
        return [path, "test", "--offline", "--ignore-scripts=false"]
    return [path, "test", "--offline", "--jobs", "2"] + (
        ["--locked"] if (root / "Cargo.lock").exists() else []
    )


def passed(recipe, code, output):
    if code != 0:
        return False
    if recipe == "python-unittest":
        counts = re.findall(r"Ran (\d+) tests?", output)
        return bool(
            counts and int(counts[-1]) > 0 and re.search(r"^OK(?:\s|$)", output, re.M)
        )
    if recipe == "node-test":
        counts = re.findall(r"^# tests (\d+)", output, re.M)
        return bool(
            counts and int(counts[-1]) > 0 and re.search(r"^# fail 0$", output, re.M)
        )
    if recipe == "cargo-test":
        counts = re.findall(r"test result: ok\. (\d+) passed", output)
        return bool(counts and sum(map(int, counts)) > 0)
    # A project-defined npm script is an executed check; no test count is asserted.
    return True
