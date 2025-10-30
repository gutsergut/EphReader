# Convert DE431 SPICE to .eph format
# DE431 состоит из двух частей: part-1 (BC 13200 to ~AD 8000) и part-2 (~AD 8000 to AD 17191)
# Usage: .\convert_de431.ps1

Write-Host ("=" * 80)
Write-Host "DE431 SPICE to .eph Conversion (Both Parts)"
Write-Host ("=" * 80)
Write-Host ""

$inputFile1 = "data\ephemerides\jpl\de431\de431_part-1.bsp"
$inputFile2 = "data\ephemerides\jpl\de431\de431_part-2.bsp"
$outputFile1 = "data\ephemerides\jpl\de431_part-1.eph"
$outputFile2 = "data\ephemerides\jpl\de431_part-2.eph"

# Check if both input files exist
$part1Exists = Test-Path $inputFile1
$part2Exists = Test-Path $inputFile2

if (-not $part1Exists) {
    Write-Host "❌ Part 1 not found: $inputFile1" -ForegroundColor Red
    Write-Host "   Download: curl -L -o $inputFile1 https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de431_part-1.bsp" -ForegroundColor Yellow
}

if (-not $part2Exists) {
    Write-Host "❌ Part 2 not found: $inputFile2" -ForegroundColor Red
    Write-Host "   Download: curl -L -o $inputFile2 https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de431_part-2.bsp" -ForegroundColor Yellow
}

if (-not ($part1Exists -and $part2Exists)) {
    Write-Host ""
    Write-Host "Please download missing files first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Part 1 found: $inputFile1" -ForegroundColor Green
$fileSize1 = (Get-Item $inputFile1).Length / 1MB
Write-Host "   Size: $([math]::Round($fileSize1, 2)) MB" -ForegroundColor Cyan

Write-Host "✅ Part 2 found: $inputFile2" -ForegroundColor Green
$fileSize2 = (Get-Item $inputFile2).Length / 1MB
Write-Host "   Size: $([math]::Round($fileSize2, 2)) MB" -ForegroundColor Cyan
Write-Host ""

$totalSize = $fileSize1 + $fileSize2
Write-Host "Total input size: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Check if Python and required packages are available
Write-Host "Checking Python environment..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ("=" * 80)
Write-Host "Converting Part 1 (BC 13200 to ~AD 8000)"
Write-Host ("=" * 80)
Write-Host ""
Write-Host "Bodies: Mercury, Venus, EMB, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Sun, Moon"
Write-Host "Interval: 16 days (optimized for balance between size and accuracy)"
Write-Host ""

python tools\jpl2eph.py $inputFile1 $outputFile1 --format binary

if (-not (Test-Path $outputFile1)) {
    Write-Host ""
    Write-Host "❌ Part 1 conversion FAILED!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Part 1 converted successfully!" -ForegroundColor Green
$outputSize1 = (Get-Item $outputFile1).Length / 1MB
Write-Host "   Output: $([math]::Round($outputSize1, 2)) MB" -ForegroundColor Cyan
Write-Host ""

Write-Host ("=" * 80)
Write-Host "Converting Part 2 (~AD 8000 to AD 17191)"
Write-Host ("=" * 80)
Write-Host ""

python tools\jpl2eph.py $inputFile2 $outputFile2 --format binary

if (-not (Test-Path $outputFile2)) {
    Write-Host ""
    Write-Host "❌ Part 2 conversion FAILED!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Part 2 converted successfully!" -ForegroundColor Green
$outputSize2 = (Get-Item $outputFile2).Length / 1MB
Write-Host "   Output: $([math]::Round($outputSize2, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Summary
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host "✅ CONVERSION COMPLETE!" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host ""

$totalOutputSize = $outputSize1 + $outputSize2
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Part 1: $([math]::Round($fileSize1, 2)) MB → $([math]::Round($outputSize1, 2)) MB" -ForegroundColor White
Write-Host "  Part 2: $([math]::Round($fileSize2, 2)) MB → $([math]::Round($outputSize2, 2)) MB" -ForegroundColor White
Write-Host "  Total:  $([math]::Round($totalSize, 2)) MB → $([math]::Round($totalOutputSize, 2)) MB" -ForegroundColor White

$compression = (1 - ($totalOutputSize / $totalSize)) * 100
if ($compression -gt 0) {
    Write-Host "  Compression: $([math]::Round($compression, 1))% smaller" -ForegroundColor Green
} else {
    Write-Host "  Size change: $([math]::Round(-$compression, 1))% larger" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Output files:" -ForegroundColor Cyan
Write-Host "  $outputFile1" -ForegroundColor White
Write-Host "  $outputFile2" -ForegroundColor White
Write-Host ""
Write-Host "Note: Use Part 1 for testing (covers 1550-2650 AD, same as DE440)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next step: Run comparison test" -ForegroundColor Yellow
Write-Host "  php test_de431_comparison.php" -ForegroundColor Yellow
