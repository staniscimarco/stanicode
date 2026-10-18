# STANICODE

Private, local-first coding desktop application under development. **This checkout is an implemented development slice, not a complete or released offline Windows product.**

React/TypeScript UI + Tauri 2 shell + standard-library Python backend. The engine inspects a workspace, requests structured actions from local llama-server, requires review before writes and Python test execution, executes real tests, attempts up to three repairs, records events/snapshots in SQLite and supports rollback after restart. Sequential local architect, implementer/debugger and reviewer roles share one model. Italian/English UI includes folder selection, task controls, file comparisons, reports, sessions, local evidence export/deletion and theme settings.

## Development

Node 24, Python 3.12+, Rust and native Tauri prerequisites are developer dependencies. The Debian cloud image can prepare an unprivileged native sysroot with `python3 scripts/setup_native_linux.py`; source `scripts/native_env.sh` before native checks. They are not intended as end-user requirements.

```sh
npm ci
python3 -m unittest discover -s tests -v
npm run test:ui
npm run build
npm run desktop -- dev
```

On Windows use `python` for Python commands. Set `STANICODE_PYTHON` to a Python executable if needed. The native shell starts and authenticates the backend automatically. A browser-only Vite session cannot access the native folder picker/backend bootstrap. The app reports missing inference honestly until `models/manifest.json`, the licensed model and verified runtime are present. See [model packaging](models/README.md).

`python scripts/package_agent.py` packages a standalone backend using `requirements-build.txt`. `scripts/windows_release.ps1` verifies the payload before a Windows build. CI builds a clearly named **no-model development installer**, not an offline release. Read [development evidence and limitations](docs/STATUS.md) and [security boundaries](SECURITY.md).

## Scope today

Validation recipes support bundled Python unittest, Node tests, project npm test scripts and offline Cargo tests. Tests execute with user permissions after explicit approval. There is no OS sandbox, production vector logo, verified bundled model, real-model acceptance result, clean Windows result, signed binary, complete portable artifact or published release. Optional Git recovery refs preserve the user index; persisted snapshots provide file rollback. Local FTS retrieves test-backed cases with provenance. Memory does not train model weights. Test inference uses a deterministic mock and is labeled accordingly.
