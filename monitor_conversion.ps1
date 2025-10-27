# Monitor conversion progress
# Usage: .\monitor_conversion.ps1

Write-Host "=== EPM2021 → .eph Conversion Monitor ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring (conversion will continue)`n"

$logFile = "conversion_log.txt"
$outputFile = "data\ephemerides\epm\2021\epm2021.eph"

while ($true) {
    Clear-Host
    Write-Host "=== EPM2021 → .eph Conversion Monitor ===" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'HH:mm:ss')`n" -ForegroundColor Gray

    # Check log file
    if (Test-Path $logFile) {
        Write-Host "--- Last 15 lines of log ---" -ForegroundColor Yellow
        Get-Content $logFile -Tail 15 | ForEach-Object { Write-Host $_ }

        # Count processed bodies
        $processed = (Select-String -Path $logFile -Pattern "OK \(\d+ intervals\)" -AllMatches).Matches.Count
        Write-Host "`nBodies processed: $processed / 12" -ForegroundColor Green
    } else {
        Write-Host "Log file not found yet..." -ForegroundColor Red
    }

    # Check output file size
    if (Test-Path $outputFile) {
        $size = (Get-Item $outputFile).Length
        $sizeMB = [math]::Round($size / 1MB, 2)
        Write-Host "`nOutput file: $sizeMB MB" -ForegroundColor Cyan
    } else {
        Write-Host "`nOutput file not created yet" -ForegroundColor Yellow
    }

    Write-Host "`nRefreshing in 10 seconds..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}
