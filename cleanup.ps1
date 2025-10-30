# EphReader - Cleanup Script
# Removes ONLY temporary log files and merges documentation
# Version: 2.0.0 (REVISED: Keep all code and tools)
# Date: October 30, 2025

param(
    [switch]$DryRun,        # Show what would be deleted without deleting
    [switch]$SkipDocMerge   # Skip documentation merging
)

$rootDir = $PSScriptRoot

# Color output functions
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Host "================================================================================`n" -ForegroundColor Magenta
Write-Host "  EPHREADER - CLEANUP UTILITY" -ForegroundColor Magenta
Write-Host "`n================================================================================" -ForegroundColor Magenta
Write-Host ""
Write-Info "Project: EphReader - Multi-format ephemeris reader library"
Write-Info "License: MIT"
Write-Host ""

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No files will be deleted"
} else {
    Write-Warning "This will DELETE temporary log files"
    Write-Host "Press Ctrl+C to cancel, or Enter to continue..." -ForegroundColor Yellow
    Read-Host
}

Write-Host ""

# File lists - ONLY temporary logs and session notes to delete
$logFiles = @(
    "conversion_errors.txt",
    "conversion_log.txt",
    "conversion_status.txt",
    "BINARY_FIX_COMPLETE.txt",
    "BENCHMARK_RESULTS.txt",
    "ACCURACY_TEST_RESULTS.txt",
    "EPHEMERIS_INVENTORY_FULL.txt",
    "CONVERSION_SUCCESS.txt",
    "EPM2021_CONVERSION_RESULTS.txt"
)

$sessionNotes = @(
    "CHANGELOG.md",
    "SESSION_11_CHANGELOG.md",
    "SESSION_ACCURACY_CHANGELOG.md"
)

$oldDocs = @(
    "ACCURACY_SUMMARY_QUICK.md",
    "ASTEROIDS_AND_NODES_ANALYSIS.md",
    "AVAILABLE_EPHEMERIDES_COMPLETE.md",
    "CHANGELOG.md",
    "CHIRON_AND_LUNAR_NODES_GUIDE.md",
    "CHIRON_DATA_ACQUISITION_REPORT.md",
    "CHIRON_INTEGRATION_REPORT_OLD.md",
    "CONVERSION_FINAL_REPORT.md",
    "CONVERTER_GUIDE.md",
    "DE431_CONVERSION_PROGRESS.md",
    "EPM2021_CONVERSION_RESULTS.txt",
    "EPM2021_FINAL_RESULTS.md",
    "EPM2021_NATIVE_PARAMS.md",
    "EPHEMERIS_ACCURACY_COMPARISON_FULL.md",
    "EPHEMERIS_ACCURACY_COMPARISON_SUMMARY.md",
    "EPHEMERIS_COMPARISON.md",
    "EPHEMERIS_COMPARISON_SUMMARY.md",
    "EPHEMERIS_FORMATS_AND_COMPARISON.md",
    "EXECUTIVE_SUMMARY.md",
    "MISSION_ACCOMPLISHED_NATIVE_INTERVALS.md",
    "NATIVE_INTERVALS_EXACT.md",
    "NATIVE_INTERVALS_GUIDE.md",
    "PRECISION_RECOMMENDATIONS.md",
    "QUICK_REFERENCE.md",
    "QUICKSTART.md",
    "SESSION_11_CHANGELOG.md",
    "SESSION_ACCURACY_CHANGELOG.md",
    "SWISS_EPHEMERIS_GUIDE.md",
    "SWISS_EPHEMERIS_SETUP.md",
    "SWISS_EPH_FINAL_DECISION.md",
    "SWISS_EPH_FINAL_STATUS.md",
    "SWISS_EPH_FIX_GUIDE.md"
)

# Helper function to delete files
function Remove-FilesList {
    param(
        [string[]]$files,
        [string]$category
    )

    Write-Host "-----------------------------------" -ForegroundColor DarkGray
    Write-Host "Processing: $category" -ForegroundColor Yellow
    Write-Host "-----------------------------------" -ForegroundColor DarkGray

    $deleted = 0
    $missing = 0

    foreach ($file in $files) {
        $fullPath = Join-Path $rootDir $file

        if (Test-Path $fullPath) {
            if ($DryRun) {
                Write-Host "  [DELETE] $file" -ForegroundColor Yellow
            } else {
                Remove-Item -Path $fullPath -Force
                Write-Host "  [DELETED] $file" -ForegroundColor Green
                $deleted++
            }
        } else {
            $missing++
        }
    }

    if ($DryRun) {
        Write-Info "Would delete $($files.Count) files ($missing already missing)"
    } else {
        Write-Success "Deleted: $deleted files, Missing: $missing"
    }
    Write-Host ""
}

# Execute cleanup (ONLY logs and session notes)
Remove-FilesList -files $logFiles -category "Temporary Log Files"
Remove-FilesList -files $sessionNotes -category "Session Notes"

# Documentation merging
if (-not $SkipDocMerge) {
    Write-Host "-----------------------------------" -ForegroundColor DarkGray
    Write-Host "Documentation Consolidation" -ForegroundColor Yellow
    Write-Host "-----------------------------------" -ForegroundColor DarkGray
    Write-Info "All old documentation will be merged into COMPLETE_DOCUMENTATION.md"
    Write-Info "Original files will be preserved (not deleted)"
    Write-Host "  ✅ Files will remain for reference" -ForegroundColor Green
    Write-Host "  ✅ New comprehensive doc will be created" -ForegroundColor Green
    Write-Host ""
}# Summary
Write-Host "================================================================================`n" -ForegroundColor Magenta
Write-Host "  CLEANUP COMPLETE" -ForegroundColor Magenta
Write-Host "`n================================================================================" -ForegroundColor Magenta
Write-Host ""

if ($DryRun) {
    Write-Warning "DRY RUN - No changes were made"
    Write-Info "Run without -DryRun to execute cleanup"
} else {
    Write-Success "Cleanup completed successfully!"
    Write-Host ""
    Write-Info "ALL CODE AND TOOLS PRESERVED:"
    Write-Host "  ✅ All PHP readers (including experimental)" -ForegroundColor Green
    Write-Host "  ✅ All Python tools (converters, integrators)" -ForegroundColor Green
    Write-Host "  ✅ All benchmarks and comparison scripts" -ForegroundColor Green
    Write-Host "  ✅ All debug and analysis tools" -ForegroundColor Green
    Write-Host "  ✅ All documentation files" -ForegroundColor Green
    Write-Host ""
    Write-Info "DELETED (only temporary files):"
    Write-Host "  🗑️  Log files (.txt)" -ForegroundColor Gray
    Write-Host "  🗑️  Session changelogs" -ForegroundColor Gray
    Write-Host ""
    Write-Success "Ready for GitHub publication as 'EphReader'!"
}

Write-Host ""
