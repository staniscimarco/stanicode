"""Explicitly approved per-user project SDK provisioning; never required by core AI."""

import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
import runner

VERSION = '24.19.0'
DIRECTORY = f'node-v{VERSION}-win-x64'
DESTINATION = 'node'
SOURCE = f'https://nodejs.org/dist/v{VERSION}/{DIRECTORY}.zip'
SHA256 = '57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73'
OWNER = 'STANICODE-managed-project-tools'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_publisher(path, environment):
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    # The filename is passed through a dedicated environment entry, not code.
    code = "$ErrorActionPreference='Stop'; $s=Get-AuthenticodeSignature -LiteralPath $env:STANICODE_SIGNATURE_FILE; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'OpenJS Foundation') { throw 'Invalid Node.js publisher signature' }; $s.SignerCertificate.Subject"
    status, output = runner.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', code],
                                path.parent, {**environment, 'STANICODE_SIGNATURE_FILE': str(path)}, timeout=60)
    if status:
        raise ValueError('Node.js publisher signature verification failed')
    return output.strip()


def extract(archive, destination):
    with zipfile.ZipFile(archive) as package:
        if sum(item.file_size for item in package.infolist()) > 512 * 1024**2:
            raise ValueError('Project SDK extraction exceeds its disk budget')
        for item in package.infolist():
            relative = PurePosixPath(item.filename)
            if (relative.is_absolute() or '..' in relative.parts or '\\' in item.filename
                    or ':' in item.filename or not relative.parts or relative.parts[0] != DIRECTORY
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe path in project SDK archive')
        package.extractall(destination)
    return Path(destination) / DIRECTORY


class ProjectTools:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.supported = os.name == 'nt'
        self.lock = threading.Lock()
        self.nonce = None
        self.expires = 0
        self.busy = False
        self.phase = 'not-installed'
        self.error = ''
        self.installed = False
        if self.supported:
            try:
                self.installed = self.verify_installed()
                if self.installed:
                    self.phase = 'installed'
            except (OSError, ValueError, KeyError, TypeError):
                self.error = 'Managed Node.js integrity check failed; approved repair is required'

    def verify_installed(self):
        manifest_path = self.root / 'node-installation.json'
        if not manifest_path.is_file():
            return False
        if manifest_path.stat().st_size > 20_000_000:
            raise ValueError('Invalid project SDK manifest')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if (manifest.get('owner') != OWNER or manifest.get('directory') != DESTINATION
                or manifest.get('archive_sha256') != SHA256 or not manifest.get('files')):
            raise ValueError('Invalid project SDK provenance')
        directory = self.root / DESTINATION
        for name, expected in manifest['files'].items():
            path = (directory / name).resolve(strict=True)
            if not path.is_relative_to(directory.resolve()) or digest(path) != expected:
                raise ValueError('Managed project SDK file checksum mismatch')
        if not {'node.exe', 'LICENSE', 'node_modules/npm/bin/npm-cli.js'}.issubset(manifest['files']):
            raise ValueError('Incomplete project SDK')
        actual = {path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()}
        if actual != set(manifest['files']):
            raise ValueError('Unmanifested files in managed project SDK')
        return True

    @property
    def status(self):
        return {'supported': self.supported, 'installed': self.installed,
                'version': VERSION, 'phase': self.phase, 'error': self.error,
                'source': SOURCE, 'destination': str(self.root / DESTINATION), 'busy': self.busy}

    def environment(self, environment):
        result = dict(environment)
        directory = self.root / DESTINATION
        if self.installed and (directory / 'node.exe').is_file():
            result['PATH'] = str(directory) + os.pathsep + result.get('PATH', '')
        return result

    def propose(self):
        if not self.supported:
            raise ValueError('Automatic project Node.js setup is supported on Windows x64')
        with self.lock:
            if self.busy:
                raise ValueError('Project SDK setup is already running')
            self.nonce = secrets.token_urlsafe(32)
            self.expires = time.monotonic() + 300
            return {**self.status, 'approval_id': self.nonce, 'sha256': SHA256,
                    'operation': 'Download verified official Node.js and npm into private application data; no administrator or global PATH changes'}

    def install(self, approval_id, environment):
        with self.lock:
            if (not isinstance(approval_id, str) or not self.nonce
                    or not hmac.compare_digest(approval_id, self.nonce) or time.monotonic() > self.expires):
                raise ValueError('Missing, expired or stale project SDK approval')
            if self.busy or not self.supported:
                raise ValueError('Project SDK setup unavailable')
            self.nonce = None
            self.busy = True
        try:
            try:
                valid = self.verify_installed()
            except (OSError, ValueError, KeyError, TypeError):
                valid = False
            if valid:
                self.installed = True
                self.phase = 'installed'
                return {**self.status, 'busy': False}
            self.installed = False
            self.root.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(self.root).free < 1024**3:
                raise ValueError('At least 1 GiB free disk is required for approved project SDK setup')
            destination = self.root / DESTINATION
            if destination.exists():
                old_manifest = self.root / 'node-installation.json'
                if old_manifest.is_file() and old_manifest.stat().st_size > 20_000_000:
                    raise ValueError('Existing oversized SDK manifest preserved')
                old = json.loads(old_manifest.read_text()) if old_manifest.is_file() else {}
                if old.get('owner') != OWNER or old.get('directory') != DESTINATION:
                    raise ValueError('Existing unmanaged SDK directory preserved; choose a different application data directory')
            with tempfile.TemporaryDirectory(prefix='approved-node-', dir=self.root, ignore_cleanup_errors=True) as directory:
                temporary = Path(directory)
                archive = temporary / 'node.zip'
                self.phase, self.error = 'downloading', ''
                try:
                    with urllib.request.urlopen(SOURCE, timeout=60) as source, archive.open('wb') as output:
                        size = 0
                        started = time.monotonic()
                        while data := source.read(1024 * 1024):
                            size += len(data)
                            if size > 160 * 1024**2 or time.monotonic() - started > 300:
                                raise ValueError('Project SDK download exceeded its bounded size/time budget')
                            output.write(data)
                except (urllib.error.URLError, TimeoutError) as error:
                    raise ValueError('Node.js download failed; Internet access is required for this approved setup') from error
                self.phase = 'verifying'
                if digest(archive) != SHA256:
                    raise ValueError('Node.js archive SHA-256 verification failed')
                node = extract(archive, temporary)
                publisher = verify_publisher(node / 'node.exe', environment)
                code, output = runner.run([str(node / 'node.exe'), '--version'], node, environment, timeout=30)
                if code or output.strip() != 'v' + VERSION:
                    raise ValueError('Verified Node.js runtime did not start correctly')
                self.phase = 'installing'
                files = {path.relative_to(node).as_posix(): digest(path) for path in node.rglob('*') if path.is_file()}
                if not {'node.exe', 'LICENSE', 'node_modules/npm/bin/npm-cli.js'}.issubset(files):
                    raise ValueError('Official Node.js distribution is incomplete')
                backup = None
                if destination.exists():
                    backup = self.root / (DESTINATION + '-backup-' + secrets.token_hex(4))
                    destination.rename(backup)
                try:
                    node.rename(destination)
                except OSError:
                    if backup and not destination.exists():
                        backup.rename(destination)
                    raise
                manifest = {'owner': OWNER, 'directory': DESTINATION, 'version': VERSION,
                            'source': SOURCE, 'archive_sha256': SHA256, 'publisher': publisher, 'files': files}
                pending = self.root / 'node-installation.json.pending'
                pending.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
                pending.replace(self.root / 'node-installation.json')
            self.installed = self.verify_installed()
            self.phase = 'installed'
            return {**self.status, 'busy': False}
        except Exception:
            self.phase = 'failed'
            self.error = 'Project SDK setup failed; the core local AI remains available'
            raise
        finally:
            self.busy = False
