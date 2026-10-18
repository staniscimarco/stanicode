# STANICODE — verification status

Updated 18 October 2026. The public source repository is authorized by the owner. The Windows development installer was downloaded and installed by the owner. It does not contain the model and is not the complete offline delivery.

## Verified

- Linux/Windows development CI and native installer compilation passed, including run [39110506989](https://github.com/staniscimarco/stanicode/actions/runs/39110506989).
- The current Python suite discovers 47 tests: 46 passed locally and one Windows-only check was skipped. Four React tests and the production TypeScript/Vite build passed. The Chromium integration exercises the actual UI/backend/files/tests with an explicitly simulated model and native bridge; it is not Windows/model acceptance.
- Actual Qwen2.5-Coder-7B-Instruct Q4_K_M weights and llama.cpp b11669 CPU binaries were acquired on Windows and matched the pinned upstream SHA-256 values. App-local Microsoft CRT DLL signatures were checked.
- **Real-model end-to-end acceptance passed** in Windows runs [39109327656](https://github.com/staniscimarco/stanicode/actions/runs/39109327656) and [39110301782](https://github.com/staniscimarco/stanicode/actions/runs/39110301782): planning, implementation, explicit approvals, actual Python tests and independent review. Switching the frozen backend from one-file to one-directory packaging resolved child-interpreter test hangs without weakening validation.
- The native Windows desktop compiled with the bundled backend and fixed WebView2. Microsoft's fixed WebView2 155.0.4283.62 executable and app-local CRTs were publisher-verified. The runtime EULA, full credits and CRT license documents were extracted from official runtime/download and signed redistributable sources. The final strict inventory and distributable assembly remain separate gates.
- Editable vector brand masters and generated app icons are implemented and visually inspected; owner approval of the redraw remains separate. Advanced local Ollama is opt-in and protocol-tested; acceptance against an installed Ollama service has not run.

## Work in progress

Actual native UI acceptance drives the Windows folder picker, real local inference, file approvals, tests, report export, locale/theme, single instance and restart history. It hides developer tools from the product PATH and applies outbound Windows Firewall blocks. Real firewall preflights passed with both client and server blocked, including IPv4-mapped IPv6 loopback, in [39114635926](https://github.com/staniscimarco/stanicode/actions/runs/39114635926).

Run [39114159286](https://github.com/staniscimarco/stanicode/actions/runs/39114159286) started the real STANICODE window, fixed WebView2 processes, packaged backend and llama-server, but the GUI driver could not reach the WebView inspection port. It failed and does not prove interactive/native acceptance. Release inspection is now compiled in and enabled only by the explicit native acceptance environment flag; ordinary launches keep the inspector off. The revised Windows acceptance run is pending.

The ZIP64 assembler streams multi-GB weights directly and verifies PE architecture, GGUF header, model/runtime/support hashes and complete fixed-WebView inventory. Actual license texts and CycloneDX SBOM are mandatory. Unit-test binary fixtures are non-executable and never distributed as the product.

## Remaining delivery gates

- Pass actual native Windows/offline UI acceptance and restart recovery.
- Pass the final transitive notices/SBOM gate and portable PE dependency audit.
- Assemble and verify the complete extract-and-run archive; publish its actual URL, size and SHA-256 only after it exists.
- A hosted runner contains development software. Hiding PATH and auditing DLLs do not prove a fresh Windows 10/11 VM has no missing system dependencies. Dedicated clean-machine acceptance remains a separate requirement.
- Signing credentials are absent. Application binaries are unsigned and may trigger SmartScreen.
- Experimental reviewed-dataset/LoRA/merge preparation follows the functional baseline; actual training must never be simulated or implied by local memory retrieval.

## Product boundaries

File writes require review; fixed validation recipes execute workspace code with the user's permissions. Process lifecycle controls are not a filesystem/network sandbox. Task history can contain private source and must remain protected locally. Local memory retrieves test-backed cases and does not train model weights. No cloud AI/account/subscription is required by the core. Microsoft WebView2 data collection and SmartScreen terms are disclosed separately.

See [Windows delivery](WINDOWS_DELIVERY.md), [advanced local models](ADVANCED_LOCAL_MODELS.md) and [release checklist](../RELEASE_CHECKLIST.md). No completed release is claimed while the required gates remain open.
