#!/usr/bin/env python3
"""
Convert Swiss Ephemeris .se1 files to unified .eph format

Swiss Ephemeris uses proprietary compressed Chebyshev polynomials.
This converter extracts data using swisseph Python library and
converts to our standard .eph format.

Requirements:
    pip install pyswisseph numpy

Usage:
    python tools/swisseph2eph.py ephe/ output.eph --bodies 1,2,3,301,399 --interval 16.0
"""

import sys
import struct
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

try:
    import swisseph as swe
except ImportError:
    print("ERROR: pyswisseph not installed. Run: pip install pyswisseph", file=sys.stderr)
    sys.exit(1)


# NAIF body ID mapping for Swiss Ephemeris
BODY_MAPPING = {
    # Planets (NAIF)
    1: swe.MERCURY,
    2: swe.VENUS,
    3: swe.EARTH,  # Actually EMB in JPL
    4: swe.MARS,
    5: swe.JUPITER,
    6: swe.SATURN,
    7: swe.URANUS,
    8: swe.NEPTUNE,
    9: swe.PLUTO,
    10: swe.SUN,
    301: swe.MOON,
    399: swe.EARTH,
}

BODY_NAMES = {
    1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
    5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune",
    9: "Pluto", 10: "Sun", 301: "Moon", 399: "Earth",
}


class SwissEph2Eph:
    """Convert Swiss Ephemeris to .eph format"""

    def __init__(self, ephe_path: str, output_path: str, body_ids: List[int]):
        self.ephe_path = Path(ephe_path)
        self.output_path = Path(output_path)
        self.body_ids = body_ids

        if not self.ephe_path.exists():
            raise FileNotFoundError(f"Swiss Ephemeris directory not found: {ephe_path}")

        # Initialize Swiss Ephemeris
        swe.set_ephe_path(str(self.ephe_path))

    def convert(self, start_jd: float, end_jd: float, interval_days: float = 16.0, degree: int = 7):
        """
        Convert Swiss Ephemeris data to .eph format

        Args:
            start_jd: Start Julian Date
            end_jd: End Julian Date
            interval_days: Interval size in days (default: 16)
            degree: Chebyshev polynomial degree (default: 7)
        """
        print(f"Converting Swiss Ephemeris to: {self.output_path}")
        print(f"Time range: JD {start_jd:.2f} to {end_jd:.2f}")

        # Generate intervals
        intervals = self._generate_intervals(start_jd, end_jd, interval_days)
        num_intervals = len(intervals)
        print(f"Intervals: {num_intervals} x {interval_days} days")

        # Extract coefficients for each body
        all_coeffs = {}
        print(f"Processing {len(self.body_ids)} bodies...")

        for body_id in self.body_ids:
            body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
            print(f"  {body_name} (ID {body_id})...", end="", flush=True)

            try:
                coeffs = self._extract_coefficients(body_id, intervals, degree)
                all_coeffs[body_id] = coeffs
                print(f" OK ({len(coeffs)} intervals)")
            except Exception as e:
                print(f" SKIP ({e})")
                continue

        if not all_coeffs:
            raise RuntimeError("No valid bodies extracted")

        # Write .eph file
        print(f"Writing output: {self.output_path}")
        self._write_eph_file(all_coeffs, intervals, interval_days, degree)

        # Statistics
        input_size = sum(f.stat().st_size for f in self.ephe_path.glob("*.se1"))
        output_size = self.output_path.stat().st_size

        print(f"\nConversion complete!")
        print(f"  Input size:  {input_size:,} bytes ({input_size/1024/1024:.2f} MB)")
        print(f"  Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
        print(f"  Compression: {input_size/output_size:.2f}x smaller")

    def _generate_intervals(self, start_jd: float, end_jd: float, interval_days: float) -> List[Tuple[float, float]]:
        """Generate list of (jd_start, jd_end) intervals"""
        intervals = []
        current = start_jd

        while current < end_jd:
            interval_end = min(current + interval_days, end_jd)
            intervals.append((current, interval_end))
            current = interval_end

        return intervals

    def _extract_coefficients(self, body_id: int, intervals: List[Tuple[float, float]], degree: int) -> List[Dict]:
        """
        Extract Chebyshev coefficients for body over all intervals

        Uses least-squares fitting to approximate Swiss Ephemeris data
        with Chebyshev polynomials.
        """
        swe_body = BODY_MAPPING.get(body_id)
        if swe_body is None:
            raise ValueError(f"Body {body_id} not supported by Swiss Ephemeris")

        coeffs_list = []

        for jd_start, jd_end in intervals:
            # Sample positions over interval
            num_samples = degree * 2 + 1  # Nyquist sampling
            jds = np.linspace(jd_start, jd_end, num_samples)

            positions = []
            for jd in jds:
                try:
                    # Swiss Ephemeris: calc_ut returns [longitude, latitude, distance, speed_long, speed_lat, speed_dist]
                    # We need heliocentric cartesian coordinates
                    result = swe.calc_ut(jd, swe_body, swe.FLG_HELCTR | swe.FLG_SWIEPH)

                    # Convert from heliocentric ecliptic (result[0:3]) to cartesian
                    # Swiss Ephemeris returns: lon, lat, distance
                    lon, lat, dist = result[0:3]

                    # Spherical to Cartesian
                    lon_rad = np.radians(lon)
                    lat_rad = np.radians(lat)

                    x = dist * np.cos(lat_rad) * np.cos(lon_rad)
                    y = dist * np.cos(lat_rad) * np.sin(lon_rad)
                    z = dist * np.sin(lat_rad)

                    positions.append([x, y, z])
                except Exception as e:
                    raise RuntimeError(f"Failed to compute position at JD {jd}: {e}")

            positions = np.array(positions)

            # Fit Chebyshev polynomials
            t_normalized = 2 * (jds - jd_start) / (jd_end - jd_start) - 1  # [-1, 1]

            coeffs_x = np.polynomial.chebyshev.chebfit(t_normalized, positions[:, 0], degree)
            coeffs_y = np.polynomial.chebyshev.chebfit(t_normalized, positions[:, 1], degree)
            coeffs_z = np.polynomial.chebyshev.chebfit(t_normalized, positions[:, 2], degree)

            coeffs_list.append({
                'x': coeffs_x.tolist(),
                'y': coeffs_y.tolist(),
                'z': coeffs_z.tolist()
            })

        return coeffs_list

    def _write_eph_file(self, all_coeffs: Dict, intervals: List[Tuple[float, float]],
                        interval_days: float, degree: int):
        """Write .eph binary file"""

        num_bodies = len(all_coeffs)
        num_intervals = len(intervals)
        start_jd = intervals[0][0]
        end_jd = intervals[-1][1]

        with open(self.output_path, 'wb') as f:
            # Header (512 bytes)
            header = struct.pack(
                '4s I I I d d d I 464x',
                b'EPH\0',              # magic
                1,                      # version
                num_bodies,
                num_intervals,
                interval_days,
                start_jd,
                end_jd,
                degree
            )
            f.write(header)

            # Body table (32 bytes each)
            data_offset = 512 + num_bodies * 32 + num_intervals * 16

            for body_id in sorted(all_coeffs.keys()):
                body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
                body_entry = struct.pack(
                    'i 24s Q',
                    body_id,
                    body_name.encode('ascii')[:24],
                    data_offset
                )
                f.write(body_entry)

                # Calculate next offset
                coeffs_per_interval = (degree + 1) * 3  # x, y, z
                bytes_per_interval = coeffs_per_interval * 8  # doubles
                data_offset += num_intervals * bytes_per_interval

            # Interval index (16 bytes each)
            for jd_start, jd_end in intervals:
                interval_entry = struct.pack('dd', jd_start, jd_end)
                f.write(interval_entry)

            # Coefficient data
            for body_id in sorted(all_coeffs.keys()):
                coeffs_list = all_coeffs[body_id]

                for coeffs in coeffs_list:
                    # Write X, Y, Z coefficients
                    for axis in ['x', 'y', 'z']:
                        coeff_data = struct.pack(f'{len(coeffs[axis])}d', *coeffs[axis])
                        f.write(coeff_data)


def main():
    parser = argparse.ArgumentParser(description='Convert Swiss Ephemeris to .eph format')
    parser.add_argument('ephe_path', help='Path to Swiss Ephemeris directory (containing .se1 files)')
    parser.add_argument('output', help='Output .eph file path')
    parser.add_argument('--bodies', default='1,2,3,4,5,6,7,8,9,10,301,399',
                       help='Comma-separated body IDs (default: planets+Moon+Earth)')
    parser.add_argument('--start-jd', type=float, default=2414992.5,
                       help='Start Julian Date (default: 1900-01-01)')
    parser.add_argument('--end-jd', type=float, default=2488068.5,
                       help='End Julian Date (default: 2100-01-01)')
    parser.add_argument('--interval', type=float, default=16.0,
                       help='Interval size in days (default: 16.0)')
    parser.add_argument('--degree', type=int, default=7,
                       help='Chebyshev polynomial degree (default: 7)')

    args = parser.parse_args()

    body_ids = [int(b.strip()) for b in args.bodies.split(',')]

    converter = SwissEph2Eph(args.ephe_path, args.output, body_ids)
    converter.convert(args.start_jd, args.end_jd, args.interval, args.degree)


if __name__ == '__main__':
    main()
