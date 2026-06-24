# Run the draft client using the project venv.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_draft.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "venv not found. Run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1"
}

$Verifier = "http://192.168.50.1:8010"
$Prompt = "Explain speculative decoding in one short paragraph."
$MaxNew = 64
$BlockSize = 2

# Real SD: SmolLM2-360M draft -> SmolLM2-1.7B verifier (FAST_DEMO=0)
if (-not $env:FAST_DEMO) { $env:FAST_DEMO = "0" }
if (-not $env:DRAFT_MODEL) { $env:DRAFT_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct" }

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        "--verifier" { $Verifier = $args[++$i]; continue }
        "--prompt" { $Prompt = $args[++$i]; continue }
        "--max-new-tokens" { $MaxNew = [int]$args[++$i]; continue }
        "--block-size" { $BlockSize = [int]$args[++$i]; continue }
    }
}

Write-Host "Verifier: $Verifier"
Write-Host "Draft:    $env:DRAFT_MODEL"
Write-Host "FAST_DEMO: $env:FAST_DEMO"
Write-Host ""

& $python (Join-Path $Root "draft\client.py") `
    --verifier $Verifier `
    --prompt $Prompt `
    --max-new-tokens $MaxNew `
    --block-size $BlockSize `
    --skip-wait
