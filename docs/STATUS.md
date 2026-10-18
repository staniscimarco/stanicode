# Development evidence and release blockers

This is implemented application code, **not a completed or accepted Windows release**.

## Implemented

- One local model runs serial architect, implementer/debugger and independent-reviewer roles. The architect plan is passed to implementation. The reviewer can reject a task even when tests pass. Malformed implementation JSON triggers a bounded repair attempt. Cancellation interrupts an in-flight inference socket.
- File actions require review and approval tied to a unique proposal identifier; stale approval requests are rejected. Portable path rules reject traversal, symlinks, Windows device names, alternate streams, Git internals and common secret paths. Atomic replacement avoids modifying an external hardlink. Concurrent tasks and rollback/write races are rejected.
- Optional Git recovery refs preserve the user's index; file snapshots support rollback without resetting unrelated work. Unfinished approvals are marked interrupted on restart. Write-ahead snapshots recover both sides of an interrupted file replacement.
- Fixed validation recipes cover bundled Python unittest, Node tests, project npm test scripts and offline Cargo tests. Missing project toolchains have explicit diagnostics; STANICODE itself does not require Node or Cargo at launch. No dependency installation is performed by these recipes.
- Validation output is bounded in memory. Linux process groups are cleaned up on cancellation/timeout/exit. A Windows Job Object implementation is present but remains untested on Windows. These mechanisms are process lifecycle controls, not an OS sandbox.
- SQLite FTS retrieves deduplicated, test-backed cases before planning; provenance records model/runtime identity and patch hashes. Cases are saved only after passing validation and independent review. Root-cause text remains a model hypothesis. Memory can be searched, exported and deleted; weights are not trained or changed.
- Authenticated loopback backend with random session token, allowed Origin and exact Host checks. Generated code does not inherit injected API/GitHub credentials. Task snapshots still contain private source; the local database must be protected.
- Shared startup/package verifier checks runtime/model/companion hashes, source/version/license metadata and declared RAM requirements. Inference uses a random loopback port and per-launch API key. Startup detects a missing bundle and monitors runtime exit.
- Italian/English React UI includes folder selection, task controls, file comparisons, events, sessions, report export, searchable memory and dark/light themes. Native Tauri shell starts the standalone backend. Raster branding and ICO sizes derive from supplied assets.
- ZIP64 assembly validates Windows x64 PE headers, actual GGUF magic, model/runtime hashes, companion libraries and the complete fixed WebView2 file hash inventory. It requires license/SBOM staging and produces only an unaccepted candidate. It never relabels a Linux binary as Windows or downloads missing components at end-user startup.

## Actual local evidence

- **39 Python tests passed**, including real Python, Node and Rust test executions; role protocol over a local HTTP fixture; independent-review rejection; retrieval/dedup/deletion; Git index preservation; traversal/Windows paths/hardlinks; process timeout/cancel/output limits; and packaging integrity/container fixtures.
- **4 UI component tests passed** with native/HTTP mocks.
- **Real system Chromium acceptance passed** through the actual UI and authenticated backend: folder selection through a native bridge fixture, request, approval, real file writes, actual Python unittest, reviewer fixture, memory search, JSON report download, locale/theme and rollback. Inference and native selection/bootstrap were simulated in this check; it is not real-model or Windows acceptance.
- TypeScript and Vite production build passed. Full npm audit reported zero known advisories in the installed tree. Ruff checks passed. This is not proof of complete application security.
- **Native Linux `cargo check --locked --jobs 2` passed** after extracting 131 signature/checksum-verified Debian packages into `/workspace/.stanicode-tools/linux-sysroot`. System files were not installed or modified. This compiles/checks the Tauri source; it does not prove a linked GUI executable runs.
- A standalone Linux backend was built and tested. Its packaged interpreter ran a real project unittest; authenticated health correctly rejected missing inference; parent-close shutdown passed. No Windows conclusion follows from that Linux result.
- Packaging tests use explicitly labeled, non-executable PE/GGUF container fixtures. No test fixture is a distributable product or real model.

## Confirmed external blockers

- The running cloud machine still receives proxy **403 Forbidden** for `api.github.com`, `huggingface.co`, `cdn.playwright.dev` and the official `developer.microsoft.com` WebView2 page. Saved draft network rules are not evidence that runtime access was applied.
- No actual inference weights/runtime or fixed Windows WebView2 payload could be obtained and validated. Exact model suitability, licensing, RAM/performance and real tool-use reliability remain unproven. Task creation correctly stays disabled without real inference readiness.
- No Windows machine/runner is attached or executed. Windows compile/link, Job Object behavior, portable startup, no-prerequisite offline acceptance, signing and installer behavior remain unvalidated.
- Git read access works. GitHub API account/privacy verification and Actions access remain blocked. No source push, CI success, tag, release URL or downloadable Windows app is claimed. User preference is to complete local development before publication.

## Remaining release requirements

Run `scripts/smoke_real_inference.py` on the actual packaged backend and licensed model. Build and inspect the Windows portable candidate, include a verified fixed WebView2 runtime, dependency license texts and complete CycloneDX SBOM, then execute clean Windows native/offline acceptance before any release. The current assembler checks structure/integrity, not runtime correctness or legal sufficiency.

A complete editable SVG brand master, full accessibility review, a safe advanced Ollama integration, stronger project isolation and comprehensive real-model regressions remain unfinished. Training/merging research modules are deliberately deferred until the baseline release works, as the supplied specification requires. No production-readiness claim is made. See RELEASE_CHECKLIST.md.

## Network recheck after configuration publication

The environment configuration was subsequently published and contains the required custom domains. Explicit network permission was also granted for the current turn. Nevertheless the running machine still receives proxy CONNECT 403 for api.github.com, huggingface.co and developer.microsoft.com. The standard package-registry control succeeds. Re-saving the same domain list is not the next diagnostic step: the machine/proxy must be reconnected or reprovisioned against the published configuration, or the platform egress-policy mismatch investigated. No model download, Windows execution or completed release is claimed.
