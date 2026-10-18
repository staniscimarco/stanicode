"""Optional local Git recovery refs; never modifies the user's index or pushes."""

from pathlib import Path
import shutil
import subprocess
import tempfile


def create(workspace, paths, task_id, environment):
    root = Path(workspace)
    if (
        not (root / ".git").is_dir()
        or (root / ".git").is_symlink()
        or not shutil.which("git")
    ):
        return None
    with tempfile.TemporaryDirectory(prefix="stanicode-index-") as temp:
        env = {
            **environment,
            "GIT_INDEX_FILE": str(Path(temp) / "index"),
            "GIT_AUTHOR_NAME": "STANICODE",
            "GIT_AUTHOR_EMAIL": "local@stanicode.invalid",
            "GIT_COMMITTER_NAME": "STANICODE",
            "GIT_COMMITTER_EMAIL": "local@stanicode.invalid",
        }

        def git(*args, input=None, check=True):
            return subprocess.run(
                ["git", "-c", "core.hooksPath=", "-c", "core.fsmonitor=false", *args],
                cwd=root,
                env=env,
                input=input,
                text=True,
                capture_output=True,
                check=check,
                timeout=15,
            )

        head = git("rev-parse", "--verify", "HEAD", check=False)
        if head.returncode == 0:
            git("read-tree", "HEAD")
        else:
            git("read-tree", "--empty")
        existing = [p for p in paths if (root / p).is_file()]
        if existing:
            git("add", "--", *existing)
        tree = git("write-tree").stdout.strip()
        args = ["commit-tree", tree]
        if head.returncode == 0:
            args += ["-p", head.stdout.strip()]
        commit = git(
            *args, input="STANICODE local recovery checkpoint\n"
        ).stdout.strip()
        git("update-ref", "refs/stanicode/" + task_id, commit)
        return commit
