# setup-audio.ps1 — Helper for Pi Windows Notification Extension
# Usage: powershell -ExecutionPolicy Bypass -File setup-audio.ps1

$extDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$nircmdUrl = "https://www.nirsoft.net/utils/nircmd-x64.zip"
$nircmdZip = Join-Path $env:TEMP "nircmd-x64.zip"
$nircmdExe = Join-Path $extDir "nircmd.exe"

Write-Host "`n=== Pi Windows Notify - Audio Setup ===`n" -ForegroundColor Cyan

# ── Step 1: Ensure nircmd.exe is present ────────────────────────────────
if (Test-Path $nircmdExe) {
    Write-Host "[OK] nircmd.exe already exists at:" -ForegroundColor Green
    Write-Host "     $nircmdExe" -ForegroundColor Gray
} else {
    Write-Host "[INFO] Downloading nircmd.exe from NirSoft..." -ForegroundColor Yellow
    
    try {
        # Check if already downloaded but not extracted
        $zipFile = Join-Path $extDir "nircmd-x64.zip"
        if (-not (Test-Path $zipFile)) {
            Write-Host "  Downloading..." -NoNewline
            Invoke-WebRequest -Uri $nircmdUrl -OutFile $nircmdZip -UseBasicParsing | Out-Null
            Write-Host " done." -ForegroundColor Green
        }

        # Extract
        Write-Host "  Extracting nircmd.exe..." -NoNewline
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($nircmdZip, $extDir)
        
        # Move if inside a subfolder (zip structure varies by version)
        $found = Get-ChildItem $extDir -Filter "nircmd.exe" -Recurse | Select-Object -First 1
        if ($found -and $found.FullName -ne $nircmdExe) {
            Copy-Item $found.FullName $nircmdExe -Force
            Remove-Item $found.FullName -ErrorAction SilentlyContinue
        }

        Remove-Item $nircmdZip -ErrorAction SilentlyContinue
        Write-Host " done." -ForegroundColor Green
    } catch {
        Write-Host "" -ForegroundColor Red
        Write-Host "[ERROR] Failed to download nircmd.exe:" $_.Exception.Message -ForegroundColor Red
        Write-Host "`nPlease download manually from: https://www.nirsoft.net/utils/nircmd-x64.zip" -ForegroundColor Yellow
        Write-Host "Extract nircmd.exe and place it in:" -ForegroundColor Yellow
        Write-Host "  $extDir`n" -ForegroundColor Gray
        exit 1
    }
}

# ── Step 2: List available audio devices ───────────────────────────────
Write-Host "`n=== Available Audio Output Devices ===`n" -ForegroundColor Cyan

try {
    # Use PowerShell's built-in Get-AudioEndpoint cmdlet (Windows 10+) or nircmd fallback
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        try {
            $devices = Get-AudioEndpoint | Where-Object { $_.Direction -eq 'Play' } | ForEach-Object {
                [PSCustomObject]@{ Name = $_.FriendlyName; Index = $_.Index }
            }
            
            if ($devices.Count -gt 0) {
                Write-Host "PowerShell Audio Endpoints:" -ForegroundColor Gray
                foreach ($d in $devices) {
                    Write-Host "  [$($d.Index)] $($d.Name)" -ForegroundColor White
                }
                
                # Also check nircmd for additional devices
                $nircmdOutput = & "$nircmdExe" listaudiodvices 2>&1
                if ($LASTEXITCODE -eq 0 -and $nircmdOutput.Trim()) {
                    Write-Host "`nNirCmd Audio Devices:" -ForegroundColor Gray
                    foreach ($line in $nircmdOutput.Split("`r`n")) {
                        $parts = $line.Trim().Split("`t")
                        if ($parts.Count -ge 3) {
                            Write-Host "  [$($parts[0].Trim())] $($parts[2].Trim())" -ForegroundColor White
                        }
                    }
                }
            } else {
                throw "No devices found via PowerShell"
            }
        } catch {
            # Fallback to nircmd only
            $nircmdOutput = & "$nircmdExe" listaudiodvices 2>&1
            if ($LASTEXITCODE -eq 0 -and $nircmdOutput.Trim()) {
                foreach ($line in $nircmdOutput.Split("`r`n")) {
                    $parts = $line.Trim().Split("`t")
                    if ($parts.Count -ge 3) {
                        Write-Host "  [$($parts[0].Trim())] $($parts[2].Trim())" -ForegroundColor White
                    }
                }
            } else {
                throw "Could not enumerate devices"
            }
        }
    } else {
        # PowerShell 5.x fallback — use nircmd only
        $nircmdOutput = & "$nircmdExe" listaudiodvices 2>&1
        foreach ($line in $nircmdOutput.Split("`r`n")) {
            $parts = $line.Trim().Split("`t")
            if ($parts.Count -ge 3) {
                Write-Host "  [$($parts[0].Trim())] $($parts[2].Trim())" -ForegroundColor White
            }
        }
    }

} catch {
    Write-Host "[ERROR] Could not list audio devices: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Configuration ===`n" -ForegroundColor Cyan
$configFile = Join-Path $extDir "config.json"

if (Test-Path $configFile) {
    Write-Host "Current config:" -ForegroundColor Gray
    Get-Content $configFile | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    
    # Prompt for device name
    Write-Host ""
    $deviceName = Read-Host "Enter the exact device name from above (or press Enter to keep empty/use default)"
    if ($deviceName.Trim()) {
        try {
            $json = Get-Content $configFile -Raw | ConvertFrom-Json
            $json.audio_output_device = $deviceName.Trim()
            $json.play_sound = $true  # Enable sound when setting a device
            
            $json | ConvertTo-Json -Depth 10 | Set-Content $configFile
            Write-Host "`n[OK] Updated config.json with audio device: '$($deviceName.Trim())'" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed to update config: $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "No config.json found. Create one at:" -ForegroundColor Yellow
    Write-Host "  $configFile`n" -ForegroundColor Gray
}

Write-Host "`n=== Done ===`n" -ForegroundColor Cyan
Write-Host "Remember to restart Pi or run /reload after changing the config." -ForegroundColor DarkGray
