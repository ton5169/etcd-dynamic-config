<#
Build & publish Python package to PyPI or TestPyPI on Windows.

- Cleans dist/build/*.egg-info (optional)
- Creates venv (if missing), installs build + twine
- Builds sdist + wheel
- (Optional) Verifies package version against current git tag vX.Y.Z
- Uploads via python -m twine to PyPI or TestPyPI
- Uses env vars PYPI_API_TOKEN / TEST_PYPI_API_TOKEN or prompts securely

Usage examples:
  .\publish.ps1 -Clean -SkipExisting
  .\publish.ps1 -Repository testpypi -Clean -SkipExisting
  .\publish.ps1 -VerifyVersionWithTag -Clean
#>

[CmdletBinding()]
param(
  [ValidateSet('pypi','testpypi')]
  [string]$Repository = 'pypi',

  [switch]$SkipExisting,

  [switch]$Clean,

  [switch]$VerifyVersionWithTag,

  [string]$VenvPath = ".venv"
)

$ErrorActionPreference = 'Stop'

function Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Warn($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Fail($m){ Write-Host "[ERROR] $m" -ForegroundColor Red }

# Optional: force UTF-8 output to reduce mojibake in some consoles
try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
} catch {}

# 1) Python available?
try {
  $pyVersion = & python -c "import sys; print(sys.version.split()[0])"
  Info "Python: $pyVersion"
} catch {
  Fail "Python not found in PATH."
  exit 1
}

# 2) Ensure venv
if (!(Test-Path $VenvPath)) {
  Info "Creating venv at $VenvPath"
  python -m venv $VenvPath
}
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
if (!(Test-Path $venvPython)) {
  Fail "venv python not found at $venvPython"
  exit 1
}

# 3) Tools
Info "Upgrading pip and installing build, twine"
& $venvPython -m pip install --upgrade pip       | Out-Null
& $venvPython -m pip install --upgrade build twine | Out-Null

# 4) Clean (optional)
if ($Clean) {
  Info "Cleaning dist/, build/, *.egg-info"
  if (Test-Path dist)  { Remove-Item dist -Recurse -Force }
  if (Test-Path build) { Remove-Item build -Recurse -Force }
  Get-ChildItem . -Filter "*.egg-info" -Directory | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
}

# 5) Build
Info "Building sdist + wheel"
& $venvPython -m build
if (!(Test-Path "dist")) {
  Fail "dist/ not found after build"
  exit 1
}

# 6) Verify version with git tag (optional)
if ($VerifyVersionWithTag) {
  # get exact tag for HEAD
  $tag = $null
  try { $tag = (git describe --tags --exact-match) 2>$null } catch {}
  if (-not $tag) {
    Fail "No exact git tag for current commit (need vX.Y.Z)."
    exit 1
  }
  $tagVersion = ($tag -replace '^[vV]','')
  Info "Git tag: $tag  -> expected package version: $tagVersion"

  # pick newest wheel and parse version from its filename: name-<ver>-py3-...
  $wheel = Get-ChildItem dist -Filter "*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $wheel) {
    Fail "No wheel in dist/"
    exit 1
  }
  $m = [regex]::Match($wheel.BaseName, '^[^-]+-(?<ver>[^-]+)-')
  if (-not $m.Success) {
    Fail "Failed to parse version from wheel name: $($wheel.Name)"
    exit 1
  }
  $pkgVer = $m.Groups['ver'].Value
  Info "Wheel version: $pkgVer"
  if ($pkgVer -ne $tagVersion) {
    Fail "Version mismatch: wheel=$pkgVer vs tag=$tagVersion"
    exit 1
  }
}

# 7) Repository URL and credentials
$repoUrl = if ($Repository -eq 'testpypi') {
  "https://test.pypi.org/legacy/"
} else {
  "https://upload.pypi.org/legacy/"
}

$env:TWINE_USERNAME = "__token__"
if ($Repository -eq 'testpypi') {
  if (-not $env:TEST_PYPI_API_TOKEN) {
    Warn "TEST_PYPI_API_TOKEN not set; prompting for token"
    $secure = Read-Host "Enter TestPyPI API token (starts with pypi-)" -AsSecureString
    $env:TWINE_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
      [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
  } else {
    $env:TWINE_PASSWORD = $env:TEST_PYPI_API_TOKEN
  }
} else {
  if (-not $env:PYPI_API_TOKEN) {
    Warn "PYPI_API_TOKEN not set; prompting for token"
    $secure = Read-Host "Enter PyPI API token (starts with pypi-)" -AsSecureString
    $env:TWINE_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
      [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
  } else {
    $env:TWINE_PASSWORD = $env:PYPI_API_TOKEN
  }
}

# 8) Upload
$twineArgs = @("upload")
if ($SkipExisting) { $twineArgs += "--skip-existing" }
$twineArgs += @("--repository-url", $repoUrl, "dist/*")

Info "Uploading to $Repository ($repoUrl)"
try {
  & $venvPython -m twine @twineArgs
  Write-Host "`n✅ Publish finished successfully." -ForegroundColor Green
} catch {
  Fail "Upload failed. See Twine output above."
  exit 1
}
