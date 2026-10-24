[CmdletBinding()]
param(
    [ValidateSet("Backend", "Frontend", "All")]
    [string]$Component = "All",
    [switch]$InstallDependencies,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Command
    )

    Write-Host "`n==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Verification step failed: $Name (exit code $LASTEXITCODE)"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    if ($Component -in @("Backend", "All")) {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            throw "Python is not available in PATH."
        }

        Push-Location "backend"
        try {
            if ($InstallDependencies) {
                if (Test-Path "requirements.txt") {
                    Invoke-Step "Install backend dependencies" { python -m pip install -r requirements.txt }
                }
                else {
                    Invoke-Step "Install backend project" { python -m pip install -e ".[dev]" }
                }
            }

            Invoke-Step "Backend compile check" { python -m compileall -q app tests }
            Invoke-Step "Backend tests" { python -m pytest -q }
        }
        finally {
            Pop-Location
        }
    }

    if ($Component -in @("Frontend", "All")) {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "npm is not available in PATH."
        }

        if ($InstallDependencies) {
            Invoke-Step "Install frontend dependencies" { npm --prefix frontend ci }
        }

        Invoke-Step "Frontend lint" { npm --prefix frontend run lint }
        Invoke-Step "Frontend typecheck" { npm --prefix frontend run typecheck }

        if (-not $SkipBuild) {
            Invoke-Step "Frontend production build" { npm --prefix frontend run build }
        }
    }

    Write-Host "`nAll requested Sellora verification steps passed."
}
finally {
    Pop-Location
}
