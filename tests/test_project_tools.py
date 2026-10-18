"""Provisioning safeguards use labeled non-executable SDK fixtures."""

import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/agent'))
import project_tools
from engine import Workspace, Engine, Store
from server import make_server


class ProjectToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = project_tools.ProjectTools(self.root / 'managed tools')
        self.tools.supported = True  # Pure provisioning fixture, not Windows execution evidence.
        self.environment = {'PATH': os.environ.get('PATH', '')}

    def archive(self, traversal=False):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as package:
            prefix = project_tools.DIRECTORY + '/'
            for name, value in {'node.exe': b'non-executable fixture', 'LICENSE': b'fixture-only license',
                                'node_modules/npm/bin/npm-cli.js': b'fixture-only source'}.items():
                package.writestr(prefix + name, value)
            if traversal:
                package.writestr(prefix + '../outside.txt', b'bad')
        return stream.getvalue()

    def install_fixture(self, data=None):
        data = data or self.archive()
        approval = self.tools.propose()['approval_id']
        with patch.object(project_tools, 'SHA256', hashlib.sha256(data).hexdigest()), \
             patch.object(project_tools.urllib.request, 'urlopen', return_value=io.BytesIO(data)), \
             patch.object(project_tools, 'verify_publisher', return_value='unit-test signature fixture'), \
             patch.object(project_tools.runner, 'run', return_value=(0, 'v' + project_tools.VERSION)):
            result = self.tools.install(approval, self.environment)
            self.assertTrue(self.tools.verify_installed())
            return result

    def test_missing_expired_and_replayed_approval_do_not_download(self):
        with patch.object(project_tools.urllib.request, 'urlopen') as download:
            with self.assertRaisesRegex(ValueError, 'approval'):
                self.tools.install('missing', self.environment)
            proposal = self.tools.propose()
            self.tools.expires = 0
            with self.assertRaisesRegex(ValueError, 'approval'):
                self.tools.install(proposal['approval_id'], self.environment)
            download.assert_not_called()
        self.assertFalse(self.tools.root.exists())
        self.install_fixture()
        with self.assertRaisesRegex(ValueError, 'approval'):
            self.tools.install(proposal['approval_id'], self.environment)

    def test_changed_download_cannot_be_executed(self):
        approval = self.tools.propose()['approval_id']
        with patch.object(project_tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad')), \
             patch.object(project_tools, 'verify_publisher') as signature:
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.tools.install(approval, self.environment)
            signature.assert_not_called()
        self.assertFalse((self.tools.root / 'node').exists())

    def test_archive_traversal_is_rejected_before_extraction(self):
        source = self.root / 'bad.zip'
        source.write_bytes(self.archive(traversal=True))
        destination = self.root / 'extract'
        destination.mkdir()
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            project_tools.extract(source, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_verified_install_is_private_and_tampering_is_detected(self):
        original_path = os.environ.get('PATH')
        result = self.install_fixture()
        self.assertTrue(result['installed'])
        self.assertEqual(os.environ.get('PATH'), original_path)
        environment = self.tools.environment(self.environment)
        self.assertEqual(environment['PATH'].split(os.pathsep)[0], str(self.tools.root / 'node'))
        (self.tools.root / 'node/node.exe').write_bytes(b'changed')
        fixture_hash = json.loads((self.tools.root / 'node-installation.json').read_text())['archive_sha256']
        with patch.object(project_tools, 'SHA256', fixture_hash), self.assertRaisesRegex(ValueError, 'checksum'):
            self.tools.verify_installed()

    def test_unknown_existing_directory_is_preserved(self):
        directory = self.tools.root / 'node'
        directory.mkdir(parents=True)
        (directory / 'keep.txt').write_text('keep')
        approval = self.tools.propose()['approval_id']
        with patch.object(project_tools.urllib.request, 'urlopen') as download:
            with self.assertRaisesRegex(ValueError, 'unmanaged'):
                self.tools.install(approval, self.environment)
            download.assert_not_called()
        self.assertEqual((directory / 'keep.txt').read_text(), 'keep')

    def test_failed_repair_does_not_activate_a_known_corrupt_sdk(self):
        self.install_fixture()
        manifest = json.loads((self.tools.root / 'node-installation.json').read_text())
        (self.tools.root / 'node/node.exe').write_bytes(b'changed')
        approval = self.tools.propose()['approval_id']
        with patch.object(project_tools, 'SHA256', manifest['archive_sha256']), \
             patch.object(project_tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad')):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.tools.install(approval, self.environment)
        self.assertFalse(self.tools.installed)
        self.assertEqual(self.tools.environment(self.environment), self.environment)

    def test_common_toolchain_credential_files_are_not_workspace_context(self):
        workspace = Workspace(self.root)
        for name in ('.npmrc', '.pypirc', '.netrc', '.git-credentials', '.kube/config', 'id_ed25519'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Protected'):
                workspace.path(name)

    def test_sdk_api_requires_authentication_and_refuses_active_tasks(self):
        engine = Engine(Store(self.root / 'tasks.sqlite3'), object(), self.tools)
        server = make_server(engine, 'fixture-only-token', SimpleNamespace(status={'ready': False}), project_tools=self.tools)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(path, body, authorized=True):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                headers = {'Content-Type': 'application/json'}
                if authorized:
                    headers['Authorization'] = 'Bearer fixture-only-token'
                connection.request('POST', path, json.dumps(body), headers)
                response = connection.getresponse()
                result = (response.status, json.loads(response.read()))
                connection.close()
                return result
            self.assertEqual(request('/project-tools/node/propose', {}, False)[0], 401)
            self.assertIsNone(self.tools.nonce)
            self.assertEqual(request('/project-tools/node/install', {'approval_id': 'wrong'})[0], 400)
            engine.tasks['fixture'] = {'state': 'running'}
            self.assertEqual(request('/project-tools/node/propose', {})[0], 400)
            self.assertFalse(self.tools.root.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
