# STANICODE — verification status

Updated 19 October 2026. Public source publication is authorized by the owner. The earlier development installer has no model; use the separate complete portable candidate in [Windows delivery](WINDOWS_DELIVERY.md).

## Verified

- Source `9a5dc10169bc5e794bf1482c3cd2d94f05d02885`: development CI, complete Windows workflow and actual approved private Windows SDK workflow all completed successfully.
- Python: 71 tests discovered, 70 passed locally and one Windows-only check skipped. Seven React tests and the production TypeScript/Vite build passed. Chromium integration used the real backend/files/tests and explicitly simulated model/native bridge; it is separate from real Windows acceptance.
- The complete Windows build drove the actual Tauri app, fixed WebView2 and bundled CPU model offline, with developer tools absent from the product PATH and external traffic blocked by Windows Firewall. Folder selection, approved writes, actual Python tests, independent review, report export, locale/theme, single-instance behavior and history after restart passed. New in-app approval dialogs, cancellation of optional SDK installation without installing, rollback after restart and memory deletion preserving task history also passed.
- Standalone actual-model acceptance passed, including deliberate backend crash and owned model-process cleanup. The frozen backend contains its own Python interpreter.
- Actual optional private Node 24.19.0/npm installation passed on Windows through the frozen backend: official download, pinned SHA-256, OpenJS Authenticode, real Node/npm tests and unchanged global PATH. No SDK download occurs without approval. npm success requires real nonzero passing test evidence.
- Pinned model/runtime hashes, Microsoft WebView2/CRT publisher verification, complete dependency/runtime notices, CycloneDX inventory and PE import auditing passed. ZIP64 assembly, archive CRC verification and final Actions upload passed. The actual downloadable ZIP digest is recorded in the delivery receipt, separately from the local assembly ZIP digest.
- Editable vector branding was visually inspected; owner approval of the redraw is separate. Optional Ollama is protocol-tested; installed-service acceptance is unrun.
- Experimental research preparation validates reviewed case provenance, secret patterns and floating-point checkpoint compatibility and prepares LoRA/MergeKit configurations. Nine unit tests cover its safeguards. The standalone preparation command was exercised using labeled miniature fixtures. No training, merge, GPU benchmark or automatic promotion was performed.

## Remaining release gates

- Dedicated clean Windows 10/11 and owner-PC acceptance remain unrun. A hosted Windows Server runner, hidden developer PATH, DLL auditing and offline execution do not establish a clean Windows 10/11 result. No owner PC was remotely accessed.
- Application signing credentials are absent. Candidate executables are unsigned and may trigger SmartScreen.
- Actual optional LoRA training, MergeKit execution and GPU evaluation remain unsupported/unvalidated. Core operation does not depend on them.

## Security boundary

Authentication, origin/host checks, path restrictions, explicit approvals, journal/rollback, process supervision, packaging checks and research inputs were reviewed and regression-tested. This is not an independent penetration test or an OS sandbox. Approved validation executes workspace code with the user's permissions. History stays local; memory retrieves test-backed cases without training weights. The core requires no cloud AI account; separate Microsoft WebView2 data collection and SmartScreen terms are disclosed.

See [Windows delivery](WINDOWS_DELIVERY.md), [project tools](PROJECT_TOOLS.md), [research](EXPERIMENTAL_RESEARCH.md) and [release checklist](../RELEASE_CHECKLIST.md). No completed production release is claimed while required gates remain open.
