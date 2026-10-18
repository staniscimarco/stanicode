# Offline payload — not present

No weights or inference binaries are included in this source checkout. The application must report unavailable inference rather than simulate readiness.

The private product specification proposes Qwen2.5-Coder-7B-Instruct GGUF Q4 with llama.cpp. This is a candidate, not a validated shipped model. License, exact upstream revisions, RAM and tool-protocol reliability still require evaluation. A real bundle needs:

```json
{
  "runtime": {"file": "bin/llama-server.exe", "sha256": "ACTUAL_SHA256", "source": "UPSTREAM_URL", "version": "EXACT_REVISION", "license": "MIT", "license_file": "licenses/llama.cpp.txt"},
  "model": {"file": "coding-model.gguf", "sha256": "ACTUAL_SHA256", "source": "UPSTREAM_URL", "version": "EXACT_REVISION", "license": "ACTUAL_LICENSE", "license_file": "licenses/model.txt", "minimum_available_ram_bytes": "MEASURED_POSITIVE_INTEGER"}
}
```

Store it as `models/manifest.json`. Include all companion libraries and actual license texts. Never substitute invented digests. Run `python scripts/verify_bundle.py models` before packaging. The release script fails when these prerequisites are missing. Large weights belong in verified packaging storage, never Git. No download happens at first launch.

The final manifest must also list `support_files` (file + sha256 for each companion DLL/library). Startup and packaging use the same verifier. The RAM requirement is a measured positive integer, never a placeholder in a release. `scripts/smoke_real_inference.py` exercises the actual packaged backend and real model; it deliberately fails without the payload.
