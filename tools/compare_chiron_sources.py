#!/usr/bin/env python3
"""
Compare Chiron positions from three sources:
1. JPL Horizons (via .eph file) - reference
2. Swiss Ephemeris (via FFI)
3. Original JSON data (validation)

This script measures accuracy of our .eph conversion and compares
with Swiss Ephemeris built-in Chiron ephemeris (ID=15).

Author: AI Assistant
Date: 2025-10-30
"""

import json
import struct
import sys
from pathlib import Path
import numpy as np

# Try to import Swiss Ephemeris (optional)
try:
    import swisseph as swe
    HAS_SWISSEPH = True
except ImportError:
    HAS_SWISSEPH = False
    print("WARNING: swisseph module not found, Swiss Eph comparison will be skipped")
    print("  Install with: pip install pyswisseph")
    print()


class ChironComparison:
    """Compare Chiron data from multiple sources."""

    AU_TO_KM = 149597870.7  # km per AU

    def __init__(self):
        self.json_file = Path("data/chiron/chiron_vectors_jpl.json")
        self.eph_file = Path("data/chiron/chiron_jpl.eph")
        self.ephe_path = Path("ephe")  # Swiss Ephemeris data files

        self.json_data = None
        self.eph_file_handle = None
        self.eph_header = None
        self.eph_intervals = []

    def load_json(self):
        """Load original JPL Horizons JSON data."""
        print("Loading JPL Horizons JSON data...")
        with open(self.json_file, 'r') as f:
            self.json_data = json.load(f)
        print(f"  ✓ Loaded {len(self.json_data['epochs'])} points\n")

    def load_eph_file(self):
        """Load binary .eph file."""
        print("Loading binary .eph file...")
        self.eph_file_handle = open(self.eph_file, 'rb')

        # Read header
        header_data = self.eph_file_handle.read(512)
        unpacked = struct.unpack('<4sIIIdddI', header_data[:44])

        self.eph_header = {
            'magic': unpacked[0],
            'version': unpacked[1],
            'num_bodies': unpacked[2],
            'num_intervals': unpacked[3],
            'interval_days': unpacked[4],
            'start_jd': unpacked[5],
            'end_jd': unpacked[6],
            'coeff_degree': unpacked[7]
        }

        # Skip body table (40 bytes)
        self.eph_file_handle.seek(512 + 40)

        # Read intervals
        for i in range(self.eph_header['num_intervals']):
            interval_data = self.eph_file_handle.read(16)
            jd_start, jd_end = struct.unpack('<dd', interval_data)
            self.eph_intervals.append({'jd_start': jd_start, 'jd_end': jd_end})

        print(f"  ✓ Loaded {len(self.eph_intervals)} intervals\n")

    def get_json_position(self, jd):
        """Get position from JSON data (nearest epoch)."""
        epochs = np.array(self.json_data['epochs'])
        idx = np.argmin(np.abs(epochs - jd))

        if abs(epochs[idx] - jd) > 8.0:  # More than 8 days away
            return None

        vector = self.json_data['vectors'][idx]
        return np.array([vector['x'], vector['y'], vector['z']])

    def get_eph_position(self, jd):
        """Get position from .eph file (Chebyshev interpolation)."""
        # Find interval
        interval_idx = None
        for idx, interval in enumerate(self.eph_intervals):
            if interval['jd_start'] <= jd <= interval['jd_end']:
                interval_idx = idx
                break

        if interval_idx is None:
            return None

        interval = self.eph_intervals[interval_idx]

        # Normalize time
        t_norm = 2.0 * (jd - interval['jd_start']) / (interval['jd_end'] - interval['jd_start']) - 1.0

        # Read coefficients
        degree = self.eph_header['coeff_degree']
        coeffs_per_interval = 3 * (degree + 1)
        bytes_per_interval = coeffs_per_interval * 8

        # Data starts after header (512) + body table (40) + interval index (72*16)
        data_offset = 512 + 40 + self.eph_header['num_intervals'] * 16
        offset = data_offset + interval_idx * bytes_per_interval

        self.eph_file_handle.seek(offset)
        coeff_data = self.eph_file_handle.read(bytes_per_interval)
        coeffs = struct.unpack(f'<{coeffs_per_interval}d', coeff_data)

        # Split into X, Y, Z
        n = degree + 1
        x_coeffs = coeffs[0:n]
        y_coeffs = coeffs[n:2*n]
        z_coeffs = coeffs[2*n:3*n]

        # Evaluate Chebyshev polynomials
        x = self.eval_chebyshev(x_coeffs, t_norm)
        y = self.eval_chebyshev(y_coeffs, t_norm)
        z = self.eval_chebyshev(z_coeffs, t_norm)

        return np.array([x, y, z])

    def get_swisseph_position(self, jd):
        """Get position from Swiss Ephemeris."""
        if not HAS_SWISSEPH:
            return None

        # Set ephemeris path
        swe.set_ephe_path(str(self.ephe_path.absolute()))

        # SE_CHIRON = 15
        # SEFLG_SWIEPH = 2 (use .se1 files)
        # SEFLG_HELCTR = 8 (heliocentric)
        # SEFLG_XYZ = 4096 (Cartesian coordinates)
        flags = 2 | 8 | 4096

        try:
            result = swe.calc_ut(jd, 15, flags)
            # result is tuple: (data_array, flags)
            # data_array = [x, y, z, dx, dy, dz]
            return np.array(result[0][:3])  # Just X, Y, Z
        except Exception as e:
            print(f"  Swiss Eph error at JD {jd}: {e}")
            return None

    @staticmethod
    def eval_chebyshev(coeffs, x):
        """Evaluate Chebyshev polynomial using Clenshaw's algorithm."""
        n = len(coeffs)
        if n == 0:
            return 0.0
        if n == 1:
            return coeffs[0]

        b_k_plus_2 = 0.0
        b_k_plus_1 = 0.0

        for k in range(n - 1, 0, -1):
            b_k = 2.0 * x * b_k_plus_1 - b_k_plus_2 + coeffs[k]
            b_k_plus_2 = b_k_plus_1
            b_k_plus_1 = b_k

        return x * b_k_plus_1 - b_k_plus_2 + coeffs[0]

    def compare_sources(self, test_epochs):
        """Compare positions from all sources."""
        print("=" * 70)
        print("Chiron Position Comparison")
        print("=" * 70)
        print()
        print("Sources:")
        print("  1. JPL Horizons JSON (reference)")
        print("  2. Binary .eph file (Chebyshev)")
        if HAS_SWISSEPH:
            print("  3. Swiss Ephemeris (ID=15)")
        print()

        results = []

        for epoch_name, jd in test_epochs:
            print(f"Epoch: {epoch_name} (JD {jd})")
            print("-" * 70)

            # Get positions from all sources
            json_pos = self.get_json_position(jd)
            eph_pos = self.get_eph_position(jd)
            swe_pos = self.get_swisseph_position(jd) if HAS_SWISSEPH else None

            if json_pos is None:
                print("  ⚠ No JSON data for this epoch\n")
                continue

            # Print positions
            print(f"  JPL JSON:  X={json_pos[0]:+.8f}  Y={json_pos[1]:+.8f}  Z={json_pos[2]:+.8f} AU")

            if eph_pos is not None:
                print(f"  .eph file: X={eph_pos[0]:+.8f}  Y={eph_pos[1]:+.8f}  Z={eph_pos[2]:+.8f} AU")

                # Compute error
                diff = eph_pos - json_pos
                error_au = np.linalg.norm(diff)
                error_km = error_au * self.AU_TO_KM

                print(f"    → Error: {error_au:.3e} AU ({error_km:.3f} km)")

            if swe_pos is not None:
                print(f"  Swiss Eph: X={swe_pos[0]:+.8f}  Y={swe_pos[1]:+.8f}  Z={swe_pos[2]:+.8f} AU")

                # Compute error vs JPL
                diff = swe_pos - json_pos
                error_au = np.linalg.norm(diff)
                error_km = error_au * self.AU_TO_KM

                print(f"    → Error vs JPL: {error_au:.3e} AU ({error_km:.0f} km)")

                results.append({
                    'epoch': epoch_name,
                    'jd': jd,
                    'eph_error_km': np.linalg.norm(eph_pos - json_pos) * self.AU_TO_KM if eph_pos is not None else None,
                    'swe_error_km': error_km
                })

            print()

        # Summary statistics
        if results:
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print()

            eph_errors = [r['eph_error_km'] for r in results if r['eph_error_km'] is not None]
            swe_errors = [r['swe_error_km'] for r in results if r['swe_error_km'] is not None]

            if eph_errors:
                print("Binary .eph file accuracy:")
                print(f"  RMS error:    {np.sqrt(np.mean(np.array(eph_errors)**2)):.3f} km")
                print(f"  Mean error:   {np.mean(eph_errors):.3f} km")
                print(f"  Median error: {np.median(eph_errors):.3f} km")
                print(f"  Max error:    {np.max(eph_errors):.3f} km")
                print()

            if swe_errors:
                print("Swiss Ephemeris accuracy (vs JPL Horizons):")
                print(f"  RMS error:    {np.sqrt(np.mean(np.array(swe_errors)**2)):.0f} km")
                print(f"  Mean error:   {np.mean(swe_errors):.0f} km")
                print(f"  Median error: {np.median(swe_errors):.0f} km")
                print(f"  Max error:    {np.max(swe_errors):.0f} km")
                print()

    def run(self):
        """Run comparison."""
        self.load_json()
        self.load_eph_file()

        # Use EXACT epochs from JSON data (subset for testing)
        epochs_array = np.array(self.json_data['epochs'])

        # Select test epochs: every 300th point (about 7 samples)
        indices = np.arange(0, len(epochs_array), 300)

        test_epochs = []
        for idx in indices:
            jd = epochs_array[idx]
            # Convert JD to approximate year for label
            year = 2000 + (jd - 2451545.0) / 365.25
            test_epochs.append((f"Index {idx} (~{year:.0f})", jd))

        self.compare_sources(test_epochs)        # Cleanup
        if self.eph_file_handle:
            self.eph_file_handle.close()


def main():
    """Main entry point."""
    print("=" * 70)
    print("Chiron Multi-Source Comparison Tool")
    print("=" * 70)
    print()

    comparison = ChironComparison()
    comparison.run()

    print("=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
