# Development security boundary

This is an early development version, not a hardened agent. File proposals require approval and path checks reject traversal, symlinks, Git metadata and `.env` files. A single task writes at a time. SQLite snapshots permit rollback and refuse to overwrite external edits. Backend requests require a random per-process bearer token, allowed Origin and exact loopback Host. Only the native shell receives the token.

Approved Python tests execute arbitrary workspace code with the current user's permissions. They are **not sandboxed**. Do not open untrusted projects or approve generated tests without review. A command allowlist does not restrict what Python code can do. Concurrent hostile filesystem changes are not contained. Linux process groups and Windows Job Objects provide lifecycle cleanup, not filesystem/network isolation. The Windows real-model acceptance exercises backend crash cleanup of the model process. File/prompt contents can contain sensitive data; context filtering is incomplete and SQLite task records include prompts, diffs and logs. Keep the local data directory private. The core implements no cloud AI requests or application telemetry; Microsoft's bundled WebView2 has its own data collection and SmartScreen terms, disclosed in the application and bundled notices.

Model binaries and weights must be verified with SHA-256 and audited licenses before launch. A digest from the same untrusted source is not proof of authenticity. Download manifests through a trusted, reviewed release process.

Do not publish vulnerability details or personal code through issue trackers. Report privately to the repository owner; a dedicated security contact has not yet been configured.
