# JPL DE440 Conversion Pipeline
# Converts DE440 SPICE BSP to all formats with interval=16 days

$ErrorActionPreference = "Stop"

$input_bsp = "data\ephemerides\jpl\de440.bsp"
$output_dir = "data\ephemerides\jpl\"

# Bodies: 1=Mercury, 2=Venus, 3=Earth-Moon Barycenter, 4=Mars, 5=Jupiter,
#         6=Saturn, 7=Uranus, 8=Neptune, 9=Pluto, 10=Sun, 301=Moon, 399=Earth
$bodies = "1,2,3,4,5,6,7,8,9,10,301,399"
$interval = "16.0"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "JPL DE440 Conversion Pipeline" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check input file
if (-not (Test-Path $input_bsp)) {
    Write-Host "❌ Input file not found: $input_bsp" -ForegroundColor Red
    Write-Host "Please download first:" -ForegroundColor Yellow
    Write-Host "  curl -L https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp -o $input_bsp`n" -ForegroundColor Yellow
    exit 1
}

$size_mb = [math]::Round((Get-Item $input_bsp).Length / 1MB, 2)
Write-Host "✅ Input: $input_bsp ($size_mb MB)" -ForegroundColor Green

# 1. Binary .eph
Write-Host "`n[1/4] Converting to Binary .eph..." -ForegroundColor Yellow
python tools\spice2eph.py `
    $input_bsp `
    "${output_dir}de440.eph" `
    --bodies $bodies `
    --interval $interval

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Binary conversion failed" -ForegroundColor Red
    exit 1
}

# 2. SQLite .db
Write-Host "`n[2/4] Converting to SQLite .db..." -ForegroundColor Yellow
python tools\spice2sqlite.py `
    $input_bsp `
    "${output_dir}de440.db" `
    --bodies $bodies `
    --interval $interval

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ SQLite conversion failed" -ForegroundColor Red
    exit 1
}

# 3. Hybrid .hidx + .heph
Write-Host "`n[3/4] Converting to Hybrid format..." -ForegroundColor Yellow
python tools\spice2hybrid.py `
    $input_bsp `
    $output_dir `
    --bodies $bodies `
    --interval $interval

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Hybrid conversion failed" -ForegroundColor Red
    exit 1
}

# 4. MessagePack .msgpack
Write-Host "`n[4/4] Converting to MessagePack..." -ForegroundColor Yellow
python tools\spice2msgpack.py `
    $input_bsp `
    "${output_dir}de440.msgpack" `
    --bodies $bodies `
    --interval $interval

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ MessagePack conversion failed" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Conversion Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Output files:" -ForegroundColor Yellow
Get-ChildItem "${output_dir}de440.*" | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "  $($_.Name) - $size MB" -ForegroundColor White
}

Write-Host "`nTest with:" -ForegroundColor Yellow
Write-Host "  php test_all_formats.php`n" -ForegroundColor White
