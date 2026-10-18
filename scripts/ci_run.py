"""Preserve command failures and expose their bounded diagnostic tail in CI checks."""

from collections import deque
import subprocess
import sys


def main():
    tail = deque(maxlen=65)
    process = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for line in process.stdout:
        print(line, end="", flush=True)
        tail.append(line)
    status = process.wait()
    if status:
        detail = "".join(tail)[-18000:].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::error title=Build or acceptance failed::" + detail)
    return status


if __name__ == "__main__":
    sys.exit(main())
