# Optional local Ollama adapter

The ordinary Windows launcher uses the embedded Qwen/llama.cpp bundle. No Ollama installation, account, key or manual model setup is required.

For an expert who already maintains a local Ollama service and an installed, appropriately licensed model, setting `STANICODE_ADVANCED_OLLAMA_MODEL` before launching the desktop selects the optional adapter. The equivalent backend developer flag is `--ollama-model <installed-name>`.

Only `127.0.0.1:11434` is used. The adapter checks the installed catalog, sends native JSON chat requests with a 16k context and reuses the serial roles/cancellation/approval engine. It never calls a pull, install or delete endpoint. The bundled runtime is not started in this mode, and closing STANICODE does not terminate the user's Ollama service. A missing service/model produces an unavailable status rather than silently downloading anything.

Provenance records the externally reported model digest and labels this user-configured provider; it does not claim the external model was verified against the bundled GGUF. Model quality, memory and license requirements remain those of the chosen model. Automated native-protocol fixture tests cover this adapter. An actual separately installed Ollama service/model has not been tested in this environment; default bundled inference has separate actual-model acceptance evidence.
