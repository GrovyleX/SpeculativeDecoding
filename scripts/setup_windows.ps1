# Windows one-time setup for aisehack conda env (run in Anaconda Prompt / PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Speculative Decoding — Windows setup ===" -ForegroundColor Cyan

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Error "conda not found. Install Miniconda first."
}

$envName = "aisehack"
$envs = conda env list 2>$null
if ($envs -notmatch $envName) {
    Write-Host "Creating conda env: $envName"
    conda create -n $envName python=3.11 -y
} else {
    Write-Host "Conda env '$envName' already exists"
}

Write-Host "Installing PyTorch with CUDA ..."
conda run -n $envName pip install torch --index-url https://download.pytorch.org/whl/cu124

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "Installing requirements from $root ..."
conda run -n $envName pip install -r "$root\requirements.txt"

Write-Host ""
Write-Host "Verifying GPU ..."
conda run -n $envName python -c "import torch; print('cuda:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"

Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Green
Write-Host "  1. Ensure Ethernet IP is 192.168.50.2"
Write-Host "  2. Start verifier on Fedora: bash scripts/start_verifier.sh"
Write-Host "  3. Run draft client:"
Write-Host "     conda activate $envName"
Write-Host "     cd $root"
Write-Host "     python draft/client.py --verifier http://192.168.50.1:8000"
