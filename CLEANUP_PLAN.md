# EphReader - Cleanup Plan (REVISED)

**Project Name**: `EphReader` (Multi-format ephemeris reader library)
**License**: MIT (with data source attributions)

## 📁 KEEP (Production Files)

### Core Library
- ✅ `php/src/EphReader.php` - Main .eph reader
- ✅ `php/src/ChironEphReader.php` - Chiron specialized reader
- ✅ `php/src/EphemerisInterface.php` - Interface definition
- ✅ `php/src/SqliteEphReader.php` - SQLite format reader (**KEEP experimental**)
- ✅ `php/src/MessagePackEphReader.php` - MessagePack reader (**KEEP experimental**)
- ✅ `php/src/HybridEphReader.php` - Hybrid reader (**KEEP experimental**)
- ✅ `php/src/SwissEphFFIReader.php` - Swiss Eph FFI reader (**KEEP experimental**)
- ✅ `tools/eph_reader.py` - Python .eph reader
- ✅ `tools/spice2eph.py` - SPICE → .eph converter
- ✅ `tools/spice2sqlite.py` - SPICE → SQLite converter (**KEEP**)
- ✅ `tools/spice2msgpack.py` - SPICE → MessagePack converter (**KEEP**)
- ✅ `tools/swisseph2eph.py` - Swiss → .eph converter (**KEEP**)
- ✅ `tools/swisseph_ffi2eph.py` - Swiss FFI converter (**KEEP**)
- ✅ `tools/swisseph_direct.py` - Direct Swiss access (**KEEP**)
- ✅ `tools/swisseph_standalone.php` - PHP Swiss standalone (**KEEP**)
- ✅ `tools/swisseph_universal.php` - Universal Swiss adapter (**KEEP**)
- ✅ `tools/calceph_ctypes.py` - calceph ctypes wrapper (**KEEP**)
- ✅ `tools/integrate_chiron_hybrid.py` - RK4 orbit integrator
- ✅ `tools/fetch_chiron_horizons.py` - JPL Horizons downloader
- ✅ `tools/get_de440_position.py` - DE440 position tester (**KEEP**)
- ✅ `tools/spice_inspect.py` - SPICE inspector (**KEEP**)
- ✅ `composer.json` - PHP dependencies
- ✅ `requirements.txt` - Python dependencies

### Conversion & Benchmark Tools (**ALL KEEP**)
- ✅ `benchmark_comparison.php` - Format comparison benchmark
- ✅ `benchmark_intervals.py` - Interval optimization test
- ✅ `benchmark_spice.py` - SPICE performance test
- ✅ `convert_de431.ps1` - DE431 conversion script
- ✅ `convert_de440.ps1` - DE440 conversion script
- ✅ `monitor_conversion.ps1` - Conversion progress monitor
- ✅ `run_comprehensive_comparison.ps1` - Full comparison suite
- ✅ `compare_all_triple.ps1` - Triple comparison script
- ✅ `compare_binary_hybrid.php` - Binary vs hybrid comparison
- ✅ `compare_intervals.php` - Interval comparison

### Analysis & Debug Tools (**ALL KEEP**)
- ✅ `debug_binary_issue.php` - Binary format debugger
- ✅ `debug_coeffs.php` - Coefficient validator
- ✅ `debug_comparison.php` - Comparison debugger
- ✅ `debug_hybrid.php` - Hybrid reader debugger
- ✅ `debug_structure.php` - Structure analyzer
- ✅ `debug_sweph_raw.php` - Swiss Eph raw access
- ✅ `debug_swiss_coords.php` - Coordinate system checker
- ✅ `check_binary_meta.php` - Binary metadata checker
- ✅ `check_existing_de.php` - DE file checker
- ✅ `quick_test.php` - Quick validation test
- ✅ `quick_compare_chiron.php` - Chiron quick comparison
- ✅ `analyze_spice_resolution.py` - SPICE resolution analyzer
- ✅ `analyze_swisseph_formats.php` - Swiss format analyzer
- ✅ `example_universal_adapter.php` - Universal adapter example

### Inventory Tools (**ALL KEEP**)
- ✅ `inventory_ephemerides.py` - Basic inventory
- ✅ `inventory_spice.py` - SPICE inventory
- ✅ `inventory_swisseph.php` - Swiss inventory
- ✅ `inventory_all_ephemerides.py` - Complete inventory

### Examples
- ✅ `php/examples/example_usage.php` - Basic usage demo
- ✅ `php/examples/compare_chiron_4way.php` - 4-way Chiron comparison
- ✅ `php/examples/compare_chiron_accuracy.php` - Accuracy validation
- ✅ `php/examples/compare_de440_eph.php` - Integration method comparison
- ✅ `php/examples/compare_all_ephemerides.php` - Full comparison

### Tests
- ✅ `test_accuracy_comparison.php` - EPM/Swiss vs DE440 accuracy
- ✅ `test_all_bodies.php` - Swiss Eph body inventory
- ✅ `test_all_coordinate_systems.php` - Coordinate system tests

### Build Tools
- ✅ `build_swisseph.ps1` - Swiss Eph DLL build script
- ✅ `Makefile` - Build automation
- ✅ `cleanup.ps1` - Cleanup utility (NEW!)

---

## 📚 DOCUMENTATION: Consolidate into COMPLETE_DOCUMENTATION.md

**Action**: Merge all individual docs into one comprehensive guide

### Source Files (to merge):
- `README.md` - Overview
- `USER_GUIDE.md` - User manual (NEW, already comprehensive!)
- `FINAL_ACCURACY_REPORT.md` - Accuracy results ✅
- `CHIRON_INTEGRATION_FINAL_REPORT.md` - Chiron study ✅
- `HYBRID_INTEGRATOR_GUIDE.md` - Integrator manual ✅
- Old documentation (archive after merge):
  - `ACCURACY_SUMMARY_QUICK.md`
  - `ASTEROIDS_AND_NODES_ANALYSIS.md`
  - `AVAILABLE_EPHEMERIDES_COMPLETE.md`
  - `CHIRON_AND_LUNAR_NODES_GUIDE.md`
  - `CHIRON_DATA_ACQUISITION_REPORT.md`
  - `CHIRON_INTEGRATION_REPORT_OLD.md`
  - `CONVERSION_FINAL_REPORT.md`
  - `CONVERTER_GUIDE.md`
  - `DE431_CONVERSION_PROGRESS.md`
  - `EPM2021_FINAL_RESULTS.md`
  - `EPM2021_NATIVE_PARAMS.md`
  - `EPHEMERIS_ACCURACY_COMPARISON_FULL.md`
  - `EPHEMERIS_ACCURACY_COMPARISON_SUMMARY.md`
  - `EPHEMERIS_COMPARISON.md`
  - `EPHEMERIS_COMPARISON_SUMMARY.md`
  - `EPHEMERIS_FORMATS_AND_COMPARISON.md`
  - `EXECUTIVE_SUMMARY.md`
  - `MISSION_ACCOMPLISHED_NATIVE_INTERVALS.md`
  - `NATIVE_INTERVALS_EXACT.md`
  - `NATIVE_INTERVALS_GUIDE.md`
  - `PRECISION_RECOMMENDATIONS.md`
  - `QUICK_REFERENCE.md`
  - `QUICKSTART.md`
  - `SWISS_EPHEMERIS_GUIDE.md`
  - `SWISS_EPHEMERIS_SETUP.md`
  - `SWISS_EPH_FINAL_DECISION.md`
  - `SWISS_EPH_FINAL_STATUS.md`
  - `SWISS_EPH_FIX_GUIDE.md`

### Keep Separate:
- ✅ `README.md` - Project landing page (short overview + quick start)
- ✅ `LICENSE` - MIT license
- ✅ `.github/copilot-instructions.md` - AI agent guidelines
- ✅ `CLEANUP_PLAN.md` - This file

---

## 🗑️ DELETE (Only Log Files)

### Log Files (temporary outputs)
- ❌ `conversion_errors.txt`
- ❌ `conversion_log.txt`
- ❌ `conversion_status.txt`
- ❌ `BINARY_FIX_COMPLETE.txt`
- ❌ `BENCHMARK_RESULTS.txt`
- ❌ `ACCURACY_TEST_RESULTS.txt`
- ❌ `EPHEMERIS_INVENTORY_FULL.txt`
- ❌ `CONVERSION_SUCCESS.txt`
- ❌ `EPM2021_CONVERSION_RESULTS.txt`

### Session Changelogs (internal notes)
- ❌ `CHANGELOG.md` - Superseded by git history
- ❌ `SESSION_11_CHANGELOG.md`
- ❌ `SESSION_ACCURACY_CHANGELOG.md`

---

## 📦 NO ARCHIVE NEEDED

All code and tools stay in place. Old documentation merged into COMPLETE_DOCUMENTATION.md.

### Log Files (7 files)
- ❌ `conversion_errors.txt`
- ❌ `conversion_log.txt`
- ❌ `conversion_status.txt`
- ❌ `BINARY_FIX_COMPLETE.txt`
- ❌ `BENCHMARK_RESULTS.txt`
- ❌ `ACCURACY_TEST_RESULTS.txt`
- ❌ `EPHEMERIS_INVENTORY_FULL.txt`

### Old Documentation (22 files)
- ❌ `ACCURACY_SUMMARY_QUICK.md` - Superseded by FINAL_ACCURACY_REPORT
- ❌ `ASTEROIDS_AND_NODES_ANALYSIS.md` - Merged into USER_GUIDE
- ❌ `AVAILABLE_EPHEMERIDES_COMPLETE.md` - Merged into USER_GUIDE
- ❌ `CHANGELOG.md` - Move to archive
- ❌ `CHIRON_AND_LUNAR_NODES_GUIDE.md` - Merged into USER_GUIDE
- ❌ `CHIRON_DATA_ACQUISITION_REPORT.md` - Superseded by FINAL_REPORT
- ❌ `CHIRON_INTEGRATION_REPORT_OLD.md` - Obsolete version
- ❌ `CONVERSION_FINAL_REPORT.md` - Merged into USER_GUIDE
- ❌ `CONVERTER_GUIDE.md` - Merged into USER_GUIDE
- ❌ `CONVERSION_SUCCESS.txt` - Obsolete
- ❌ `DE431_CONVERSION_PROGRESS.md` - Obsolete (DE431 not recommended)
- ❌ `EPM2021_CONVERSION_RESULTS.txt` - Obsolete
- ❌ `EPM2021_FINAL_RESULTS.md` - Merged into USER_GUIDE
- ❌ `EPM2021_NATIVE_PARAMS.md` - Merged into USER_GUIDE
- ❌ `EPHEMERIS_ACCURACY_COMPARISON_FULL.md` - Superseded by FINAL_ACCURACY_REPORT
- ❌ `EPHEMERIS_ACCURACY_COMPARISON_SUMMARY.md` - Superseded by FINAL_ACCURACY_REPORT
- ❌ `EPHEMERIS_COMPARISON.md` - Superseded by FINAL_ACCURACY_REPORT
- ❌ `EPHEMERIS_COMPARISON_SUMMARY.md` - Superseded by FINAL_ACCURACY_REPORT
- ❌ `EPHEMERIS_FORMATS_AND_COMPARISON.md` - Merged into USER_GUIDE
- ❌ `EXECUTIVE_SUMMARY.md` - Superseded by USER_GUIDE
- ❌ `MISSION_ACCOMPLISHED_NATIVE_INTERVALS.md` - Internal note
- ❌ `NATIVE_INTERVALS_EXACT.md` - Merged into USER_GUIDE
- ❌ `NATIVE_INTERVALS_GUIDE.md` - Merged into USER_GUIDE
- ❌ `PRECISION_RECOMMENDATIONS.md` - Merged into USER_GUIDE
- ❌ `QUICK_REFERENCE.md` - Superseded by USER_GUIDE
- ❌ `QUICKSTART.md` - Merged into USER_GUIDE
- ❌ `SESSION_11_CHANGELOG.md` - Internal
- ❌ `SESSION_ACCURACY_CHANGELOG.md` - Internal
- ❌ `SWISS_EPHEMERIS_GUIDE.md` - Merged into USER_GUIDE
- ❌ `SWISS_EPHEMERIS_SETUP.md` - Merged into USER_GUIDE
- ❌ `SWISS_EPH_FINAL_DECISION.md` - Merged into FINAL_ACCURACY_REPORT
- ❌ `SWISS_EPH_FINAL_STATUS.md` - Merged into FINAL_ACCURACY_REPORT
- ❌ `SWISS_EPH_FIX_GUIDE.md` - Obsolete

---

## 📦 ARCHIVE (Historical Documentation)

Create `docs/archive/` folder for:
- All old .md files (keep for reference)
- Session changelogs
- Intermediate reports

---

## Summary Statistics (REVISED)

- **Keep:** ~80+ files (all code, tools, converters, benchmarks, experimental readers)
- **Delete:** ~10 files (only log files and session notes)
- **Merge docs:** 30+ markdown files → 1 comprehensive `COMPLETE_DOCUMENTATION.md`

**Benefits:**
- ✅ All experimental code preserved for future development
- ✅ All benchmarks and converters available for testing
- ✅ Complete documentation in single searchable file
- ✅ Clean git history (no large deletions)
- 🗑️ Only temporary logs removed (can be regenerated)
