# STANICODE — CODEX MASTER BUILD AND DELIVERY MANDATE

**Project name:** STANICODE
**Repository to create:** `stanicode` under the connected GitHub account
**Product:** a complete, private, zero-subscription, local-first autonomous coding desktop application for Windows
**Brand identity:** STANICODE. The approved emblem discreetly embeds the letters G, D and C; never display family names or surname in visuals, UI, documentation or metadata.
**Role:** You are Codex acting as principal architect, full-stack developer, agent engineer, QA lead, security reviewer, build/release engineer, and technical writer. **Execute the implementation**, not merely write a specification.

## 0. What the owner expects — non-negotiable end-user experience

The owner does **not** want to install, configure, or connect Ollama, Python, Node.js, Git, Docker, WSL, models, SDKs, agents, plugins, API keys, or any development dependency before using STANICODE. They expect **one deliverable to launch**. The preferred deliverable is an **offline portable Windows x64 ZIP** containing the entire working program and bundled offline model. Unzip it and double-click `STANICODE.exe`; no additional setup and no account. Also provide a conventional one-click Windows installer if feasible. Everything required for STANICODE's own operation must ship inside the product, subject to third-party licenses. The initial archive will be large: that's acceptable.

Normal flow: **Open STANICODE → choose a local project folder → type what to build or change → press Start Development → watch real agent activity → receive modified files and objective validation results**. No model picker or manual technical steps in the normal flow. The owner only performs this final hands-on acceptance test after a release is ready; **Codex is responsible for all earlier automated integration, security, packaging, and smoke tests**.

DO NOT claim zero setup if a critical runtime or model must still be downloaded separately. DO NOT claim an offline package exists unless it truly contains the model and all app runtime dependencies. If the current environment or connected accounts cannot produce or validate a complete binary, document the exact blocker and keep working on everything that is feasible; **do not pretend the release is complete**. An unattended product installation cannot solve missing compilers/SDKs required by arbitrary *user-created projects*; distinguish those from STANICODE's own bundled dependencies. If an external project toolchain is missing, detect it, explain it, and offer an explicitly approved automated setup where technically and legally feasible.

## 1. GitHub: create and deliver the actual repository

1. Discover the GitHub identity and available permissions using the already connected GitHub integration in Codex. **Create a new repository named exactly `stanicode`**, PRIVATE by default; do not make family names or project code public without the owner's explicit approval.
2. Initialize it with complete source, assets, lockfiles, `.gitignore`, license/third-party notices, tests, documentation, security policy, GitHub Actions and issue/milestone tracking as useful. Commit and push real implementation incrementally. Do not create an empty repository and stop.
3. Check for an existing repository of that exact name first; never overwrite or delete existing work. If it exists and belongs to the owner, inspect and request direction only if necessary to avoid destructive operations.
4. Set up CI using **GitHub Actions Windows runners** for build, lint, unit tests, integration tests, packaging smoke tests, checksum generation and release artifact publication. Require CI success before tagging a release.
5. Create a release, e.g. `v0.1.0` for the first actually working end-to-end release, and publish downloadable artifacts. **Don't label anything production-ready until release criteria are met.** Include an offline portable package containing the model and a regular installer where practical.
6. Model files may exceed Git hosting limits. **Never commit model weights to the Git repository.** For release packaging, obey current GitHub release per-asset and storage limits: package as verified chunks if allowed, use the release workflow to reassemble internally, or choose an appropriate explicitly documented artifact host. The user must not manually combine chunks or fetch/install models. A single extract-and-run distributable is the preference; if the platform cannot host it, report that limitation instead of claiming completion.
7. If the GitHub integration cannot create repositories, push, trigger Actions or publish releases, report the exact unavailable permission/action and generate all the repository-ready code and automation locally. **Do not fabricate a GitHub URL, CI pass, commit, or release.**

## 2. Brand and graphic assets (mandatory)

The supplied `assets/STANICODE_APPROVED_LOGO.png` is the OWNER-APPROVED visual reference and supersedes all previous concepts. Preserve its overall composition and G/D/C monogram. The product name STANICODE is the only visible name in the branding. Add these files to the new repository's `branding/` directory:
- `STANICODE_APPROVED_LOGO.png` — owner-approved dark-background visual identity, with G/D/C hidden in the symbol. Do not replace the artistic direction without owner approval.
- `STANICODE_app_icon_512.png` — icon draft extracted from the approved monogram, to be remastered as an SVG/ICO.
- Produce an original **clean, editable SVG master** faithfully referencing the approved emblem, **without any ® registered-trademark sign**. The letters G, D and C must be subtly woven into the shape, not written as standalone names. Preserve the luminous cyan/blue/violet palette, dark theme, and professional developer aesthetic. A stylized reference image is NOT a substitute for a clean vector.
- Produce `STANICODE.ico` (multi-resolution Windows icon), PNG assets at 16/32/48/64/128/256/512/1024 where required, taskbar icon, loading splash, About page lockup and installation imagery. Provide a usable light-background variant and accessible high-contrast rendering.
- Wordmark exactly `STANICODE`; optional product subtitle `Autonomous AI Development Studio`. **Do not print [private name omitted], [private name omitted], [private name omitted], [private name omitted] or the expanded initials anywhere in the app, splash, About, installer, metadata, screenshots, README or release.** Only the visually concealed G/D/C letterforms may appear in the emblem.
- Integrate the assets into the actual executable, installer, taskbar, window chrome, splash, About page, documentation and GitHub README. No generic Tauri/Vite/Python icons or placeholders remain in shipping deliverables.
- Do not add `®` or imply trademark registration without legal confirmation. Check potential name conflicts before public distribution, but do not block private development for trademark research.

## 3. Architecture and runtime: self-contained by design

Desktop UI: Tauri 2 + React + TypeScript for Windows 10/11 x64, accessible bilingual Italian/English UX and real folder picker. Build signed binaries only when credentials actually exist; otherwise unsigned builds are honestly labeled with Windows SmartScreen caveats.

Agent backend: a packaged and supervised local service (e.g. Python 3.12+ FastAPI bundled as a standalone sidecar, or a Rust implementation if simpler to distribute). No Python install, Node install, manual virtual environment, separate terminal, web service configuration or ports exposed to the LAN. Use loopback-only + random session token, strict origin checking, safe process lifecycle and diagnostics.

Inference: default to an **embedded llama.cpp/llama-server CPU-compatible Windows executable with a bundled, redistributable, quantized open-weight coding model**. Evaluate model licenses, RAM/performance and tool-calling reliability; Qwen2.5-Coder-7B-Instruct GGUF Q4-class is a candidate, **not an assumed universal best**. Preserve an Ollama adapter for advanced use, but the owner must not need Ollama installed or running. Bundle and launch the inference process automatically; provide model hash, model license, and all corresponding runtime licenses. If llama.cpp tool-calling format is imperfect, use a validated structured action protocol with strict parsing and recovery. Gracefully handle CPU-only inference slowness and memory pressure on an i7/16 GB laptop; avoid loading multiple models concurrently.

The product must run with **zero cloud credentials, zero AI API calls, zero mandatory telemetry and zero recurring fees**. Offline operation means no network is needed after the portable distribution has been obtained. Clear disclosures: normal CPU inference can be slow and less capable than Claude Opus; no falsely guaranteed capability parity, speed, or success.

## 4. Agent behavior — equivalent interaction pattern to Claude Code / Cursor

Implement real, validated tool-use and a persistent agent state machine:
`Analyze → Plan → Implement → Execute → Test → Diagnose → Repair → Review → Deliver`.

Required behaviors:
- Open a new/old workspace, inspect relevant files and project instructions, build a task plan, recognize language/runtime and project conventions, generate or modify multiple files, search within repo, apply diffs safely, use Git checkpoints, execute approved terminal commands, run builds/tests, inspect failures, iterate with explicit limits, and present actual changed files and test output.
- Stream real activity; Pause/Resume/Cancel; bounded retries/timeouts; recover from application crash; maintain task history; automatic report with files changed, commands run, tests passed/failed, known limitations, next steps.
- Work with Python, TypeScript/JavaScript/React, Node, HTML/CSS, Rust and mixed repositories by recognizing existing project tools; support extension adapters for additional languages.
- Multi-agent roles (architect/planner, implementer, debugger, independent reviewer), **sequential on the same local model by default** for 16 GB RAM. Role-specific plans/prompts and objective acceptance gates, not four heavyweight models in parallel. Parallel modes only after measured hardware/benchmark suitability.
- Never allow competing agents to write the same files simultaneously; use serial patches or isolated worktrees. Prefer simple, reliable agent orchestration to fragile complexity.
- Project files remain inside the selected workspace. Protect against path traversal and symlink escapes. Hide secrets from model context unless strictly needed. Require approval for destructive commands, network access, privileged operations, installers, access outside the workspace, deletion, publication and risky dependency changes. Warn that command allowlists are not a true OS-level sandbox; use OS sandboxing where feasible.
- Real functional controls: folder picker, chat, Start, Stop, Pause, Resume, diff review, approvals, rollback, log viewer, test results, memory, Settings, About and export. Nothing decorative or inert.

## 5. Verified continuous learning (NOT false claims of self-training)

- Save objective task history and only **verified fixes** with original symptom, root cause, patch, relevant environment, test evidence, model/runtime version and provenance in local SQLite.
- Provide local search with SQLite FTS as a low-resource baseline. Optional on-device embeddings/vector retrieval only when memory allows. Retrieve relevant solved cases before new tasks; verify relevance and prevent stale or incorrect examples from overriding instructions.
- Track strategy metrics and deduplicate experiences; allow user to inspect/export/delete personal knowledge. Do not use code from the web for training without license and provenance review, and do not store secrets.
- Add dataset export of reviewed examples and a separate *experimental* LoRA/fine-tuning and MergeKit-compatible checkpoint merge workflow with compatibility checks, reproducible benchmarks and manual promotion. **Do not silently alter model weights or claim a model learned through weight updates when only RAG/memory occurred.**
- Real parameter training/merging may be infeasible on this machine; in that case implement preparation, validation, and clear unsupported status rather than faking training results. Core app MUST function without these research modules.

## 6. Interface and usability

- Brand-aligned desktop layout inspired by the clarity of Cursor/Claude Code but original in design. Dark theme by default with light theme optional.
- Easy first launch: app discovers its packaged model and backend, checks available resources, starts them automatically, reports actual readiness, and opens workspace selection. User should not see a setup wizard requiring accounts, API keys, commands or runtime installers.
- Main page: workspace folder, natural-language task box and primary **Start Development** action. Optional sidebar for file tree and existing sessions; task plan, terminal events, diffs, approvals and test results in tabs/panels. Advanced model settings hidden from routine use.
- Italian and English translations from first release. Proper error messages, keyboard navigation, status indicator for offline model, memory settings and cancellation.
- No fabricated progress bars, meaningless “AI working” animations or hardcoded results.

## 7. Testing, packaging and distribution are part of development, not homework for owner

Before delivery, Codex must run or set up automation for:
- Backend unit/integration tests, front-end type/lint/component tests, reproducible builds and secure dependency audits.
- Deterministic mock-model end-to-end test: empty folder → request → created project → test execution → verified diff/report.
- Real embedded-inference test: packaged `STANICODE.exe` starts embedded llama.cpp with bundled model, issues a request, modifies a test workspace, runs a real test, closes/restarts without losing the task history. Clearly distinguish this from mocked tests.
- Regression tests for missing/bad model hash, insufficient RAM, backend crash, invalid tool JSON, malicious paths/symlinks, cancel/pause/resume, command timeout, rollback, dangerous shell commands, incomplete installations, no internet, locale switching and memory integrity.
- **Windows GitHub Actions release build**, including bundled model and backend; checksum every artifact; scan for missing runtime dependencies. Launch STANICODE from a clean Windows test environment with no Python/Node/Ollama/Git prerequisites installed. Use a clean runner/VM and automate as much of the no-prerequisite acceptance test as possible.
- Produce `STANICODE-Windows-x64-Portable.zip` with executable, runtime, model, backend and assets, and optionally `STANICODE-Setup-Windows-x64.exe` with equivalent offline payload. If exact filenames or distribution need chunking due to hosting limits, publish user-friendly fully automatic retrieval/extraction; no manual model installation. Document actual offline vs online limitations.
- Publish evidence: test commands/logs, CI job URL, actual artifact URL, SHA-256, shipped model name/version/hash/license, portable distribution file size, known issues and honest release status. **Never claim to have tested hardware you did not access.**
- Never ship secret keys, personal data, or personal names in telemetry. No mandatory sign-in.

## 8. Mandatory repository contents

`apps/desktop/` (desktop UI and native packaging), `services/agent/` (or equivalent packaged agent runtime), `packages/contracts/`, `packages/engine/` or appropriate module boundaries, `branding/`, `models/README.md` (metadata only, not weights), `tests/`, `scripts/`, `.github/workflows/`, `docs/`, `THIRD_PARTY_NOTICES.md`, `SECURITY.md`, `README.md`, `README.it.md`, `LICENSE` (license must be chosen consistently with ownership and dependencies), `CHANGELOG.md`, `RELEASE_CHECKLIST.md`, `SBOM` where feasible. Create the cleanest realistic layout rather than empty placeholder folders.

## 9. Execution protocol for Codex — act, do not merely explain

1. Inspect available tool/runtime, connected GitHub account and permissions. Create PRIVATE `stanicode` repository. Push initial skeleton with issue plan and baseline tests.
2. Import the owner-approved STANICODE logo and create all production icon/vector variants; integrate into the desktop application.
3. Build a complete working vertical slice immediately: desktop UI → local agent backend → validated file tool → mock local inference → real project generation → tests → diff/report. Execute tests; fix failures.
4. Implement local bundled inference executable + one licensed coding model, CPU hardware detection, resource management, process supervision, offline launch and real agent tool-calling. Validate in suitable environment.
5. Implement multi-agent roles, secure execution and approvals, Git rollback, persistent memory/learning and restart recovery, full UI/i18n.
6. Implement Windows portable distribution, embedded model handling, CI Windows build and automated smoke tests. Run them, fix failing tests and release the actual binaries. Keep improving until the mandatory acceptance criteria are demonstrably satisfied or a specific external blocker is documented.
7. Implement optional model-merging and dataset fine-tuning tools only after the baseline release is functional; do not let research work block the deliverable.
8. Supply **final answer only when there is a real result**, including GitHub URL (real, discovered), release tag and download link (real, verified), CI status, checksums, bundle size, features tested, failures and limitations. If some action is blocked by access/permissions/hardware, say exactly what was not done, why, and which single explicit user action is required. Keep the user informed with factual milestones; never stop at a plan and ask whether to continue.

## 10. Ship/no-ship criteria

**SHIP only if**: repository actually exists; meaningful implementation and tests have been pushed; app is launchable on Windows without user-installed STANICODE dependencies; UI chooses a folder; a prompt causes safe file changes; tests and task reports work; memory survives restart; portable distribution includes all required inference/runtime/model assets; branding and icon are integrated; Windows CI actually passes; and packaging + security checks have evidence. Report model/CPU capability limits candidly. Users may still need the appropriate SDK for applications they *ask STANICODE to build*, but STANICODE must not require installing SDKs to launch.

**DO NOT SHIP / DO NOT CLAIM DONE** when CI, actual bundled model, complete portable build, functional tool calls or core end-to-end smoke tests are missing. Keep implementation output and a precise blocker report instead.

**Your mission:** deliver an owned, ready-to-launch, genuinely local coding agent named **STANICODE**. Minimize handoffs to the owner. Don't substitute a mockup, incomplete scaffold, task outline or set of copy-paste installation commands for a working product.


## 11. Owner-approved logo finalization and confidentiality

- **Only `assets/STANICODE_APPROVED_LOGO.png` is approved.** It supersedes older logo concepts, and represents the aesthetic direction for all products and packages.
- Hide the initials `G`, `D`, `C` in the monogram geometry, aesthetically integrated, without labeling them or explaining their personal significance in public-facing copy.
- Never include the user's surname or full family member names in artwork, splash screen, About page, packaging, GitHub repo description, binaries, metadata, or release notes.
- Keep the GitHub repository private by default.
- Deliver a crisp production SVG and multiresolution .ico, preserve legibility from 16px to 512px and use brand-correct assets in desktop application and installer.

## 12. Deliver the complete application without manual setup

- The owner's acceptance test is only **launching the distributed application, choosing a folder and describing a coding task**. No end-user commands, model downloads, secrets, Docker/WSL/Node/Python/Ollama installation, or extension setup are acceptable for launching STANICODE.
- Produce a self-contained release artifact, ideally an offline portable ZIP with embedded inference executable, appropriately licensed model weights, packaged backend and native desktop executable. Zero-install means no *STANICODE* dependencies installed by the owner; additional software required to build arbitrary requested projects cannot be guaranteed.
- If a model's license or GitHub binary artifact size rules prevent the exact deliverable, solve distribution technically where possible without manual end-user assembly. If impossible, clearly report the blocker and **do not call the build complete**.
- Work autonomously through implementation, tests and packaging; keep actual progress honest, and do not mark mocks as production capability.
