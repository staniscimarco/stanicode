# STANICODE — verification status

Updated 18 October 2026. The public source repository is authorized by the owner. The Windows development installer was downloaded and installed by the owner. It does not contain the model and is not the complete offline delivery.

## Verified

- GitHub Actions run [39105314504](https://github.com/staniscimarco/stanicode/actions/runs/39105314504) passed on Linux and Windows, including backend tests, UI tests/build, dependency audit, Windows standalone backend smoke and native NSIS installer compilation.
- The current backend suite contains 40 tests. All 40 passed locally, including actual Python/Node/Rust validation, Windows path rules, nested context, malformed action recovery, approval nonces, independent-review rejection, verified memory, persistence/rollback, process cancellation/timeout and packaging integrity. Windows and Linux CI rerun the suite for changes.
- Four React tests and the production TypeScript/Vite build passed. The Chromium integration test exercises the actual UI/backend/files/tests with an explicitly simulated model and native bridge; it is not Windows/model acceptance.
- Official Qwen2.5-Coder-7B-Instruct Q4_K_M weights were actually acquired on a Windows runner and matched the pinned upstream SHA-256. The llama.cpp b11669 CPU archive also matched its upstream digest; app-local Microsoft CRT DLL signatures were checked.
- Microsoft's fixed WebView2 155.0.4283.62 was obtained from the official download page and its executable's Microsoft signature validated. Its first verified archive hash is pinned for subsequent builds.
- In real-model run [39107807819](https://github.com/staniscimarco/stanicode/actions/runs/39107807819), the model planned and generated two files and the backend applied them after explicit approval in a disposable workspace. The subsequent actual validation timed out. This run **failed**, and does not establish working end-to-end generation.

## Work in progress

The complete Windows workflow diagnoses frozen-interpreter startup while the actual model occupies memory, preserves inference diagnostics, inventories upstream license texts and compiles the native desktop. An actual native UI acceptance script drives the Windows folder picker, real local inference, file approvals, test execution, report export, locale/theme and restart history. It hides developer tools from the product PATH and applies outbound Windows Firewall blocks. These are executable checks, not evidence that they have passed.

The ZIP64 assembler streams multi-GB model files directly, verifies PE architecture, GGUF header, model/runtime/support hashes and complete fixed-WebView inventory. License texts and CycloneDX SBOM are mandatory. Container fixtures used by unit tests are explicitly non-executable and never distributed as a product.

## Remaining delivery gates

- Diagnose and pass actual-model validation with the frozen backend.
- Pass actual native Windows/offline UI acceptance and restart recovery.
- Identify and include the correct Microsoft runtime redistribution terms and complete transitive notices/SBOM. The WebView2 SDK license does not replace its runtime terms.
- Assemble and verify the complete extract-and-run archive; publish its actual URL, size and SHA-256 only after it exists.
- A hosted Windows runner has development software installed. Hiding its PATH does not prove a fresh Windows 10/11 VM has no missing system dependencies. Dedicated clean-machine acceptance remains a separate requirement.
- Signing credentials are absent. Binaries are unsigned and may trigger SmartScreen.

## Product boundaries

File writes require review; fixed validation recipes execute workspace code with the user's permissions. Process lifecycle controls are not a filesystem/network sandbox. Task history can contain private source and must remain protected locally. Local memory retrieves test-backed cases and does not train model weights. No cloud AI/account/subscription is required by the core architecture.

The editable vector brand master, advanced Ollama integration and experimental dataset/LoRA/merge preparation remain separate unfinished requirements; research execution must not be faked or block the baseline app. See [Windows delivery](WINDOWS_DELIVERY.md) and [release checklist](../RELEASE_CHECKLIST.md). No completed release is claimed while the gates above remain open.
