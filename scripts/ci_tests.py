"""Run actual suites and expose actionable failure details as GitHub check annotations."""

from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
for test, trace in [*result.errors, *result.failures]:
    message = (str(test) + "\n" + trace)[-10000:]
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::error title=Python test failure::" + message, flush=True)
if result.testsRun == 0:
    print("::error::No tests executed", flush=True)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
