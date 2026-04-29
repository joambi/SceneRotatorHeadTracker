$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv-windows"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$DistDir = Join-Path $ScriptDir "dist-windows"
$BuildDir = Join-Path $ScriptDir "build-windows"
$AppScript = Join-Path $ScriptDir "headtracker_scenerotator_tk_app.py"
$IconFile = Join-Path $ScriptDir "assets\SceneRotatorHeadTracker.ico"

if (!(Test-Path $Python)) {
    py -3.11 -m venv $VenvDir
}

& $Python -c "import tkinter" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "This Python installation does not include Tkinter. Install the official Python 3.11 build from python.org and make sure Tcl/Tk support is included."
}

& $Python -m pip install --upgrade pip
& $Python -m pip install pyheadtracker opencv-python python-osc pyinstaller

$SitePackages = & $Python -c "import site; print(next(p for p in site.getsitepackages() if 'site-packages' in p))"

$PyInstallerArgs = @(
    "--noconfirm",
    "--windowed",
    "--clean",
    "--name", "SceneRotatorHeadTracker",
    "--distpath", $DistDir,
    "--workpath", $BuildDir,
    "--specpath", $BuildDir,
    "--hidden-import", "encodings.idna",
    "--add-data", "$SitePackages\mediapipe;mediapipe",
    "--add-data", "$SitePackages\pyheadtracker\data;pyheadtracker\data"
)

if (Test-Path $IconFile) {
    $PyInstallerArgs += @("--icon", $IconFile)
}

& $Python -m PyInstaller @PyInstallerArgs $AppScript

Write-Host ""
Write-Host "Built Windows app:"
Write-Host "  $DistDir\SceneRotatorHeadTracker\SceneRotatorHeadTracker.exe"
