# Windows delivery contract

The end user should receive one archive, extract its complete STANICODE folder and double-click STANICODE.exe. They should not install Python, Node, Rust, Git, Ollama, a model or WebView2 to launch STANICODE. Project toolchains for projects the agent builds are a separate requirement and are detected rather than silently installed.

Development dependencies and payload acquisition are Codex/build-runner work. Do not ask the owner to assemble a runtime/model manually as the acceptance test.

The verified build payload must contain:

- `stanicode-agent.exe` produced on Windows by PyInstaller;
- `models/manifest.json`, the actual licensed GGUF, llama-server and all verified companion DLLs/license files;
- `webview2/msedgewebview2.exe` and its complete fixed runtime, with `webview2-manifest.json` (version, official source, license_file and a files map of every relative file to its SHA-256);
- complete notices, dependency license texts and `SBOM.cdx.json`.

The native launcher points WebView2 to this payload before constructing the window. The ZIP64 assembler can hold multi-GB model files without manual chunks. It checks PE architecture, GGUF signature, hashes and metadata, but these checks cannot establish functional acceptance or licensing rights.

Run the real-model backend smoke, then the Windows build and portable assembly through `scripts/windows_release.ps1`. It intentionally fails when payloads are missing. The output is a candidate until clean Windows/native UI/offline acceptance succeeds. The existing GitHub CI workflow is a development/no-model workflow; neither its file nor its future artifact is evidence of a completed offline release.

Do not distribute the Linux backend or source ZIP as the owner's ready-to-run Windows application. Do not tag/publish a release without real test evidence, bundle size, exact model/runtime versions/licenses, checksums and clean-machine results.
