# STANICODE — verification status

Updated 18 October 2026. Public source publication is authorized by the owner. The earlier Windows development installer was downloaded and installed by the owner; it does not contain the model. The complete portable candidate is a separate delivery.

## Verified

- Linux/Windows development CI and native installer compilation have passed. The source suite now contains 59 Python tests. Before the final timestamp regression was added, 57 passed locally and one Windows-only check was skipped; the 11 packaging tests, including that new regression, then passed. Windows/Linux CI rerun the full current suite. Four React tests and the production TypeScript/Vite build also passed.
- Chromium integration exercises the real UI/backend/files/tests with an explicitly simulated model and native bridge. This is separate from the actual Windows/model acceptance below.
- Qwen2.5-Coder-7B-Instruct Q4_K_M and llama.cpp b11669 CPU payloads were acquired on Windows and matched pinned upstream SHA-256 values. App-local release CRT DLLs and fixed WebView2 155.0.4283.62 were Microsoft publisher-verified. Runtime terms, full credits, actual transitive dependency notices and a populated CycloneDX inventory were collected. PE import auditing passed, including Microsoft's hash-pinned auxiliary x86 host loader inside its x64 runtime distribution.
- **Actual native offline acceptance passed** in [39117025871](https://github.com/staniscimarco/stanicode/actions/runs/39117025871) and again with isolated test directories in [39119211505](https://github.com/staniscimarco/stanicode/actions/runs/39119211505). These steps drove the actual Tauri app, fixed WebView2, Windows folder picker, bundled CPU model, explicit file approvals, actual Python tests, independent model review, report export, IT/EN, theme, second-instance handling and restart history. Developer tools were absent from the product PATH, and external traffic was blocked with Windows Firewall. Both complete jobs subsequently failed in archive assembly, not in those functional steps.
- Standalone real-model acceptance also passed in those runs, including deliberate backend crash/model-process cleanup. The one-directory frozen backend avoids the test-subprocess hangs observed with the earlier one-file packaging.
- Editable vector branding and generated app/installer icons are implemented and visually inspected; owner approval of the redraw is separate. Optional local Ollama is protocol-tested; acceptance against an installed Ollama service remains unrun.
- Experimental research preparation exports matched reviewed cases, checks patch provenance and secret patterns, generates a LoRA configuration and validates floating-point checkpoint architecture/tokenizer/tensor compatibility for MergeKit. Eight unit tests cover its safeguards. The actual standalone preparation command was exercised with clearly labeled miniature fixtures. No parameter training, merge, GPU benchmark or automatic promotion was performed or claimed.

## Archive assembly

The native test originally added runtime-generated files to the staging tree. It now uses separate directories with hard-linked immutable payload bytes; new browser state is confined to the test copy. Final manifest coverage remains strict. This isolated native acceptance passed in run 39119211505.

The subsequent ZIP writer rejected a vendor file timestamp older than 1980. The writer now uses the ZIP library's supported timestamp clamping, preserving file bytes and their hashes; its regression test passed. The complete workflow is rerunning this correction.

The ZIP64 assembler checks actual model/runtime/support hashes, complete fixed-WebView inventory, PE headers, license-file hashes, archive CRC and SHA-256. Actions receives the verified directory tree so its downloadable ZIP contains `STANICODE.exe` and the full payload after one extraction. The actual downloadable archive digest is recorded separately from the local assembly ZIP digest.

## Remaining release gates

- Observe successful complete archive assembly and upload; publish its actual URL, size and downloadable ZIP SHA-256 after it exists.
- Dedicated clean Windows 10/11 acceptance remains unrun. A hosted Windows Server runner contains development software; hiding PATH, auditing DLLs and executing offline do not establish a fresh Windows 10/11 VM result. No owner PC was remotely accessed.
- Application signing credentials are absent. Candidate executables are unsigned and may trigger SmartScreen.
- Actual LoRA training, MergeKit execution and GPU evaluation remain unsupported/unvalidated optional research operations. The core app does not depend on them.

## Security boundary

The implemented authentication, origin/host checks, path restrictions, approval nonces, journal/rollback behavior, process supervision, packaging checks and research input handling were reviewed and regression-tested. This is not an independent penetration test or an OS sandbox. Approved validation executes workspace code with the user's permissions; hostile concurrent filesystem changes are not contained. Private task history remains local. Memory retrieves test-backed cases without training weights. The core requires no cloud AI/account/subscription; Microsoft WebView2's separate data collection and SmartScreen terms are disclosed.

See [Windows delivery](WINDOWS_DELIVERY.md), [experimental research](EXPERIMENTAL_RESEARCH.md), [advanced local models](ADVANCED_LOCAL_MODELS.md) and [release checklist](../RELEASE_CHECKLIST.md). No completed production release is claimed while required gates remain open.
