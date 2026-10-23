#Requires -Version 5.1
<#
Install prerequisites and the Suno Audacity plugin for the current Windows user.
Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
Use -CheckOnly to verify prerequisites without installing or writing files.
References:
https://learn.microsoft.com/en-us/windows/package-manager/winget/install
https://docs.python.org/3.13/using/windows.html#installing-without-ui
#>
[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
# Handle native exit codes explicitly, including on PowerShell 7.
$PSNativeCommandUseErrorActionPreference = $false

function Update-SessionPath {
    $paths = @(
        [Environment]::GetEnvironmentVariable('Path', 'User')
        [Environment]::GetEnvironmentVariable('Path', 'Machine')
        $env:Path
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')
    )
    $env:Path = ($paths | Where-Object { $_ }) -join ';'
}

function Find-Python {
    $candidates = @()
    $commands = Get-Command python.exe, python3.exe -CommandType Application -All -ErrorAction SilentlyContinue
    foreach ($command in $commands) {
        # Do not trigger the Microsoft Store installation alias.
        if ($command.Source -notlike '*\Microsoft\WindowsApps\*') {
            $candidates += $command.Source
        }
    }
    foreach ($hive in @('HKCU:\Software\Python\PythonCore',
                         'HKLM:\Software\Python\PythonCore',
                         'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
        foreach ($version in (Get-ChildItem $hive -ErrorAction SilentlyContinue)) {
            $key = Get-Item (Join-Path $version.PSPath 'InstallPath') -ErrorAction SilentlyContinue
            if ($key) {
                $executable = $key.GetValue('ExecutablePath')
                if ($executable) { $candidates += $executable }
                $directory = $key.GetValue('')
                if ($directory) { $candidates += Join-Path $directory 'python.exe' }
            }
        }
    }
    # Also find a fresh per-user install before the shell's PATH has refreshed.
    $candidates += Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\python.exe') -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName
    $probe = @'
import sys, pathlib
assert sys.version_info >= (3, 10)
assert pathlib.Path(sys.executable).with_name('pythonw.exe').is_file()
import tkinter
from tkinter import ttk
root = tkinter.Tk()
root.withdraw()
ttk.Frame(root).destroy()
root.destroy()
print(sys.executable)
'@
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $result = @(& $candidate -I -c $probe 2>$null)
            if ($LASTEXITCODE -eq 0 -and $result.Count -gt 0) {
                return [string]$result[-1]
            }
        } catch { continue }
    }
    return $null
}

function Find-MediaTool([string]$Name) {
    $candidates = @()
    $configured = [Environment]::GetEnvironmentVariable('SUNO_' + $Name.ToUpperInvariant())
    if ($configured) { $candidates += $configured }
    $candidates += Get-Command "$Name.exe" -CommandType Application -All -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Source
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            & $candidate -version 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch { continue }
    }
    return $null
}

function Install-WinGetPackage([string]$Id, [string[]]$ExtraArguments = @()) {
    $winget = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'WinGet is required to install missing dependencies. Install/update App Installer from https://apps.microsoft.com/detail/9NBLGGH4NNS1 then reopen PowerShell and retry.'
    }
    Write-Host "Installing $Id for the current user..."
    $arguments = @('install', '--id', $Id, '--exact', '--source', 'winget',
                   '--scope', 'user', '--silent', '--accept-package-agreements',
                   '--accept-source-agreements', '--disable-interactivity') + $ExtraArguments
    & $winget.Source @arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "WinGet failed for $Id (exit $LASTEXITCODE). See its output above, resolve the error, then run this script again."
    }
    Update-SessionPath
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'This installer requires Windows.' }
    $installer = Join-Path $PSScriptRoot 'install.py'
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw 'Keep install.ps1 in the project folder alongside install.py.'
    }
    Update-SessionPath
    Write-Host 'Checking Python 3.10+, Tkinter and pythonw...'
    $pythonExe = Find-Python
    if (-not $pythonExe -and -not $CheckOnly) {
        # Use the supported 3.13 line; explicitly include Tcl/Tk and avoid a global launcher.
        Install-WinGetPackage 'Python.Python.3.13' @('--force', '--custom',
            'InstallAllUsers=0 Include_tcltk=1 Include_launcher=0 PrependPath=1')
        $pythonExe = Find-Python
    }
    if (-not $pythonExe) {
        throw 'No working Python 3.10+ with Tkinter and pythonw found. If Python is already installed, use its installer > Modify > tcl/tk and IDLE, then retry.'
    }
    Write-Host "Python + Tkinter: $pythonExe"

    $ffmpegExe = Find-MediaTool 'ffmpeg'
    $ffprobeExe = Find-MediaTool 'ffprobe'
    if ((-not $ffmpegExe -or -not $ffprobeExe) -and -not $CheckOnly) {
        Install-WinGetPackage 'Gyan.FFmpeg' @('--force')
        $ffmpegExe = Find-MediaTool 'ffmpeg'
        $ffprobeExe = Find-MediaTool 'ffprobe'
    }
    if (-not $ffmpegExe -or -not $ffprobeExe) {
        throw 'ffmpeg and ffprobe must both run successfully. Check PATH or set SUNO_FFMPEG / SUNO_FFPROBE to their executable paths, then retry.'
    }
    Write-Host "FFmpeg:  $ffmpegExe"
    Write-Host "FFprobe: $ffprobeExe"
    if ($CheckOnly) {
        Write-Host 'Checks passed. No packages or plugin files were installed.'
        exit 0
    }

    # install.py records these paths in the helper launcher, even with a stale Explorer PATH.
    $env:SUNO_FFMPEG = $ffmpegExe
    $env:SUNO_FFPROBE = $ffprobeExe
    Write-Host 'Running install.py...'
    Push-Location -LiteralPath $PSScriptRoot
    try {
        & $pythonExe $installer
        if ($LASTEXITCODE -ne 0) { throw "install.py failed (exit $LASTEXITCODE)." }
    } finally { Pop-Location }
    Write-Host ''
    Write-Host 'Done. Restart Audacity or rescan plugins, then open Start Suno Helper.vbs.' -ForegroundColor Green
    Write-Host 'In Audacity: Tools > Nyquist > Suno Audacity Importer > Suno URL Import.'
} catch {
    [Console]::Error.WriteLine('Installation failed: ' + $_.Exception.Message)
    exit 1
}
