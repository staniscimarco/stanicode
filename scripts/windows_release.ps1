$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
# This script deliberately fails without a real verified model/runtime bundle.
python scripts/verify_bundle.py models
if ($LASTEXITCODE -ne 0) { throw 'Model/runtime verification failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
npm ci --no-fund --no-audit
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
python scripts/package_agent.py
if ($LASTEXITCODE -ne 0) { throw 'Backend packaging failed' }
npm run desktop -- build --no-bundle
if ($LASTEXITCODE -ne 0) { throw 'Native Windows build failed' }
python scripts/smoke_real_inference.py --agent .local/package/stanicode-agent.exe --bundle .local/package/models
if ($LASTEXITCODE -ne 0) { throw 'Real-model acceptance failed' }
# Fixed WebView2, dependency licenses and CycloneDX SBOM must already be staged.
python scripts/build_portable.py --executable apps/desktop/src-tauri/target/release/stanicode.exe
if ($LASTEXITCODE -ne 0) { throw 'Portable verification/assembly failed' }
# Candidate only: real inference and clean Windows acceptance must pass before release.
