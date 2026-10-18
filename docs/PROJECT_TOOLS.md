# Optional project tools

STANICODE's own UI, model and Python validation runtime are bundled. Opening the application never downloads or installs Node.js, Git, Rust or a compiler.

JavaScript projects can require Node.js/npm. On Windows x64, open **Settings → JavaScript project tools** (Italian: **Impostazioni → Strumenti per i progetti JavaScript**) and choose setup. The app first asks for explicit approval of the official download and private destination. Cancellation does not download or install anything. Existing active coding tasks must finish or be cancelled first.

The managed baseline is Node.js **24.19.0**, from:

`https://nodejs.org/dist/v24.19.0/node-v24.19.0-win-x64.zip`

SHA-256: `57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73`

Setup verifies the pinned archive hash and a valid OpenJS Foundation Authenticode signature, rejects unsafe archive paths, checks the actual runtime version and records file hashes. The official distribution, including its complete LICENSE, remains intact. Partial or unverified installations are not activated. Approved repair preserves an existing app-managed directory as a backup; unknown pre-existing directories are not overwritten.

Installation stays in private application data. The app does not change system/user PATH, registry settings or administrator privileges. Only approved project validation processes receive the managed SDK directory in their environment. A subsequent app start rechecks its installed file hashes. Automatic setup requires Internet and at least 1 GiB free disk; the core local AI remains usable when setup is declined or fails.

This installs a project SDK, not arbitrary project dependencies. Node tests execute project code only after the ordinary file/test approval. npm validation remains `npm test --offline --ignore-scripts=false`; success requires a nonzero passing-test count from TAP, Jest, Vitest or Mocha, with no reported failures. Exit zero alone or an echo-only script is insufficient. Missing dependencies produce a real failure. Installing project packages or native addons is a separate operation under the user's control. Cargo/Rust validation detects the available toolchain; automatic Rust/MSVC/Windows SDK provisioning is not provided. Those project requirements are distinct from STANICODE's bundled runtime.

The advanced standalone entry point is `payload/stanicode-agent.exe --project-tools --root <private-data>/tools --approve-setup`. Close active tasks before using it. The normal owner flow uses Settings and does not need Python or command-line configuration.

Verification is split between deterministic approval/hash/path safeguards, UI consent tests and a separate Windows workflow that downloads the actual official SDK and runs real Node/npm test projects. No simulated provisioning fixture is evidence that the real Windows setup passed.
