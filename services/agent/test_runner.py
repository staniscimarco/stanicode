"""Run approved workspace unittest code using the packaged interpreter."""

import os
from pathlib import Path
import sys
import unittest
import tempfile


def run(workspace):
    print("STANICODE unittest: starting approved workspace discovery", file=sys.stderr, flush=True)
    root = Path(workspace).resolve(strict=True)
    os.chdir(root)
    sys.path.insert(0, str(root))
    # Fresh cache path prevents stale bytecode after rapid same-size repair edits.
    cache = tempfile.TemporaryDirectory(prefix="stanicode-test-cache-")
    sys.pycache_prefix = cache.name
    sys.dont_write_bytecode = True
    suite = unittest.defaultTestLoader.discover(
        str(root), pattern="test*.py", top_level_dir=str(root)
    )
    count = suite.countTestCases()
    if count == 0:
        print("No tests discovered", file=sys.stderr)
        cache.cleanup()
        return 2
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    cache.cleanup()
    return 0 if result.wasSuccessful() else 1
