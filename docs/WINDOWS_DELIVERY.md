# Windows delivery contract

## Complete Windows candidate — 19 October 2026

[Download STANICODE Windows x64 portable](https://github.com/staniscimarco/stanicode/actions/runs/39125576752/artifacts/12135978883) (GitHub sign-in may be required).

- Downloadable ZIP: **5,651,552,022 bytes** (5.65 GB).
- SHA-256: `1405f452b66cd51ebdd2933c6520be5d5956500c01d3ff0fe4447f8242c3b667`.
- Source: `9a5dc10169bc5e794bf1482c3cd2d94f05d02885`; [complete build passed](https://github.com/staniscimarco/stanicode/actions/runs/39125576752).
- Close the earlier no-model development app, extract the entire ZIP once, then open `STANICODE/STANICODE.exe`. Select a project folder, enter a request and start development. Keep all extracted runtime/model files together.
- Includes Qwen2.5-Coder-7B-Instruct Q4_K_M, llama.cpp b11669 CPU, bundled Python and fixed WebView2 155.0.4283.62. No separate developer tools are needed to launch. Optional Node/npm project tools are installed privately only with explicit approval; project dependencies and other compilers are separate.
- Candidate executables are unsigned. Dedicated clean Windows 10/11 and owner-PC acceptance remain unrun; this is not a completed production release. Artifact retention is finite; use the linked run's current artifact.

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
