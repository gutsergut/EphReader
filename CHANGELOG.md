# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added (2024-01-XX)

- **Optimized .eph binary format** for PHP 8.4+ (5.4× smaller than SPICE BSP)
  - Custom header (512 bytes) with magic, version, metadata
  - Body table (32 bytes per body) with NAIF IDs, names, offsets
  - Interval index (16 bytes per interval) for O(log n) binary search
  - Packed double arrays (Chebyshev coefficients) for direct fseek/unpack

- **PHP EphReader class** (`php/src/EphReader.php`)
  - Pure PHP 8.4 implementation, no extensions required
  - Chebyshev polynomial evaluation using Clenshaw's algorithm
  - Position + velocity computation via derivative
  - Binary search for interval lookup
  - Performance: ~0.5-2 ms per computation

- **Python converter** (`tools/spice2eph.py`)
  - Converts SPICE BSP → optimized .eph format
  - Uses CALCEPH to read SPICE, scipy DCT for Chebyshev fitting
  - Configurable body list and interval size
  - Compression: EPM2021 147 MB → 27 MB

- **Russian EPM2021 support**
  - Documentation for EPM2021 SPICE download (IAA RAS FTP)
  - Format comparison: SPICE vs IAA BIN vs optimized .eph
  - Integration with PHP reader

- **Project infrastructure**
  - `composer.json` for PHP PSR-4 autoloading
  - `requirements.txt` for Python dependencies (calceph, numpy, scipy)
  - `php/examples/example_usage.php` demo script
  - Comprehensive README with format specs, benchmarks, usage examples

- **Documentation updates**
  - `.github/copilot-instructions.md`: Added PHP/Python tooling, EPM info, .eph format details
  - `README.md`: Restructured with separate sections for JPL DE, EPM, optimized format
  - Format specification diagram (header + body table + index + coefficients)

### Changed

- **README.md**: Reorganized into JPL DE section, EPM section, format section
- **`.github/copilot-instructions.md`**: Expanded from JPL-only to multi-format (JPL + EPM + .eph)

## [0.1.0] - Initial Setup

### Added

- **JPL DE ephemerides**
  - DE440 (1550-2650 AD, ~97.5 MB)
  - DE441 (long-span -13200 to +17191, ~2.6 GB)
  - DE431 (legacy long-span, ~2.6 GB)

- **Project Pluto jpl_eph library**
  - Full source tree in `vendor/jpl_eph/jpl_eph-master/`
  - Build instructions for MSVC and MinGW
  - dump_eph utility for testing

- **Git infrastructure**
  - `.gitignore`: Exclude large binaries (data/ephemerides/**)
  - `.gitattributes`: Enforce LF line endings for all text files
  - Initial commits: project setup, data structure, vendor code

- **Documentation**
  - `README.md`: Basic structure, download links, build commands
  - `.github/copilot-instructions.md`: AI agent guidelines for JPL DE workflow

---

**Format**: [Semantic Versioning](https://semver.org/)
**License**: See LICENSE file (if applicable)
