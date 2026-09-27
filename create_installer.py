import os
import io
import sys
import zipfile
import base64

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_payload():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add goal_tracker folder
        gt_dir = os.path.join(PACKAGE_DIR, "goal_tracker")
        for root, _, files in os.walk(gt_dir):
            for file in files:
                if file.endswith((".py", ".txt")):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, PACKAGE_DIR)
                    zf.write(full_path, rel_path)
        
        # Add pyproject.toml and README.md
        for top_file in ["pyproject.toml", "README.md"]:
            fp = os.path.join(PACKAGE_DIR, top_file)
            if os.path.exists(fp):
                zf.write(fp, top_file)

    buffer.seek(0)
    b64_data = base64.b64encode(buffer.read()).decode("ascii")
    return b64_data

def generate_install_ps1(b64_payload):
    ps1_content = f'''<#
.SYNOPSIS
    TrackS Global Autonomous AI Goal & Penalty Tracker Installer
.DESCRIPTION
    One-line automated installer for Windows PowerShell & Command Prompt.
    Downloads, extracts to trusted user-selected folder, configures PATH, and launches TrackS.
#>

$ErrorActionPreference = "Stop"

Write-Host @"
====================================================================
          TrackS: AUTONOMOUS AI ACCOUNTABILITY INSTALLER           
====================================================================
"@ -ForegroundColor Cyan

# 1. Verify Python is installed
Write-Host "[*] Checking Python environment..." -ForegroundColor White
$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {{
    $pythonCmd = "python"
}} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {{
    $pythonCmd = "py"
}} else {{
    Write-Host "[!] ERROR: Python 3.9+ is required but was not found in your PATH." -ForegroundColor Red
    Write-Host "    Please download and install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "    (Make sure to check 'Add Python to PATH' during installation!)" -ForegroundColor Yellow
    exit 1
}}

$pyVersion = & $pythonCmd --version 2>&1
Write-Host "[OK] Found $pyVersion" -ForegroundColor Green

# 2. Prompt user for trusted destination directory
$defaultPath = Join-Path $HOME ".tracks"
Write-Host ""
Write-Host "Where would you like to install TrackS?" -ForegroundColor Cyan
Write-Host "Press [Enter] to use default: $defaultPath" -ForegroundColor Gray
$userChoice = Read-Host "Trusted directory path"

$targetDir = $defaultPath
if (![string]::IsNullOrWhiteSpace($userChoice)) {{
    $cleanChoice = $userChoice.Trim().Trim('"').Trim("'")
    $rawPath = [System.IO.Path]::GetFullPath($cleanChoice)
    $leafName = Split-Path $rawPath -Leaf
    if ($leafName -notmatch "^(?i)tracks?$") {{
        $targetDir = Join-Path $rawPath "tracks"
    }} else {{
        $targetDir = $rawPath
    }}
}}

Write-Host "`n[*] Installing TrackS into: $targetDir" -ForegroundColor White
if (!(Test-Path $targetDir)) {{
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}}

$binDir = Join-Path $targetDir "bin"
if (!(Test-Path $binDir)) {{
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}}

# 3. Extract Embedded Application Payload
Write-Host "[*] Extracting package files..." -ForegroundColor White
$b64Payload = @"
{b64_payload}
"@

$zipBytes = [System.Convert]::FromBase64String($b64Payload)
$zipTemp = Join-Path $env:TEMP "tracks_install_$(Get-Random).zip"
[System.IO.File]::WriteAllBytes($zipTemp, $zipBytes)

Expand-Archive -Path $zipTemp -DestinationPath $targetDir -Force
Remove-Item $zipTemp -Force

# 4. Install Dependencies
Write-Host "[*] Configuring Python dependencies (rich, pydantic)..." -ForegroundColor White
& $pythonCmd -m pip install -q --no-warn-script-location rich pydantic

try {{
    & $pythonCmd -m pip install -q --no-warn-script-location -e $targetDir 2>`$null
}} catch {{
    # Standalone launchers in bin/ manage PYTHONPATH directly
}}

# 5. Create Standalone Launchers
$tracksCmd = Join-Path $binDir "tracks.cmd"
$tracksCapCmd = Join-Path $binDir "TrackS.cmd"
$sentinelCmd = Join-Path $binDir "sentinel.cmd"
$goaltrackCmd = Join-Path $binDir "goaltrack.cmd"
$ps1Launcher = Join-Path $binDir "tracks.ps1"

$cmdScript = @"
@echo off
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"
$pythonCmd -m goal_tracker %*
"@

$ps1Script = @"
`$env:PYTHONPATH = (Join-Path `$PSScriptRoot "..") + ";" + `$env:PYTHONPATH
& "$pythonCmd" -m goal_tracker `$args
"@

[System.IO.File]::WriteAllText($tracksCmd, $cmdScript)
[System.IO.File]::WriteAllText($tracksCapCmd, $cmdScript)
[System.IO.File]::WriteAllText($sentinelCmd, $cmdScript)
[System.IO.File]::WriteAllText($goaltrackCmd, $cmdScript)
[System.IO.File]::WriteAllText($ps1Launcher, $ps1Script)

# 6. Permanently Add to User PATH
Write-Host "[*] Registering 'tracks' into your system environment PATH..." -ForegroundColor White
$currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentUserPath -notlike "*$binDir*") {{
    $newPath = if ([string]::IsNullOrEmpty($currentUserPath)) {{ $binDir }} else {{ "$currentUserPath;$binDir" }}
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "[OK] Added '$binDir' to permanent User PATH!" -ForegroundColor Green
}}

# Also add to current session PATH
if ($env:PATH -notlike "*$binDir*") {{
    $env:PATH = "$env:PATH;$binDir"
}}

Write-Host @"

====================================================================
     [SUCCESS] INSTALLATION COMPLETE! TrackS IS GLOBALLY READY.
====================================================================
You can now open ANY PowerShell or Command Prompt (cmd) window and type:

    tracks        (or TrackS)

Starting TrackS now...
"@ -ForegroundColor Green

Start-Sleep -Seconds 1
& $tracksCmd
'''
    return ps1_content

def generate_install_sh(b64_payload):
    sh_content = f'''#!/usr/bin/env bash
set -e

echo -e "\\033[1;36m====================================================================\\033[0m"
echo -e "\\033[1;33m          TrackS: AUTONOMOUS AI ACCOUNTABILITY INSTALLER           \\033[0m"
echo -e "\\033[1;36m====================================================================\\033[0m"

# 1. Check Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "\\033[1;31m[!] Python 3.9+ is required but was not found.\\033[0m"
    exit 1
fi

echo -e "\\033[0;32m[OK] Found $($PYTHON_CMD --version)\\033[0m"

# 2. Destination directory prompt
DEFAULT_PATH="$HOME/.tracks"
echo ""
echo -e "\\033[1;36mWhere would you like to install TrackS?\\033[0m"
read -p "Trusted directory path [Default: $DEFAULT_PATH]: " USER_CHOICE
RAW_PATH="${{USER_CHOICE:-$DEFAULT_PATH}}"
BASE_NAME=$(basename "$RAW_PATH")
if [[ "$BASE_NAME" =~ ^[Tt]racks?$ ]]; then
    TARGET_DIR="$RAW_PATH"
else
    TARGET_DIR="$RAW_PATH/tracks"
fi

echo -e "\\033[0;37m[*] Installing TrackS into: $TARGET_DIR\\033[0m"
mkdir -p "$TARGET_DIR/bin"

# 3. Extract Payload
TMP_ZIP="/tmp/tracks_install_$RANDOM.zip"
echo "{b64_payload}" | base64 -d > "$TMP_ZIP"
unzip -q -o "$TMP_ZIP" -d "$TARGET_DIR"
rm -f "$TMP_ZIP"

# 4. Install Dependencies
echo -e "\\033[0;37m[*] Installing dependencies (rich, pydantic)...\\033[0m"
$PYTHON_CMD -m pip install -q --user rich pydantic 2>/dev/null || $PYTHON_CMD -m pip install -q rich pydantic
$PYTHON_CMD -m pip install -q --user -e "$TARGET_DIR" 2>/dev/null || true

# 5. Create launcher
LAUNCHER="$TARGET_DIR/bin/tracks"
cat << 'EOF' > "$LAUNCHER"
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
export PYTHONPATH="$DIR/..:$PYTHONPATH"
exec python3 -m goal_tracker "$@"
EOF
chmod +x "$LAUNCHER"
ln -sf "$LAUNCHER" "$TARGET_DIR/bin/TrackS"
ln -sf "$LAUNCHER" "$TARGET_DIR/bin/sentinel"
ln -sf "$LAUNCHER" "$TARGET_DIR/bin/goaltrack"

# 6. Add to PATH in shell profile
LOCAL_BIN="$HOME/.local/bin"
if [ -d "$LOCAL_BIN" ]; then
    ln -sf "$LAUNCHER" "$LOCAL_BIN/tracks"
    ln -sf "$LAUNCHER" "$LOCAL_BIN/TrackS"
fi

echo -e "\\033[1;32m====================================================================\\033[0m"
echo -e "\\033[1;32m     [SUCCESS] INSTALLATION COMPLETE! TrackS IS GLOBALLY READY.   \\033[0m"
echo -e "\\033[1;32m====================================================================\\033[0m"
echo -e "You can now run: \\033[1;33mtracks\\033[0m from any terminal."
echo ""
exec "$LAUNCHER"
'''
    return sh_content

if __name__ == "__main__":
    payload = create_payload()
    print(f"[*] Generated payload size: {len(payload)} chars")

    ps1_code = generate_install_ps1(payload)
    ps1_path = os.path.join(PACKAGE_DIR, "install.ps1")
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write(ps1_code)
    print(f"[✓] Created {ps1_path}")

    sh_code = generate_install_sh(payload)
    sh_path = os.path.join(PACKAGE_DIR, "install.sh")
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write(sh_code)
    print(f"[✓] Created {sh_path}")
