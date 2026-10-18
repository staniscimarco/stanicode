"""Verify the same offline-payload contract used by the packaged application."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "agent"))
from bundle import verify as verify

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    manifest = verify(parser.parse_args().bundle)
    for name in ("runtime", "model"):
        print(
            name
            + ": verified "
            + manifest[name]["file"]
            + " / "
            + manifest[name]["version"]
        )
