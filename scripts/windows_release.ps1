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
npm run desktop -- build
if ($LASTEXITCODE -ne 0) { throw 'Native Windows build failed' }
# Tauri's NSIS installer is a development artifact until clean-Windows tests pass.
Get-ChildItem apps/desktop/src-tauri/target/release/bundle -Recurse -File | ForEach-Object {
  $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$hash  $($_.Name)" | Out-File -Encoding utf8 "$($_.FullName).sha256"
}
