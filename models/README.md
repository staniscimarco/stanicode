# Verified offline inference payload

Weights and executable payloads are excluded from Git. The Windows complete workflow acquires them on the build machine, packages them inside the distributable and performs real inference acceptance. End users do not download a model separately, create manifests or install Ollama. There is no first-launch model download.

Pinned baseline:

| Component | Version | License | SHA-256 |
| --- | --- | --- | --- |
| Qwen2.5-Coder-7B-Instruct GGUF Q4_K_M | `13fb94bfda8c8cf22497dc57b78f391a9acb426a` | Apache-2.0 | `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c` |
| llama.cpp Windows x64 CPU archive | `b11669` | MIT, plus bundled component notices | `37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b` |

The GGUF is 4,683,073,536 bytes. The runtime uses one model, serial roles, a 16k-token context and a conservative minimum of 7 GiB available RAM. A 16 GB machine is the baseline target; CPU inference can take minutes, and this threshold does not guarantee performance on every machine. The app reports memory pressure and payload failures rather than simulating readiness.

Build-machine acquisition is implemented in `scripts/prepare_model.py`. It verifies upstream hashes, actual license texts, the pinned llama.cpp source archive and Microsoft signatures on the designated app-local release CRTs. It generates `models/manifest.json` with model/runtime source, exact versions, licenses, RAM policy and a hash for every companion/support file. Packaging and startup share `scripts/verify_bundle.py`; payload corruption prevents readiness.

Actual Windows acceptance has passed generated-file approval, real bundled Python tests and independent model review; see [verification status](../docs/STATUS.md). This does not establish completed native/offline or clean Windows acceptance. The complete portable archive remains a delivery gate until its build actually succeeds.

For the full reproducible build, use `.github/workflows/windows-complete.yml` or `scripts/windows_release.ps1` on a suitable Windows build machine. Advanced installed Ollama is optional and documented separately in [advanced local models](../docs/ADVANCED_LOCAL_MODELS.md).
