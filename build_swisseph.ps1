# Build Swiss Ephemeris DLL using MinGW-w64
# Usage: .\build_swisseph.ps1

param(
    [switch]$Clean,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Paths
$mingwPath = "$PSScriptRoot\vendor\mingw\mingw64\bin"
$srcDir = "$PSScriptRoot\vendor\swisseph\pyswisseph-2.10.3.2\libswe"
$buildDir = "$PSScriptRoot\build\swisseph"
$dllPath = "$PSScriptRoot\vendor\swisseph\swedll64.dll"

# Clean build
if ($Clean) {
    Write-Host "🧹 Cleaning build artifacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
    Remove-Item -Force $dllPath -ErrorAction SilentlyContinue
    Write-Host "✅ Clean complete" -ForegroundColor Green
    exit 0
}

# Verify MinGW
if (-not (Test-Path "$mingwPath\gcc.exe")) {
    Write-Host "❌ MinGW not found at: $mingwPath" -ForegroundColor Red
    Write-Host "Please extract MinGW-w64 to vendor\mingw\" -ForegroundColor Yellow
    exit 1
}

# Add MinGW to PATH
$env:PATH = "$mingwPath;$env:PATH"

# Verify GCC
$gccVersion = & gcc --version 2>&1 | Select-Object -First 1
Write-Host "✅ GCC found: $gccVersion" -ForegroundColor Green

# Create build directory
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

# Compile flags
$cflags = @(
    "-O3",               # Optimization level 3
    "-Wall",             # All warnings
    "-DWIN32",           # Windows platform
    "-D_WINDOWS",        # Windows API
    "-D_USRDLL",         # DLL build
    "-fPIC"              # Position independent code
)

$ldflags = @(
    "-shared",           # Shared library (DLL)
    "-Wl,--out-implib,vendor\swisseph\libswe.a"  # Import library
)

# Get all C source files
$sourceFiles = Get-ChildItem -Path $srcDir -Filter "*.c"
$objectFiles = @()

Write-Host "`n🔨 Compiling Swiss Ephemeris C files..." -ForegroundColor Cyan
Write-Host "Source directory: $srcDir" -ForegroundColor Gray

foreach ($file in $sourceFiles) {
    $objFile = Join-Path $buildDir "$($file.BaseName).o"
    $objectFiles += $objFile

    Write-Host "  📄 $($file.Name)" -ForegroundColor Gray

    $compileCmd = @("gcc") + $cflags + @("-c", $file.FullName, "-o", $objFile)

    if ($Verbose) {
        Write-Host "    Command: $($compileCmd -join ' ')" -ForegroundColor DarkGray
    }

    & $compileCmd[0] $compileCmd[1..($compileCmd.Length-1)]

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Compilation failed: $($file.Name)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n🔗 Linking DLL..." -ForegroundColor Cyan

$linkCmd = @("gcc") + $ldflags + @("-o", $dllPath) + $objectFiles + @("-lm")

if ($Verbose) {
    Write-Host "Command: $($linkCmd -join ' ')" -ForegroundColor DarkGray
}

& $linkCmd[0] $linkCmd[1..($linkCmd.Length-1)]

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Linking failed" -ForegroundColor Red
    exit 1
}

# Verify DLL
if (Test-Path $dllPath) {
    $dllInfo = Get-Item $dllPath
    Write-Host "`n✅ Swiss Ephemeris DLL compiled successfully!" -ForegroundColor Green
    Write-Host "   📦 Location: $dllPath" -ForegroundColor White
    Write-Host "   📏 Size: $([math]::Round($dllInfo.Length / 1MB, 2)) MB" -ForegroundColor White
    Write-Host "   🕒 Created: $($dllInfo.LastWriteTime)" -ForegroundColor White
} else {
    Write-Host "❌ DLL not found after compilation" -ForegroundColor Red
    exit 1
}

Write-Host "`n🎯 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test FFI: php test_swisseph_ffi.php" -ForegroundColor Gray
Write-Host "  2. Convert: python tools\swisseph2eph.py ephe\ output.eph" -ForegroundColor Gray
