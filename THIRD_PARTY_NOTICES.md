# Third-party notices

STANICODE source is proprietary under the accompanying LICENSE. Third-party components retain their own licenses; the application's license does not replace them.

The complete Windows candidate contains Qwen2.5-Coder-7B-Instruct Q4_K_M (Apache-2.0), llama.cpp b11669 (MIT) and its verified companion libraries, LLVM OpenMP (Apache-2.0 with LLVM exception), app-local Microsoft Visual C++ release CRTs, and Microsoft's fixed WebView2 Runtime. Exact sources, versions and model/runtime hashes are in `models/manifest.json` and `webview2/webview2-manifest.json` inside the payload. Model weights are not part of the source repository.

The packaged interpreter is CPython (PSF license), with SQLite and the HTTPX dependency closure. PyInstaller's upstream license and binary-distribution exception are included. React/React DOM use MIT; Tauri and its plugins use MIT OR Apache-2.0; Rust and other native dependencies retain the individual licenses recorded in the inventory. The collection includes some build dependencies for transparency and does not imply they are executed by the end user.

`SBOM.cdx.json` inventories versioned components and hashes the actual accompanying notices under `dependency-licenses/`. Original Cargo source archives accompany their notices, including covered MPL-2.0 sources. The pinned original llama.cpp source archive and vendored source notices are preserved as well. These source archives are for license/source availability and provenance, not additional application runtimes to install. Any modifications to STANICODE remain separate from those original upstream sources.

Microsoft WebView2's own runtime terms and third-party credits are included. Its SDK license is not a substitute for the runtime agreement. WebView2 includes Microsoft Defender SmartScreen and may collect and send usage information to Microsoft as described in its supplied terms and https://aka.ms/privacy. STANICODE itself contains no application telemetry or cloud AI calls, and its local AI workflow can operate without Internet. Microsoft runtime licensing/privacy terms apply independently.

The approved branding PNGs were supplied by the owner. The editable SVG redraw and its Windows icon/installer rasterizations are included with the source. No registered-trademark claim is made.

Development/no-model artifacts omit inference payloads and must not be described as complete offline distributions. The complete-package assembler requires a populated inventory and hash-verified license files; this integrity check does not establish legal sufficiency or clean-machine acceptance by itself.
