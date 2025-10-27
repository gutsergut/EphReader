# Swisseph Ephemerides Workspace

This workspace stores JPL DE ephemerides data and vendor code (Project Pluto jpl_eph) to read/compute positions.

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
- `vendor/jpl_eph/`
  - `jpl_eph-master/` (source tree)
  - `jpl_eph.zip` (downloaded archive)
- `.github/`
  - `copilot-instructions.md` (agent rules)

Large binaries are ignored via `.gitignore` (kept under `data/ephemerides/`).

## Get data (DE440/441/431)
Files come from JPL Linux (little-endian):
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/linux_p1550p2650.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/header.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/testpo.440

Long-span ephemerides (~2.6 GB each):
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/linux_m13000p17000.441
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/header.441
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de441/testpo.441

Legacy long-span (older than DE44x):
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/lnxm13000p17000.431
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/header.431_572
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/testpo.431

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
