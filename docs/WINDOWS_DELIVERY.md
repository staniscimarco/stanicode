# Windows delivery contract

The end user should receive one archive, extract its complete STANICODE folder and double-click STANICODE.exe. They should not install Python, Node, Rust, Git, Ollama, a model or WebView2 to launch STANICODE. Project toolchains for projects the agent builds are a separate requirement and are detected rather than silently installed.

Development dependencies and payload acquisition are Codex/build-runner work. Do not ask the owner to assemble a runtime/model manually as the acceptance test.

The verified build payload must contain:

- `stanicode-agent.exe` produced on Windows by PyInstaller;
- `models/manifest.json`, the actual licensed GGUF, llama-server and all verified companion DLLs/license files;
- `webview2/msedgewebview2.exe` and its complete fixed runtime, with `webview2-manifest.json` (version, official source, license_file and a files map of every relative file to its SHA-256);
- complete notices, dependency license texts and `SBOM.cdx.json`.

The native launcher points WebView2 to this payload before constructing the window. The ZIP64 assembler can hold multi-GB model files without manual chunks. It checks PE architecture, GGUF signature, hashes and metadata, but these checks cannot establish functional acceptance or licensing rights.

The manual `windows-complete.yml` workflow acquires the pinned payloads, packages the backend, collects actual upstream notices, runs real-model acceptance, compiles the native shell, drives offline native UI acceptance, audits PE imports and assembles the candidate. `scripts/windows_release.ps1` performs the same sequence in an elevated VS2022 developer shell. A fast preflight proves the acceptance firewall allows loopback while blocking external HTTPS before the expensive build work. The output remains a candidate until dedicated clean Windows 10/11 acceptance also succeeds. The separate `ci.yml` workflow produces a development/no-model installer; it does not establish complete offline delivery.

Do not distribute the Linux backend or source ZIP as the owner's ready-to-run Windows application. Do not tag/publish a release without real test evidence, bundle size, exact model/runtime versions/licenses, checksums and clean-machine results.
