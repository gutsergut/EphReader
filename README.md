# Swisseph Ephemerides Workspace

This workspace stores planetary ephemerides (JPL DE, Russian EPM) and tools to work with them in PHP and C/C++.

## Features

- **JPL DE Series**: DE440, DE441, DE431 ephemerides from NASA JPL
- **Russian EPM Series**: EPM2021 from IAA RAS (Institute of Applied Astronomy)
- **Optimized .eph Format**: Custom binary format for PHP with ~5× compression vs SPICE
- **PHP Reader**: Pure PHP 8.4 implementation with Chebyshev polynomial evaluation
- **C/C++ Support**: Project Pluto jpl_eph library for JPL DE files

## Structure
- `data/ephemerides/jpl/de440/`
  - `linux_p1550p2650.440` (~97.5 MB)
  - `header.440`
  - `testpo.440`
- `data/ephemerides/jpl/de441/`
  - `linux_m13000p17000.441` (~2.60 GB)
  - `header.441`
  - `testpo.441`
- `data/ephemerides/jpl/de431/`
  - `lnxm13000p17000.431` (~2.60 GB)
  - `header.431_572`
  - `testpo.431`
- `data/ephemerides/epm/2021/`
  - `spice/epm2021.bsp` (~147 MB) - SPICE format
  - `spice/moonlibr_epm2021.bpc` (~11.4 MB) - lunar libration
  - `epm2021.eph` - optimized format (~27 MB)
- `php/`
  - `src/EphReader.php` - PHP reader for .eph files
  - `examples/example_usage.php` - usage demo
- `tools/`
  - `spice2eph.py` - SPICE to .eph converter
- `vendor/jpl_eph/`
  - `jpl_eph-master/` (source tree)
  - `jpl_eph.zip` (downloaded archive)
- `.github/`
  - `copilot-instructions.md` (agent rules)

Large binaries are ignored via `.gitignore` (kept under `data/ephemerides/`).

## Get data (JPL DE Series)

### DE440 (1550-2650 AD, ~97.5 MB)
Files come from JPL Linux (little-endian):
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/linux_p1550p2650.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/header.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/testpo.440

### DE441 (Long-span: -13200 to +17191, ~2.6 GB)
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/linux_m13000p17000.441
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/header.441
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/testpo.441

### DE431 (Legacy long-span, ~2.6 GB)
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/lnxm13000p17000.431
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/header.431_572
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/testpo.431

## Get data (Russian EPM Series)

### EPM2021 (1787-2214 AD, IAA RAS)

**SPICE Format** (~159 MB total):
```powershell
# Main ephemeris with TT-TDB
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/epm2021.bsp `
  -o data\ephemerides\epm\2021\spice\epm2021.bsp

# Lunar libration angles
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/moonlibr_epm2021.bpc `
  -o data\ephemerides\epm\2021\spice\moonlibr_epm2021.bpc

# Constants (masses, radii)
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/epm2021.tpc `
  -o data\ephemerides\epm\2021\spice\epm2021.tpc

# Lunar frame definition
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/moonlibr_epm2021.tf `
  -o data\ephemerides\epm\2021\spice\moonlibr_epm2021.tf
```

**Binary Format** (IAA proprietary, ~92 MB):
- http://ftp.iaaras.ru/pub/epm/EPM2021/BIN/ (22 separate .bin files)
- Requires IAA's `libephaccess` library

**Resources**:
- Main page: https://iaaras.ru/en/dept/ephemeris/epm/2021/
- SPICE toolkit: https://naif.jpl.nasa.gov/naif/toolkit.html
- CALCEPH (multi-format reader): https://www.imcce.fr/recherche/equipes/asd/calceph/

## Optimized .eph Format for PHP

### Why custom format?

SPICE BSP files have significant overhead:
- **DAF structure**: File record, summary records, linked lists (~15-20% overhead)
- **Example**: EPM2021 SPICE 147 MB → optimized .eph ~27 MB (**5.4× smaller**)
- **Benefits**: Faster loading, simpler code, no external dependencies

### Format Specification

```
┌─────────────────────────────────────────────┐
│ HEADER (512 bytes)                          │
│  - Magic: "EPH\0" (4 bytes)                 │
│  - Version: uint32                          │
│  - NumBodies, NumIntervals: uint32          │
│  - IntervalDays, StartJD, EndJD: double     │
│  - CoeffDegree: uint32                      │
├─────────────────────────────────────────────┤
│ BODY TABLE (N × 32 bytes)                   │
│  - BodyID: int32                            │
│  - Name: char[24]                           │
│  - DataOffset: uint64                       │
├─────────────────────────────────────────────┤
│ INTERVAL INDEX (M × 16 bytes)               │
│  - JD_start, JD_end: double                 │
├─────────────────────────────────────────────┤
│ COEFFICIENTS (packed doubles)               │
│  - Chebyshev coefficients [X, Y, Z]         │
│  - Arranged: body0_interval0, body0_int1... │
└─────────────────────────────────────────────┘
```

### Convert SPICE to .eph

```powershell
# Install dependencies (once)
pip install calceph numpy scipy

# Convert EPM2021 SPICE to .eph
python tools\spice2eph.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0
```

### PHP Usage

```php
<?php
require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

// Compute Earth position at J2000.0
$result = $eph->compute(399, 2451545.0); // 399 = Earth NAIF ID

echo "Position (AU): ";
echo sprintf("X=%.8f, Y=%.8f, Z=%.8f\n", ...$result['pos']);

echo "Velocity (AU/day): ";
echo sprintf("VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result['vel']);
```

## Performance Benchmarks

Comprehensive benchmark comparing three formats (1000 random access operations on Earth ephemeris):

| Format      | Speed (ops/sec) | File Size | Accuracy | Access Method |
|-------------|-----------------|-----------|----------|---------------|
| **Binary .eph** | **8,565** | **10.79 MB** | ✅ Correct | fseek/unpack |
| SQLite .db  | 162 | 16.89 MB | ✅ Correct | PDO SQL |
| SPICE BSP   | 4,768 | 147.13 MB | ✅ Reference | Python spiceypy |

**Key Findings**:
- **Binary .eph is 53× faster than SQLite** for random access
- **Binary .eph is 36% smaller** than SQLite (13.6× compression from original SPICE)
- **All formats produce identical coordinates** (verified at J2000.0 and 1000 random points)
- SPICE fastest for sequential access (11,631 ops/sec) due to internal caching
- SQLite best for initialization (4.6 ms vs Binary 41.3 ms)

**Recommendation**:
- **Production**: Use **Binary .eph** (fastest, smallest, correct)
- **Development/Debugging**: Use **SQLite .db** (SQL queries, sqlite3 CLI)

**Performance characteristics** (single computation):
- Binary .eph: ~0.12 ms (8,565 ops/sec)
- SQLite .db: ~6.1 ms (162 ops/sec)
- SPICE BSP: ~0.21 ms (4,768 ops/sec, Python-only)

See `BINARY_FIX_COMPLETE.txt` and `BENCHMARK_RESULTS.txt` for detailed analysis.

## Build utilities (Windows/pwsh)
- MSVC (Developer PowerShell):
  - `cl /EHsc /O2 jpleph.cpp dump_eph.cpp`
- MinGW/Clang:
  - `g++ -O2 jpleph.cpp dump_eph.cpp -o dump_eph.exe`

Run `dump_eph.exe <path-to-.440|.441|.431> 2451545.0 0` to test; or use `testeph` with matching `testpo.44x/431`.

Examples:
```powershell
# DE440 (J2000.0):
.\dump_eph.exe "C:\Users\serge\OneDrive\Documents\Fractal\Projects\Component\Swisseph\eph\data\ephemerides\jpl\de440\linux_p1550p2650.440" 2451545.0 0

# DE441 (ultra-long):
.\dump_eph.exe "C:\Users\serge\OneDrive\Documents\Fractal\Projects\Component\Swisseph\eph\data\ephemerides\jpl\de441\linux_m13000p17000.441" 2451545.0 0

# DE431 (ultra-long legacy):
.\dump_eph.exe "C:\Users\serge\OneDrive\Documents\Fractal\Projects\Component\Swisseph\eph\data\ephemerides\jpl\de431\lnxm13000p17000.431" 2451545.0 0
```

## Notes
- Endianness auto-detected by the code; Linux folder is little-endian, SunOS big-endian.
- Prefer DE440 (1550–2650). Use DE441 (~2.6 GB) if you need -13200…17191. DE431 offers similar span (older solution).
- To build custom range, download ASCII and run `asc2eph` from jpl_eph.
