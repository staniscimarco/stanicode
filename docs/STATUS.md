# Development evidence and remaining work

This is a development implementation, **not a completed STANICODE release**.

## Implemented and locally exercised

- Python backend: bounded structured file proposals; approval before writes and test execution; path traversal, protected-path and symlink rejection; serial task execution; pause/resume at safe checkpoints; cancellation; three-attempt repair limit.
- SQLite history and original file snapshots; persisted rollback with external-edit detection; passing-test evidence export/deletion.
- Loopback HTTP API with random session authentication, Host validation and Origin restrictions. Generated tests do not inherit injected GitHub/API credentials.
- Local llama-server adapter and supervised runtime startup with runtime/model checksums. Model requests use a per-launch API key. No cloud inference or telemetry implemented.
- React/TypeScript UI with native folder-picker integration, task controls, pending before/after review, event log, history, report export, evidence memory and Italian/English labels, dark/light themes.
- Tauri shell source that starts the standalone backend, retains session credentials in memory and closes its stdin on native process exit.
- Standalone Linux backend built with PyInstaller. Its own bundled interpreter runs an actual generated-workspace unittest. Authenticated health and shutdown on parent-close were exercised.
- Owner-supplied raster assets imported; Windows ICO and raster sizes generated. No new editable vector master is claimed.

## Checks

- 12 backend tests: real file generation and one real workspace unittest with a deterministic mock model; persistence/restart/rollback; traversal/symlinks/secrets; cancellation; pause/resume; HTTP authentication/origin; checksum and absent-payload rejection; context limits; credential filtering; zero-test rejection.
- 4 UI component tests: folder selection/request submission, disabled start without inference, proposed-file display and explicit approval, locale persistence. Native APIs and HTTP responses are mocked in these component tests.
- TypeScript check and Vite production build passed.
- Full npm audit passed after upgrading the test runner to resolve reported advisories. This is an audit of installed dependency metadata, not proof that the app is secure.
- Python Ruff checks passed.
- Packaged Linux backend smoke passed; no Windows runtime result is inferred from it.

## Observed blockers

- Requests to `api.github.com`, `huggingface.co` and `cdn.playwright.dev` returned proxy 403 Forbidden. Network additions were saved in the environment draft, but that does not apply them to the running instance. Git read access to the selected repository works; the remote originally had no refs.
- GitHub account/repository metadata and privacy could not be verified through API. No push, Actions execution, release publication or public artifact upload is claimed. Source is retained locally.
- `cargo check` stops in `glib-sys`: required `glib-2.0` system metadata is absent. GTK/WebKitGTK development libraries are also absent. The native Tauri shell has not compiled or run on this machine.
- Chromium is absent and its download was denied. No real-browser or native desktop visual test passed. UI component tests use jsdom.
- No Windows execution environment is attached. Windows build, installer, clean-machine tests and signing remain unrun.
- No actual model or inference binary is present. Real-model reliability, license verification, RAM/performance and offline end-to-end acceptance remain unvalidated. The interface deliberately disables task creation without local inference readiness.

## Product requirements still pending

This implementation supports Python unittest workflows only. Approved tests execute arbitrary workspace code with user permissions; there is no OS sandbox, process-tree containment or protection against a concurrent hostile filesystem actor. Pause/cancel during inference waits for the current model request (up to its timeout). The bundled interpreter has the modules collected by PyInstaller, not a guaranteed complete external project toolchain.

Sequential architect/implementer/debugger/reviewer roles, Git checkpoints (as distinct from current local snapshots), language adapters beyond Python, independent model review, solved-case retrieval with provenance, privacy-hardened memory, training/merge research modules, complete bilingual accessibility review, clean editable SVG branding, full license texts/SBOM and a true self-contained portable Windows distribution remain unfinished. They must not be described as shipped features.

No tag or production release has been created. The Windows workflow produces only an explicitly labeled no-model development installer when it actually runs; it does not establish release acceptance. See RELEASE_CHECKLIST.md.
