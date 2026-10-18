"""Container/integrity unit fixtures are not real Windows executables or models."""

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_portable import build, windows_x64
from verify_bundle import verify


class Packaging(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / "payload"
        self.models = self.payload / "models"
        self.models.mkdir(parents=True)
        # Deliberately minimal PE-header fixture: validates packaging logic only, cannot execute.
        data = bytearray(80)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:70] = b"PE\0\0\x64\x86"
        self.pe = bytes(data)
        for path in (
            self.root / "app.exe",
            self.payload / "stanicode-agent.exe",
            self.models / "runtime.exe",
        ):
            path.write_bytes(self.pe)
        (self.models / "model.gguf").write_bytes(b"GGUF unit-test fixture, not a model")
        (self.models / "LICENSE.txt").write_text("Unit-test fixture license")

        def entry(name):
            return {
                "file": name,
                "sha256": hashlib.sha256((self.models / name).read_bytes()).hexdigest(),
                "source": "urn:stanicode:unit-test-fixture",
                "version": "fixture-only",
                "license": "fixture-only",
                "license_file": "LICENSE.txt",
            }

        self.manifest = {
            "runtime": entry("runtime.exe"),
            "model": {**entry("model.gguf"), "minimum_available_ram_bytes": 1},
        }
        (self.models / "manifest.json").write_text(json.dumps(self.manifest))
        webview = self.payload / "webview2"
        webview.mkdir()
        (webview / "msedgewebview2.exe").write_bytes(self.pe)
        (webview / "LICENSE.txt").write_text("Fixture only")
        wm = {
            "version": "fixture-only",
            "source": "urn:fixture",
            "license_file": "LICENSE.txt",
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in webview.iterdir()
            },
        }
        (webview / "webview2-manifest.json").write_text(json.dumps(wm))
        for name in ("THIRD_PARTY_NOTICES.md", "LICENSE"):
            (self.payload / name).write_text("Fixture only")
        (self.payload / "dependency-licenses").mkdir()
        text = b"Unit-test fixture license; no real software payload"
        (self.payload / "dependency-licenses/fixture.txt").write_bytes(text)
        (self.payload / "SBOM.cdx.json").write_text(
            json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.5",
                    "version": 1,
                    "components": [{
                        "bom-ref": "fixture-only", "name": "non-executable unit fixture", "version": "0",
                        "properties": [{"name": "stanicode:license-files", "value": json.dumps([{"file": "dependency-licenses/fixture.txt", "sha256": hashlib.sha256(text).hexdigest()}])}],
                    }],
                }
            )
        )

    def test_non_windows_binary_is_rejected(self):
        file = self.root / "linux"
        file.write_bytes(b"ELF, not PE")
        with self.assertRaisesRegex(ValueError, "Not a Windows"):
            windows_x64(file)

    def test_empty_dependency_inventory_blocks_distribution(self):
        (self.payload / "SBOM.cdx.json").write_text(json.dumps({"bomFormat": "CycloneDX", "components": []}))
        with self.assertRaisesRegex(ValueError, "populated CycloneDX"):
            build(self.root / "app.exe", self.payload, self.root / "output.zip")

    def test_changed_dependency_license_blocks_distribution(self):
        (self.payload / "dependency-licenses/fixture.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "license integrity"):
            build(self.root / "app.exe", self.payload, self.root / "output.zip")

    def test_changed_model_hash_is_rejected(self):
        (self.models / "model.gguf").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify(self.models)

    def test_unverified_companion_is_rejected(self):
        (self.models / "unknown.dll").write_bytes(self.pe)
        with self.assertRaisesRegex(ValueError, "Unverified runtime companion"):
            verify(self.models)

    def test_webview_missing_file_blocks_assembly(self):
        (self.payload / "webview2" / "msedgewebview2.exe").unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.root / "app.exe", self.payload, self.root / "output.zip")
        self.assertFalse((self.root / "output.zip").exists())

    def test_fixture_archive_layout_and_checksums(self):
        output = build(
            self.root / "app.exe", self.payload, self.root / "fixture-candidate.zip"
        )
        with zipfile.ZipFile(output) as archive:
            self.assertIn("STANICODE/STANICODE.exe", archive.namelist())
            self.assertIn("STANICODE/payload/models/model.gguf", archive.namelist())
            self.assertIsNone(archive.testzip())
            for line in archive.read("STANICODE/SHA256SUMS.txt").decode().splitlines():
                digest, name = line.split("  ", 1)
                self.assertEqual(
                    hashlib.sha256(archive.read("STANICODE/" + name)).hexdigest(),
                    digest,
                )
        self.assertTrue(output.with_suffix(".zip.sha256").exists())


if __name__ == "__main__":
    unittest.main()
