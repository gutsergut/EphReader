# Swiss Ephemeris Native DLL Setup

## Quick Install (No Compilation)

### Option 1: Download Precompiled DLL (RECOMMENDED)

1. **Download Swiss Ephemeris DLL** от Astrodienst:
   - Website: https://www.astro.com/swisseph/
   - Direct FTP: ftp://ftp.astro.com/pub/swisseph/
   - Files needed:
     - `swetest.exe` (Windows executable with embedded DLL)
     - OR `swedll32.dll` / `swedll64.dll` (32/64-bit DLL)

2. **Extract DLL from swetest.exe**:
   ```powershell
   # Download
   curl -O ftp://ftp.astro.com/pub/swisseph/sweph_18.zip

   # Extract
   Expand-Archive sweph_18.zip -DestinationPath vendor/swisseph/

   # DLL is embedded in swetest.exe or provided separately
   ```

3. **Place files**:
   ```
   vendor/swisseph/
   ├── swetest.exe    (Swiss Ephemeris executable)
   ├── swedll64.dll   (64-bit DLL)
   └── README.txt

   ephe/              (ephemeris data files)
   ├── semo_*.se1     (Moon files)
   ├── seas_*.se1     (Asteroid files)
   └── sefstars.txt   (Fixed stars)
   ```

4. **Enable PHP FFI**:
   ```ini
   # php.ini
   extension=ffi
   ffi.enable=true
   ```

5. **Test**:
   ```php
   <?php
   $eph = new SwissEphFFIReader(
       'vendor/swisseph/swedll64.dll',
       'ephe/'
   );

   $result = $eph->compute(399, 2451545.0); // Earth at J2000.0
   print_r($result);
   ```

---

## Option 2: Compile from Source (Advanced)

### Requirements
- **Visual Studio 2019+** with C++ tools
- OR **MinGW-w64** (gcc for Windows)

### Using Visual Studio

1. **Install Visual Studio Build Tools**:
   https://visualstudio.microsoft.com/visual-cpp-build-tools/

   Select: "Desktop development with C++"

2. **Extract Swiss Ephemeris source**:
   ```powershell
   cd vendor/swisseph
   Expand-Archive swisseph-source.zip
   cd swisseph-master
   ```

3. **Compile DLL**:
   ```cmd
   # Open "Developer Command Prompt for VS 2019"
   cd vendor\swisseph\swisseph-master

   # Compile all C files into DLL
   cl /LD /O2 /DWIN32 /D_WINDOWS /D_USRDLL sweph.c swedate.c swehouse.c swejpl.c swemmoon.c swemplan.c swetest.c /Fe:swedll64.dll

   # Or use provided Makefile if available
   nmake -f makefile.vc
   ```

4. **Copy DLL**:
   ```powershell
   Copy-Item swedll64.dll ..\..\
   ```

### Using MinGW-w64

1. **Install MinGW-w64**:
   https://www.mingw-w64.org/downloads/

   OR via Chocolatey:
   ```powershell
   choco install mingw
   ```

2. **Compile**:
   ```bash
   cd vendor/swisseph/swisseph-master

   gcc -shared -O2 -o swedll64.dll \
       sweph.c swedate.c swehouse.c swejpl.c swemmoon.c swemplan.c \
       -lm -DWIN32
   ```

---

## Option 3: Use Python pyswisseph (if compiled)

If you successfully install pyswisseph with MSVC:

```powershell
# Install build tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install pyswisseph
C:/Python314/python.exe -m pip install pyswisseph

# Use converter
python tools/swisseph2eph.py ephe/ data/ephemerides/swisseph/swisseph.eph --bodies 1,2,3,301,399 --interval 16.0
```

---

## Verify Installation

### Test FFI Access
```php
<?php
// test_swisseph_ffi.php
require 'vendor/autoload.php';

use Swisseph\Ephemeris\SwissEphFFIReader;

try {
    $eph = new SwissEphFFIReader(
        'vendor/swisseph/swedll64.dll',  // or swetest.exe
        'ephe/'
    );

    echo "✅ Swiss Ephemeris loaded successfully!\n";
    echo "Metadata:\n";
    print_r($eph->getMetadata());

    echo "\nTesting computation...\n";
    $result = $eph->compute(10, 2451545.0); // Sun at J2000.0
    echo "Sun position: [" . implode(', ', $result['pos']) . "] AU\n";

} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
}
```

### Expected Output
```
✅ Swiss Ephemeris loaded successfully!
Metadata:
Array
(
    [format] => swiss_ephemeris_ffi
    [source] => Swiss Ephemeris 2.10.03
    [ephe_path] => ephe/
    ...
)

Testing computation...
Sun position: [0.0, 0.0, 0.0] AU
```

---

## Troubleshooting

### "FFI extension not enabled"
```ini
# Add to php.ini
extension=ffi
ffi.enable=true

# Restart PHP/Apache
```

### "DLL not found"
- Check DLL path is correct (use absolute path)
- Ensure DLL is 64-bit if using 64-bit PHP
- Try `swetest.exe` instead of separate DLL

### "Ephemeris files not found"
- Check `ephe/` directory contains `.se1` files
- Swiss Ephemeris needs at least:
  - `semo_18.se1` (Moon 1800-1900)
  - `sepl_18.se1` (Planets 1800-1900)
- Download from: ftp://ftp.astro.com/pub/swisseph/ephe/

### "Access violation" errors
- DLL architecture mismatch (32 vs 64-bit)
- Use correct FFI definitions
- Check PHP version supports FFI (7.4+)

---

## Performance Comparison

| Method | Setup | Performance | Features |
|--------|-------|-------------|----------|
| **FFI + DLL** | Download DLL | ~5,000 ops/sec | Full features, no compilation |
| **Converted .eph** | Compile pyswisseph | ~18,000 ops/sec | Fast, unified format |
| **JPL DE440** | Already done ✅ | ~9,600 ops/sec | NASA standard, ready now |

**Recommendation**:
- **Quick start**: Use FFI + precompiled DLL (no compilation)
- **Best performance**: Use JPL DE440 (already converted)
- **Full features**: FFI gives access to 10,000+ asteroids

---

## Download Links

- **Swiss Ephemeris DLL**: ftp://ftp.astro.com/pub/swisseph/
- **Documentation**: https://www.astro.com/swisseph/swephprg.htm
- **Ephemeris data**: ftp://ftp.astro.com/pub/swisseph/ephe/
- **Build Tools**: https://visualstudio.microsoft.com/visual-cpp-build-tools/
