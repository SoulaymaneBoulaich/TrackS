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
    Sentinel-X Global Autonomous AI Goal & Penalty Tracker Installer
.DESCRIPTION
    One-line automated installer for Windows PowerShell.
    Downloads, extracts to trusted user-selected folder, configures PATH, and launches Sentinel-X.
#>

$ErrorActionPreference = "Stop"

Write-Host @"
====================================================================
       SENTINEL-X: AUTONOMOUS AI ACCOUNTABILITY INSTALLER           
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
$defaultPath = Join-Path $HOME ".sentinel-x"
Write-Host ""
Write-Host "Where would you like to install Sentinel-X?" -ForegroundColor Cyan
Write-Host "Press [Enter] to use default: $defaultPath" -ForegroundColor Gray
$userChoice = Read-Host "Trusted directory path"

$targetDir = $defaultPath
if (![string]::IsNullOrWhiteSpace($userChoice)) {{
    $targetDir = [System.IO.Path]::GetFullPath($userChoice.Trim('"'))
}}

Write-Host "`n[*] Installing Sentinel-X into: $targetDir" -ForegroundColor White
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
$zipTemp = Join-Path $env:TEMP "sentinel_install_$(Get-Random).zip"
[System.IO.File]::WriteAllBytes($zipTemp, $zipBytes)

Expand-Archive -Path $zipTemp -DestinationPath $targetDir -Force
Remove-Item $zipTemp -Force

# 4. Install Dependencies
Write-Host "[*] Configuring Python dependencies (rich, pydantic)..." -ForegroundColor White
& $pythonCmd -m pip install -q --no-warn-script-location rich pydantic
& $pythonCmd -m pip install -q --no-warn-script-location -e $targetDir

# 5. Create Standalone Launchers
$sentinelCmd = Join-Path $binDir "sentinel.cmd"
$goaltrackCmd = Join-Path $binDir "goaltrack.cmd"
$ps1Launcher = Join-Path $binDir "sentinel.ps1"

$cmdScript = @"
@echo off
$pythonCmd -m goal_tracker %*
"@

$ps1Script = @"
& "$pythonCmd" -m goal_tracker `$args
"@

[System.IO.File]::WriteAllText($sentinelCmd, $cmdScript)
[System.IO.File]::WriteAllText($goaltrackCmd, $cmdScript)
[System.IO.File]::WriteAllText($ps1Launcher, $ps1Script)

# 6. Permanently Add to User PATH
Write-Host "[*] Registering 'sentinel' into your system environment PATH..." -ForegroundColor White
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
   [SUCCESS] INSTALLATION COMPLETE! SENTINEL-X IS GLOBALLY READY.
====================================================================
You can now open ANY PowerShell or Command Prompt window and type:

    sentinel      (or goaltrack)

Starting Sentinel-X now...
"@ -ForegroundColor Green

Start-Sleep -Seconds 1
& $sentinelCmd
'''
    return ps1_content

def generate_install_sh(b64_payload):
    sh_content = f'''#!/usr/bin/env bash
set -e

echo -e "\\033[1;36m====================================================================\\033[0m"
echo -e "\\033[1;33m       SENTINEL-X: AUTONOMOUS AI ACCOUNTABILITY INSTALLER           \\033[0m"
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
DEFAULT_PATH="$HOME/.sentinel-x"
echo ""
echo -e "\\033[1;36mWhere would you like to install Sentinel-X?\\033[0m"
read -p "Trusted directory path [Default: $DEFAULT_PATH]: " USER_CHOICE
TARGET_DIR="${{USER_CHOICE:-$DEFAULT_PATH}}"

echo -e "\\033[0;37m[*] Installing Sentinel-X into: $TARGET_DIR\\033[0m"
mkdir -p "$TARGET_DIR/bin"

# 3. Extract Payload
TMP_ZIP="/tmp/sentinel_install_$RANDOM.zip"
echo "{b64_payload}" | base64 -d > "$TMP_ZIP"
unzip -q -o "$TMP_ZIP" -d "$TARGET_DIR"
rm -f "$TMP_ZIP"

# 4. Install Dependencies
echo -e "\\033[0;37m[*] Installing dependencies (rich, pydantic)...\\033[0m"
$PYTHON_CMD -m pip install -q --user rich pydantic
$PYTHON_CMD -m pip install -q --user -e "$TARGET_DIR"

# 5. Create launcher
LAUNCHER="$TARGET_DIR/bin/sentinel"
cat << EOF > "$LAUNCHER"
#!/usr/bin/env bash
exec $PYTHON_CMD -m goal_tracker "\\$@"
EOF
chmod +x "$LAUNCHER"
ln -sf "$LAUNCHER" "$TARGET_DIR/bin/goaltrack"

# 6. Add to PATH in shell profile
LOCAL_BIN="$HOME/.local/bin"
if [ -d "$LOCAL_BIN" ]; then
    ln -sf "$LAUNCHER" "$LOCAL_BIN/sentinel"
    ln -sf "$LAUNCHER" "$LOCAL_BIN/goaltrack"
fi

echo -e "\\033[1;32m====================================================================\\033[0m"
echo -e "\\033[1;32m   [SUCCESS] INSTALLATION COMPLETE! SENTINEL-X IS GLOBALLY READY.\\033[0m"
echo -e "\\033[1;32m====================================================================\\033[0m"
echo -e "You can now run: \\033[1;33msentinel\\033[0m from any terminal."
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
