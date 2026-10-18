"""Prepare Debian 13 native build dependencies under /workspace, without root installs."""

from pathlib import Path
import subprocess

root = Path("/workspace/.stanicode-tools")
apt = root / "apt"
sysroot = root / "linux-sysroot"
if (sysroot / "usr/lib/x86_64-linux-gnu/pkgconfig/webkit2gtk-4.1.pc").exists():
    print("Retained native dependency sysroot is present; source scripts/native_env.sh")
    raise SystemExit(0)
if "Debian GNU/Linux 13" not in Path("/etc/os-release").read_text():
    raise RuntimeError("This helper is specific to the observed Debian 13 cloud image")
for name in ("lists/partial", "archives/partial"):
    (apt / name).mkdir(parents=True, exist_ok=True)
(apt / "sources.list").write_text(
    "deb https://deb.debian.org/debian trixie main\ndeb https://deb.debian.org/debian trixie-updates main\ndeb https://deb.debian.org/debian-security trixie-security main\n"
)
options = [
    "-o",
    "Dir::Etc::sourcelist=" + str(apt / "sources.list"),
    "-o",
    "Dir::Etc::sourceparts=-",
    "-o",
    "Dir::State::lists=" + str(apt / "lists"),
    "-o",
    "Dir::Cache::archives=" + str(apt / "archives"),
    "-o",
    "Acquire::Retries=0",
]
# Signature and package checksum verification remain enabled. No dpkg installation runs.
subprocess.run(
    ["/usr/bin/apt-get", *options, "-o", "APT::Update::Error-Mode=any", "update"],
    check=True,
)
subprocess.run(
    [
        "/usr/bin/apt-get",
        *options,
        "-o",
        "Debug::NoLocking=1",
        "--download-only",
        "--no-install-recommends",
        "-y",
        "install",
        "libwebkit2gtk-4.1-dev",
        "libgtk-3-dev",
        "libayatana-appindicator3-dev",
        "librsvg2-dev",
        "patchelf",
    ],
    check=True,
)
selected = {}
for package in (apt / "archives").glob("*.deb"):
    fields = subprocess.check_output(
        ["dpkg-deb", "-f", str(package), "Package", "Version", "Architecture"],
        text=True,
    )
    metadata = dict(line.split(": ", 1) for line in fields.splitlines())
    identity = (metadata["Package"], metadata["Architecture"])
    version = metadata["Version"]
    previous = selected.get(identity)
    if (
        previous is None
        or subprocess.run(
            ["dpkg", "--compare-versions", version, "gt", previous[0]]
        ).returncode
        == 0
    ):
        selected[identity] = (version, package)
sysroot.mkdir(exist_ok=True)
for version, package in selected.values():
    subprocess.run(["dpkg-deb", "-x", str(package), str(sysroot)], check=True)
for path in list(sysroot.rglob("*")):
    if path.is_symlink() and not path.exists():
        target = path.readlink()
        logical = path.parent / target
        host = (
            target if target.is_absolute() else Path("/") / logical.relative_to(sysroot)
        )
        if host.exists():
            path.unlink()
            path.symlink_to(host)
print("Native dependency sysroot prepared; source scripts/native_env.sh")
