# Experimental local research preparation

This optional workflow prepares reviewed examples, a LoRA configuration and compatible-checkpoint MergeKit input. It never trains, merges, downloads a model, changes the active model or promotes weights. The normal Windows app does not depend on any research SDK. Actual training and MergeKit execution have not been validated on owner hardware or in CI; the CPU/16 GB baseline is unsupported for training.

The packaged backend exposes preparation without a separate Python installation:

```powershell
.\payload\stanicode-agent.exe --research prepare --memory-export memory.json --report session.json --base-checkpoint C:\Research\TrainableCheckpoint --output C:\Research\NewPreparation --approve-export
```

Export memory and the corresponding completed session reports from STANICODE. Review source ownership, consent and privacy before passing `--approve-export`. Secret pattern filtering is incomplete and cannot replace this review. Only matched memory records from completed tasks with actual-test and independent-review event provenance are eligible; changed patch hashes, failed tasks and explicitly simulated model provenance are rejected. Reports are local, editable data, not cryptographic attestations. Preparation never executes their code. Existing output directories are refused.

A local Hugging Face checkpoint directory must provide architecture metadata and `tokenizer.json`. The bundled quantized GGUF is an inference artifact, not a trainable checkpoint. Floating-point safetensors are required to validate a merge. LoRA preparation can generate a configuration before weights are available, but it remains preparation only. Check model licenses separately before training, combining or redistributing weights.

Outputs include `dataset.jsonl`, an Axolotl-style `lora-config.yml` (JSON syntax is valid YAML), a provenance manifest and fixed held-out benchmark requests. The configuration uses Qwen2/Llama/Mistral projection modules, rank 8 and 2048-token sequences. It is a starting configuration for advanced review; trainer integration is explicitly unvalidated. Fewer than 20 reviewed examples is insufficient for the recommended initial experiment. GPU hardware, compatible trainer dependencies and memory must be evaluated separately; no optional ML stack is installed or invoked automatically.

For merge preparation:

```powershell
.\payload\stanicode-agent.exe --research prepare-merge --checkpoint C:\Research\ModelA --checkpoint C:\Research\ModelB --output C:\Research\NewMergePreparation
```

The validator checks architecture/dimension and attention/rotary configuration, exact tokenizer file hashes, floating tensor names and shapes, valid data offsets and whole weight-file hashes. It rejects quantized inputs, incompatible tokenizers/shapes and truncated headers. The generated linear `mergekit.yml` references only local paths. A separate compatible MergeKit installation may later run `mergekit-yaml mergekit.yml merged-model`; this command has not been run by the preparation tool. Review the configuration first and keep network access disabled (`HF_HUB_OFFLINE=1`) for local research.

Before manual promotion, run each held-out request against the baseline and candidate using fresh workspaces and fresh local task data. Preserve each actual task report, tests, model/runtime hashes, sampling/context settings, machine information and elapsed time. Keep the held-out requests out of the training set; exact request duplicates are rejected by the exporter. A candidate must pass objective tests and independent review without regression. Conversion to GGUF and replacement of the verified active manifest are separate, explicitly reviewed operations. The preparation manifest always records `promotion_allowed: false`; no benchmark success or learning is invented.

From source, the equivalent entry point is `python services/agent/server.py --research ...`. Unit tests use clearly labeled miniature data fixtures, not trained checkpoints or real model evidence.
