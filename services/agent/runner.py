"""Bounded output and owned process-tree cleanup. This is not a filesystem sandbox."""

from collections import deque
import os
import signal
import subprocess
import threading
import time


def windows_job(process):
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [
            ("process_time", ctypes.c_longlong),
            ("job_time", ctypes.c_longlong),
            ("flags", wintypes.DWORD),
            ("min_working", ctypes.c_size_t),
            ("max_working", ctypes.c_size_t),
            ("active", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", wintypes.DWORD),
            ("scheduling", wintypes.DWORD),
        ]

    class IO(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "read_ops",
                "write_ops",
                "other_ops",
                "read_bytes",
                "write_bytes",
                "other_bytes",
            )
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("basic", Basic),
            ("io", IO),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process", ctypes.c_size_t),
            ("peak_job", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Cannot create validation job")
    info = Extended()
    info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(
        handle, 9, ctypes.byref(info), ctypes.sizeof(info)
    ) or not kernel.AssignProcessToJobObject(
        handle, wintypes.HANDLE(int(process._handle))
    ):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise OSError(error, "Cannot contain validation process tree")
    return lambda: kernel.CloseHandle(handle)


def run(command, cwd, environment, cancel=lambda: False, timeout=30):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name != "nt",
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    cleanup = None
    reader = None
    chunks = deque(maxlen=64)
    seen = [0]
    try:
        if os.name == "nt":
            cleanup = windows_job(process)

        def collect():
            while True:
                chunk = process.stdout.read1(4096)
                if not chunk:
                    return
                chunks.append(chunk)
                seen[0] += len(chunk)

        reader = threading.Thread(target=collect, daemon=True)
        reader.start()
        start = time.monotonic()
        while process.poll() is None:
            if cancel():
                raise InterruptedError("Validation cancelled")
            if time.monotonic() - start > timeout:
                captured = b"".join(chunks.copy())[-4000:].decode("utf-8", errors="replace")
                raise TimeoutError("Validation timed out" + ("\n" + captured if captured else ""))
            time.sleep(0.03)
    finally:
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif cleanup:
            cleanup()
        elif process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        if reader:
            reader.join(timeout=5)
        if not reader or not reader.is_alive():
            process.stdout.close()
    if reader.is_alive():
        raise RuntimeError("Validation output pipe did not close")
    output = b"".join(chunks).decode("utf-8", errors="replace")
    if seen[0] > len(output.encode()):
        output = "[Earlier output truncated]\n" + output
    return process.returncode, output
