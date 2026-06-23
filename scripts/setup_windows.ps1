# One-time setup using system Python (no conda).
# Run from project root or anywhere:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Speculative Decoding - Windows setup ===" -ForegroundColor Cyan
Write-Host "Project: $Root"

function Find-Python {
    $candidates = @(
        { if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.13 -c "import sys; print(sys.executable)" 2>$null } },
        { if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.12 -c "import sys; print(sys.executable)" 2>$null } },
        { if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.11 -c "import sys; print(sys.executable)" 2>$null } },
        { if (Get-Command python -ErrorAction SilentlyContinue) { & python -c "import sys; print(sys.executable)" 2>$null } },
        { if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -c "import sys; print(sys.executable)" 2>$null } },
        { if (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 -c "import sys; print(sys.executable)" 2>$null } }
    )
    foreach ($getExe in $candidates) {
        $exe = & $getExe
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    return $null
}

$pyExe = Find-Python
if (-not $pyExe) {
    Write-Error "Python 3 not found. Install Python 3.10+ and ensure 'py' or 'python' is on PATH."
}

Write-Host "Using Python: $pyExe"

$venv = Join-Path $Root ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
if ((Test-Path $venv) -and -not (Test-Path $venvPython)) {
    Write-Host "Removing incomplete venv ..."
    Remove-Item -Recurse -Force $venv
}
if (-not (Test-Path $venv)) {
    Write-Host "Creating venv at $venv ..."
    & $pyExe -m venv $venv
} else {
    Write-Host "venv already exists: $venv"
}

$pip = Join-Path $venv "Scripts\pip.exe"
$python = Join-Path $venv "Scripts\python.exe"

Write-Host "Upgrading pip ..."
& $pip install --upgrade pip

Write-Host "Installing PyTorch with CUDA ..."
& $pip install torch --index-url https://download.pytorch.org/whl/cu124

Write-Host "Installing project requirements ..."
& $pip install -r (Join-Path $Root "requirements.txt")

Write-Host ""
Write-Host "Verifying GPU ..."
& $python -c @"
import torch
print('cuda:', torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
"@

Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Green
Write-Host "  1. Ensure Ethernet IP is 192.168.50.2"
Write-Host "  2. Start verifier on Fedora: bash scripts/start_verifier.sh"
Write-Host "  3. Run draft client:"
Write-Host "     powershell -ExecutionPolicy Bypass -File scripts\run_draft.ps1"
Write-Host ""
Write-Host "Or manually:"
Write-Host "     cd $Root"
Write-Host "     .\.venv\Scripts\python.exe draft\client.py --verifier http://192.168.50.1:8000"
