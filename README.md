# Swisseph Ephemerides Workspace

This workspace stores JPL DE ephemerides data and vendor code (Project Pluto jpl_eph) to read/compute positions.

## Structure
- `data/ephemerides/jpl/de440/`
  - `linux_p1550p2650.440` (~97.5 MB)
  - `header.440`
  - `testpo.440`
- `vendor/jpl_eph/`
  - `jpl_eph-master/` (source tree)
  - `jpl_eph.zip` (downloaded archive)
- `.github/`
  - `copilot-instructions.md` (agent rules)

Large binaries are ignored via `.gitignore` (kept under `data/ephemerides/`).

## Get data (DE440)
Files come from JPL Linux (little-endian):
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/linux_p1550p2650.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/header.440
- https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/testpo.440

## Build utilities (Windows/pwsh)
- MSVC (Developer PowerShell):
  - `cl /EHsc /O2 jpleph.cpp dump_eph.cpp`
- MinGW/Clang:
  - `g++ -O2 jpleph.cpp dump_eph.cpp -o dump_eph.exe`

Run `dump_eph.exe <path-to-.440> 2451545.0 0` to test; or use `testeph` with `testpo.440`.

## Notes
- Endianness auto-detected by the code; Linux folder is little-endian, SunOS big-endian.
- Prefer DE440 (1550–2650). Use DE441 (~2.6 GB) only if you need -13200…17191.
- To build custom range, download ASCII and run `asc2eph` from jpl_eph.
