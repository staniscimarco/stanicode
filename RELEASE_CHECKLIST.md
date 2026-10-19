# Release acceptance

- [x] Actual repository and owner-authorized public source push
- [x] Observed successful Linux and Windows CI and native development installer
- [x] Owner installed the no-model development installer
- [x] Actual pinned licensed model and CPU runtime acquired and hash-verified on Windows
- [x] Microsoft fixed WebView2 acquired and publisher verified
- [x] Fixed Python/Node/npm/offline Rust validation recipes
- [x] Approval nonces, serial roles, local Git recovery without changing the index
- [x] Test-backed local memory with provenance, search/export/deletion
- [x] Actual model generates a project that passes frozen-backend tests and independent review
- [x] Actual native Windows UI/offline acceptance, shutdown and restart (hosted runner)
- [x] Complete applicable runtime/dependency license texts and CycloneDX SBOM
- [x] Complete portable archive, actual download URL, size and SHA-256 ([receipt](docs/WINDOWS_DELIVERY.md))
- [x] Actual portable PE import audit
- [x] Approved private Node/npm SDK installation and actual npm test evidence
- [x] Native approval cancellation, rollback after restart and memory deletion preserving history
- [ ] Dedicated clean Windows 10/11 acceptance
- [x] Implemented security boundary reviewed and regression-tested, plus real-model/native smoke; no penetration-test or OS sandbox claim
- [x] Editable vector master and small-size/accessibility branding review (owner approval remains separate)
- [x] Advanced local Ollama adapter implemented and protocol-tested; installed-service acceptance remains unrun
- [x] Experimental reviewed-dataset and LoRA/MergeKit preparation; actual training/merge/GPU evaluation unrun

Do not publish a completed release or claim production readiness until the required acceptance evidence exists. Hosted-runner tests are distinct from clean-machine and owner hardware tests. Optional research training may remain unsupported when hardware is unsuitable; report that honestly.
