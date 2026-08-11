param(
    [string]$SourceDir = "dist/PortfolioTracker",
    [string]$OutputDir = "release",
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$ResolvedSource = (Resolve-Path (Join-Path $ProjectRoot $SourceDir)).Path
$ResolvedOutput = Join-Path $ProjectRoot $OutputDir
$Definition = Join-Path $PSScriptRoot "PortfolioTracker.iss"
$Compiler = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6/ISCC.exe"

if (-not (Test-Path $Compiler)) {
    throw "Inno Setup 6 bulunamadı: $Compiler"
}

New-Item -ItemType Directory -Force -Path $ResolvedOutput | Out-Null
& $Compiler "/DSourceDir=$ResolvedSource" "/DOutputDir=$ResolvedOutput" "/DAppVersion=$Version" $Definition
if ($LASTEXITCODE -ne 0) {
    throw "Windows installer derlemesi başarısız oldu."
}

$Installer = Join-Path $ResolvedOutput "PortfolioTracker-$Version-Windows-x64-Setup.exe"
if (-not (Test-Path $Installer)) {
    throw "Windows installer bulunamadı: $Installer"
}

$Hash = (Get-FileHash -Algorithm SHA256 $Installer).Hash.ToLowerInvariant()
"$Hash  $(Split-Path -Leaf $Installer)" | Set-Content -Encoding ascii "$Installer.sha256"
Write-Host "Windows installer hazır: $Installer"
