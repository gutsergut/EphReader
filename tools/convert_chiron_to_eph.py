#!/usr/bin/env python3
"""
Convert Chiron JPL Horizons vectors to optimized binary .eph format.

This converter takes heliocentric XYZ vectors from JPL Horizons and fits
Chebyshev polynomials to create a compact binary ephemeris file compatible
with EphReader.php.

Input:  data/chiron/chiron_vectors_jpl.json (517 KB, 2283 points)
Output: data/chiron/chiron_jpl.eph (binary format)

Author: AI Assistant
Date: 2025-10-30
"""

import json
import struct
import sys
from pathlib import Path
import numpy as np
from scipy.interpolate import approximate_taylor_polynomial
from numpy.polynomial.chebyshev import Chebyshev


class ChironEphConverter:
    """Convert Chiron vectors to binary .eph format."""

    # .eph format constants
    MAGIC = b'EPH\0'
    VERSION = 2
    HEADER_SIZE = 512
    BODY_ENTRY_SIZE = 36  # 4 (id) + 24 (name) + 8 (offset) - MUST match EphReader!
    INTERVAL_ENTRY_SIZE = 16

    def __init__(self, input_json, output_eph, chebyshev_degree=13):
        """
        Initialize converter.

        Args:
            input_json: Path to chiron_vectors_jpl.json
            output_eph: Path to output .eph file
            chebyshev_degree: Degree of Chebyshev polynomials (default: 13)
        """
        self.input_json = Path(input_json)
        self.output_eph = Path(output_eph)
        self.degree = chebyshev_degree

        self.data = None
        self.intervals = []
        self.coefficients = []

    def load_json(self):
        """Load JPL Horizons vectors from JSON."""
        print(f"Loading data from: {self.input_json}")

        with open(self.input_json, 'r') as f:
            self.data = json.load(f)

        metadata = self.data['metadata']
        num_points = metadata['num_points']

        print(f"  Body: {metadata['body_name']}")
        print(f"  Points: {num_points}")
        print(f"  Coverage: {metadata['start_jd']:.1f} - {metadata['stop_jd']:.1f} JD")
        print(f"  Step: {metadata['step_days']} days")
        print()

    def fit_chebyshev_intervals(self):
        """
        Fit Chebyshev polynomials to data intervals.

        Each interval spans multiple data points. We use Chebyshev polynomials
        to approximate position (XYZ) within each interval, similar to JPL DE format.
        """
        print(f"Fitting Chebyshev polynomials (degree {self.degree})...")

        epochs = np.array(self.data['epochs'])
        vectors = self.data['vectors']

        # Extract position arrays
        x_vals = np.array([v['x'] for v in vectors])
        y_vals = np.array([v['y'] for v in vectors])
        z_vals = np.array([v['z'] for v in vectors])

        # Determine interval size (number of points per interval)
        # For 16-day step, use ~32 points per interval (512 days, ~1.4 years)
        points_per_interval = 32
        step_days = self.data['metadata']['step_days']
        interval_days = points_per_interval * step_days

        print(f"  Interval size: {points_per_interval} points ({interval_days} days)")

        num_points = len(epochs)
        num_intervals = (num_points + points_per_interval - 1) // points_per_interval

        print(f"  Creating {num_intervals} intervals...")
        print()

        for i in range(num_intervals):
            start_idx = i * points_per_interval
            end_idx = min(start_idx + points_per_interval, num_points)

            # Get interval data
            interval_epochs = epochs[start_idx:end_idx]
            interval_x = x_vals[start_idx:end_idx]
            interval_y = y_vals[start_idx:end_idx]
            interval_z = z_vals[start_idx:end_idx]

            jd_start = interval_epochs[0]
            jd_end = interval_epochs[-1]

            # Normalize time to [-1, 1] for Chebyshev
            t_normalized = 2.0 * (interval_epochs - jd_start) / (jd_end - jd_start) - 1.0

            # Fit Chebyshev polynomials for X, Y, Z
            cheb_x = Chebyshev.fit(t_normalized, interval_x, self.degree)
            cheb_y = Chebyshev.fit(t_normalized, interval_y, self.degree)
            cheb_z = Chebyshev.fit(t_normalized, interval_z, self.degree)

            # Store interval metadata
            self.intervals.append({
                'jd_start': jd_start,
                'jd_end': jd_end,
                'num_points': len(interval_epochs)
            })

            # Store coefficients (degree+1 coefficients for each of X, Y, Z)
            coeffs = np.concatenate([
                cheb_x.coef,
                cheb_y.coef,
                cheb_z.coef
            ])
            self.coefficients.append(coeffs)

            if (i + 1) % 10 == 0 or (i + 1) == num_intervals:
                print(f"  Processed interval {i+1}/{num_intervals}")

        print()

    def compute_rms_error(self):
        """Compute RMS error of Chebyshev fit."""
        print("Computing RMS error...")

        epochs = np.array(self.data['epochs'])
        vectors = self.data['vectors']

        x_vals = np.array([v['x'] for v in vectors])
        y_vals = np.array([v['y'] for v in vectors])
        z_vals = np.array([v['z'] for v in vectors])

        errors = []

        for i, interval in enumerate(self.intervals):
            # Find points in this interval
            mask = (epochs >= interval['jd_start']) & (epochs <= interval['jd_end'])
            interval_epochs = epochs[mask]

            # Normalize time
            jd_start = interval['jd_start']
            jd_end = interval['jd_end']
            t_normalized = 2.0 * (interval_epochs - jd_start) / (jd_end - jd_start) - 1.0

            # Extract coefficients
            coeffs = self.coefficients[i]
            n_per_coord = self.degree + 1

            cheb_x = Chebyshev(coeffs[0:n_per_coord])
            cheb_y = Chebyshev(coeffs[n_per_coord:2*n_per_coord])
            cheb_z = Chebyshev(coeffs[2*n_per_coord:3*n_per_coord])

            # Evaluate polynomials
            x_fit = cheb_x(t_normalized)
            y_fit = cheb_y(t_normalized)
            z_fit = cheb_z(t_normalized)

            # Compute errors
            x_err = x_vals[mask] - x_fit
            y_err = y_vals[mask] - y_fit
            z_err = z_vals[mask] - z_fit

            # Position error magnitude (in AU)
            pos_err = np.sqrt(x_err**2 + y_err**2 + z_err**2)
            errors.extend(pos_err)

        errors = np.array(errors)
        rms_au = np.sqrt(np.mean(errors**2))
        max_au = np.max(errors)

        # Convert to km (1 AU = 149,597,870.7 km)
        AU_TO_KM = 149597870.7
        rms_km = rms_au * AU_TO_KM
        max_km = max_au * AU_TO_KM

        print(f"  RMS error: {rms_au:.3e} AU ({rms_km:.3f} km)")
        print(f"  Max error: {max_au:.3e} AU ({max_km:.3f} km)")
        print()

        return rms_km, max_km

    def write_binary(self):
        """Write binary .eph file."""
        print(f"Writing binary file: {self.output_eph}")

        self.output_eph.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_eph, 'wb') as f:
            # Write header (512 bytes)
            header = bytearray(self.HEADER_SIZE)

            # Magic + version
            header[0:4] = self.MAGIC
            struct.pack_into('<I', header, 4, self.VERSION)

            # Counts
            num_bodies = 1  # Only Chiron
            num_intervals = len(self.intervals)
            struct.pack_into('<I', header, 8, num_bodies)
            struct.pack_into('<I', header, 12, num_intervals)

            # Interval parameters
            first_interval = self.intervals[0]
            last_interval = self.intervals[-1]
            interval_days = last_interval['jd_end'] - first_interval['jd_start']
            interval_days /= num_intervals  # Average interval length

            struct.pack_into('<d', header, 16, interval_days)
            struct.pack_into('<d', header, 24, first_interval['jd_start'])
            struct.pack_into('<d', header, 32, last_interval['jd_end'])

            # Coefficient degree
            struct.pack_into('<I', header, 40, self.degree)

            # Reserved space (464 bytes)

            f.write(header)

            # Write body table (36 bytes per body)
            body_entry = bytearray(self.BODY_ENTRY_SIZE)

            # Body ID (Chiron = 2060)
            struct.pack_into('<i', body_entry, 0, 2060)

            # Body name (24 bytes, null-terminated)
            name = b'Chiron\0'
            body_entry[4:4+len(name)] = name

            # Data offset (after header + body table + interval index)
            data_offset = self.HEADER_SIZE + self.BODY_ENTRY_SIZE
            data_offset += num_intervals * self.INTERVAL_ENTRY_SIZE
            struct.pack_into('<Q', body_entry, 28, data_offset)  # offset at byte 28, not 32

            f.write(body_entry)

            # Write interval index (16 bytes per interval)
            for interval in self.intervals:
                index_entry = struct.pack('<dd',
                    interval['jd_start'],
                    interval['jd_end']
                )
                f.write(index_entry)

            # Write coefficients (packed doubles)
            coeffs_per_interval = 3 * (self.degree + 1)  # X, Y, Z

            for coeffs in self.coefficients:
                # Pack as doubles
                packed = struct.pack(f'<{len(coeffs)}d', *coeffs)
                f.write(packed)

        # Report size
        size_kb = self.output_eph.stat().st_size / 1024
        print(f"  OK Written: {size_kb:.1f} KB")
        print()

    def convert(self):
        """Run full conversion pipeline."""
        print("=" * 70)
        print("Chiron JPL Horizons -> Binary .eph Converter")
        print("=" * 70)
        print()

        # Load JSON data
        self.load_json()

        # Fit Chebyshev polynomials
        self.fit_chebyshev_intervals()

        # Compute accuracy
        rms_km, max_km = self.compute_rms_error()

        # Write binary file
        self.write_binary()

        # Summary
        print("=" * 70)
        print("CONVERSION COMPLETE")
        print("=" * 70)
        print()
        print(f"Input:  {self.input_json} ({self.input_json.stat().st_size / 1024:.1f} KB)")
        print(f"Output: {self.output_eph} ({self.output_eph.stat().st_size / 1024:.1f} KB)")
        print()
        print(f"Compression: {self.input_json.stat().st_size / self.output_eph.stat().st_size:.1f}x")
        print(f"Intervals: {len(self.intervals)}")
        print(f"Chebyshev degree: {self.degree}")
        print(f"RMS error: {rms_km:.3f} km")
        print(f"Max error: {max_km:.3f} km")
        print()
        print("Next step: Test with PHP EphReader")
        print()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = "data/chiron/chiron_vectors_jpl.json"

    if len(sys.argv) > 2:
        output_eph = sys.argv[2]
    else:
        output_eph = "data/chiron/chiron_jpl.eph"

    if len(sys.argv) > 3:
        degree = int(sys.argv[3])
    else:
        degree = 13  # Default degree

    converter = ChironEphConverter(input_json, output_eph, degree)
    converter.convert()


if __name__ == '__main__':
    main()
