$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
# Build prerequisites: Windows x64, Python 3.12, Node 24, Rust,
# VS2022 C++ developer shell and system Edge. Users need none of these.
function Invoke-Checked([string]$Label, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Label failed (exit $LASTEXITCODE)" }
}
Invoke-Checked 'Build dependencies' { python -m pip install -r requirements-dev.txt -r requirements-build.txt -r requirements-acceptance.txt }
Invoke-Checked 'Frontend dependencies' { npm ci --no-fund --no-audit }
Invoke-Checked 'Actual Windows Firewall preflight' { python scripts/check_windows_firewall.py }
Invoke-Checked 'Backend validation' { python scripts/ci_tests.py }
Invoke-Checked 'UI validation' { npm run test:ui }
Invoke-Checked 'Pinned model and CPU runtime' { python scripts/prepare_model.py }
Invoke-Checked 'Standalone backend' { python scripts/package_agent.py }
Invoke-Checked 'Signed WebView2 and Microsoft notices' { python scripts/prepare_windows_runtime.py }
Invoke-Checked 'Actual dependency licenses and SBOM' { python scripts/collect_licenses.py }
Invoke-Checked 'Actual model coding and independent review' { python scripts/smoke_real_inference.py --agent .local/package/stanicode-agent.exe --bundle .local/package/models }
Push-Location apps/desktop
try {
    Invoke-Checked 'Native desktop' { node ../../node_modules/@tauri-apps/cli/tauri.js build --no-bundle }
} finally { Pop-Location }
# Firewall rules require an elevated build shell and are removed by the test.
Invoke-Checked 'Actual native offline UI and restart' { python scripts/smoke_native_windows.py --executable apps/desktop/src-tauri/target/release/stanicode.exe }
Invoke-Checked 'Portable PE imports' { python scripts/audit_windows_dependencies.py --executable apps/desktop/src-tauri/target/release/stanicode.exe }
Invoke-Checked 'Verified portable assembly' { python scripts/build_portable.py --executable apps/desktop/src-tauri/target/release/stanicode.exe }
# Candidate only: dedicated clean Windows 10/11 acceptance is a separate gate.
