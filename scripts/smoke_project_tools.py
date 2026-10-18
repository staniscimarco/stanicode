"""Actual Windows official Node provisioning and offline project validation."""

import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/agent'))
from engine import execution_environment
from project_tools import ProjectTools, SOURCE, SHA256, VERSION
import runner
import validation

if os.name != 'nt':
    raise RuntimeError('Actual Windows project SDK acceptance requires Windows')
with tempfile.TemporaryDirectory(prefix='stanicode-tools-', ignore_cleanup_errors=True) as directory:
    root = Path(directory)
    tools = ProjectTools(root / 'managed tools')
    before = os.environ.get('PATH')
    agent = Path('.local/package/stanicode-agent.exe').resolve(strict=True)
    execution = subprocess.run([str(agent), '--project-tools', '--root', str(tools.root), '--approve-setup'],
                               capture_output=True, text=True, timeout=300)
    if execution.returncode:
        raise RuntimeError(execution.stderr)
    result = json.loads(execution.stdout)
    tools = ProjectTools(tools.root)
    if not result['installed'] or os.environ.get('PATH') != before:
        raise AssertionError('Approved private SDK setup changed global process environment or failed')
    environment = tools.environment(execution_environment())
    workspace = root / 'project'
    workspace.mkdir()
    (workspace / 'test.cjs').write_text("const test=require('node:test');const assert=require('node:assert/strict');test('actual managed SDK',()=>assert.equal(2+3,5));\n")
    (workspace / 'package.json').write_text(json.dumps({'scripts': {'test': 'node --test --test-reporter=tap'}}))
    evidence = {'kind': 'actual-approved-windows-node-sdk', 'version': VERSION, 'source': SOURCE,
                'archive_sha256': SHA256, 'global_path_unchanged': True, 'actual_frozen_backend': True, 'recipes': {}}
    for recipe in ('node-test', 'npm-test'):
        command = validation.command(recipe, workspace, environment.get('PATH'))
        if not Path(command[0]).is_relative_to(tools.root):
            raise AssertionError('Installed system Node incorrectly satisfied the SDK probe')
        code, output = runner.run(command, workspace, environment, timeout=60)
        if not validation.passed(recipe, code, output) or 'actual managed SDK' not in output:
            raise RuntimeError(recipe + ': ' + output)
        evidence['recipes'][recipe] = {'command': command, 'exit_code': code, 'output': output}
    import pefile
    with pefile.PE(str(tools.root / 'node/node.exe')) as binary:
        if binary.FILE_HEADER.Machine != 0x8664:
            raise AssertionError('Official project SDK is not x64')
        imports = [entry.dll.decode('ascii') for entry in binary.DIRECTORY_ENTRY_IMPORT]
        # Do not let an installed developer VC runtime conceal a prerequisite.
        if any(name.lower().startswith(('vcruntime', 'msvcp140', 'vcomp140', 'concrt')) for name in imports):
            raise AssertionError('Official Node project SDK requires unbundled Microsoft CRTs: ' + repr(imports))
        evidence['imports'] = imports
    evidence_path = Path('.local/evidence/project-tools.json')
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('PASS: real official Node.js signature/hash, private install, actual Node/npm project tests, unchanged system PATH')
