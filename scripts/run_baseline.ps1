# Run baseline comparison using the project venv.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_baseline.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "venv not found. Run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1"
}

$Verifier = "http://192.168.50.1:8010"

for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq "--verifier") { $Verifier = $args[++$i] }
}

& $python (Join-Path $Root "bench\baseline.py") --verifier $Verifier @args
