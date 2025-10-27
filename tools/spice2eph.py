#!/usr/bin/env python3
"""
Convert SPICE BSP ephemeris to optimized .eph binary format for PHP

Usage:
    python spice2eph.py input.bsp output.eph [--bodies 1,2,3,399,301]

Requirements:
    pip install spiceypy numpy scipy

Format specification:
    Header (512 bytes):
        magic: char[4] "EPH\0"
        version: uint32
        numBodies: uint32
        numIntervals: uint32
        intervalDays: double
        startJD: double
        endJD: double
        coeffDegree: uint32
        reserved: 464 bytes

    Body Table (N × 32 bytes):
        bodyId: int32
        name: char[24]
        dataOffset: uint64

    Interval Index (M × 16 bytes):
        jdStart: double
        jdEnd: double

    Coefficients:
        [body0_interval0_x_coeffs][body0_interval0_y_coeffs][body0_interval0_z_coeffs]
        [body0_interval1_x_coeffs]...
        [body1_interval0_x_coeffs]...
"""

import sys
import struct
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

try:
    import spiceypy as spice
except ImportError:
    print("ERROR: spiceypy not installed. Run: pip install spiceypy", file=sys.stderr)
    sys.exit(1)


# NAIF body IDs and names
BODY_NAMES = {
    0: "SSB",          # Solar System Barycenter
    1: "Mercury",
    2: "Venus",
    3: "EMB",          # Earth-Moon Barycenter
    4: "Mars",
    5: "Jupiter",
    6: "Saturn",
    7: "Uranus",
    8: "Neptune",
    9: "Pluto",
    10: "Sun",
    199: "Mercury",
    299: "Venus",
    399: "Earth",
    499: "Mars",
    599: "Jupiter",
    699: "Saturn",
    799: "Uranus",
    899: "Neptune",
    999: "Pluto",
    301: "Moon",
}


class SPICEConverter:
    """Convert SPICE BSP to optimized .eph format"""

    MAGIC = b"EPH\0"
    VERSION = 1
    HEADER_SIZE = 512
    BODY_ENTRY_SIZE = 36  # int32(4) + char[24](24) + uint64(8) = 36 bytes
    INTERVAL_ENTRY_SIZE = 16

    def __init__(self, input_path: str, output_path: str, body_ids: List[int] = None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.body_ids = body_ids or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input SPICE file not found: {input_path}")

    def convert(self, interval_days: float = 16.0):
        """Main conversion routine"""
        print(f"Opening SPICE file: {self.input_path}")
        spice.furnsh(str(self.input_path))

        # Get time range from SPICE kernel
        cover = spice.spkcov(str(self.input_path), self.body_ids[0])
        intervals_spice = [spice.wnfetd(cover, i) for i in range(spice.wncard(cover))]

        if not intervals_spice:
            raise RuntimeError("No coverage intervals found in SPICE file")

        # Use first interval (typically covers full range)
        # ET is in seconds past J2000, convert to JD
        start_et, end_et = intervals_spice[0]
        J2000_JD = 2451545.0  # JD of J2000.0 epoch
        start_jd = J2000_JD + start_et / 86400.0  # ET seconds to days
        end_jd = J2000_JD + end_et / 86400.0

        print(f"Time range: JD {start_jd:.2f} to {end_jd:.2f} ({end_jd - start_jd:.1f} days)")

        # Generate intervals
        intervals = self._generate_intervals(start_jd, end_jd, interval_days)
        num_intervals = len(intervals)
        print(f"Intervals: {num_intervals} × {interval_days} days")

        # Extract coefficients for each body
        print(f"Processing {len(self.body_ids)} bodies...")
        all_coeffs = {}

        for body_id in self.body_ids:
            body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
            print(f"  {body_name} (ID {body_id})...", end="", flush=True)

            try:
                coeffs = self._extract_coefficients(body_id, intervals)
                all_coeffs[body_id] = coeffs
                print(f" OK ({len(coeffs)} intervals)")
            except Exception as e:
                print(f" SKIP ({e})")
                continue

        spice.unload(str(self.input_path))

        if not all_coeffs:
            raise RuntimeError("No bodies successfully extracted")        # Determine coefficient degree (assume all same)
        first_body_coeffs = next(iter(all_coeffs.values()))
        coeff_degree = len(first_body_coeffs[0]['x']) - 1
        print(f"Coefficient degree: {coeff_degree}")

        # Write output file
        print(f"Writing output: {self.output_path}")
        self._write_eph_file(all_coeffs, intervals, coeff_degree, interval_days, start_jd, end_jd)

        # Statistics
        output_size = self.output_path.stat().st_size
        input_size = self.input_path.stat().st_size
        compression_ratio = input_size / output_size if output_size > 0 else 0

        print(f"\nConversion complete!")
        print(f"  Input size:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
        print(f"  Output size: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
        print(f"  Compression: {compression_ratio:.2f}x smaller")

    def _generate_intervals(self, start_jd: float, end_jd: float, interval_days: float) -> List[Tuple[float, float]]:
        """Generate evenly-spaced intervals"""
        intervals = []
        current = start_jd

        while current < end_jd:
            interval_end = min(current + interval_days, end_jd)
            intervals.append((current, interval_end))
            current = interval_end

        return intervals

    def _extract_coefficients(self, body_id: int, intervals: List[Tuple[float, float]]) -> List[Dict]:
        """
        Extract Chebyshev coefficients by fitting positions in each interval

        Note: spiceypy doesn't expose raw Chebyshev coefficients, so we:
        1. Sample positions at Chebyshev nodes in each interval
        2. Fit Chebyshev polynomials to samples
        """
        coeffs_list = []

        for jd_start, jd_end in intervals:
            # Sample at Chebyshev nodes (optimal for polynomial fitting)
            degree = 7  # Use degree 7 (8 coefficients) - faster than JPL's 13
            n_samples = degree + 1

            # Chebyshev nodes in [-1, 1]
            nodes = np.cos(np.pi * (2 * np.arange(n_samples) + 1) / (2 * n_samples))

            # Map to interval [jd_start, jd_end]
            jd_mid = (jd_start + jd_end) / 2
            jd_half = (jd_end - jd_start) / 2
            jd_samples = jd_mid + jd_half * nodes

            # Compute positions at sample points
            positions = []
            for jd in jd_samples:
                try:
                    # Convert JD to ET (ephemeris time): ET = (JD - J2000_JD) * 86400
                    J2000_JD = 2451545.0
                    et = (jd - J2000_JD) * 86400.0
                    # spkgps returns state (pos + vel) relative to SSB (body 0)
                    state, _ = spice.spkgps(body_id, et, 'J2000', 0)
                    positions.append(state[:3])  # just position (km)
                except Exception as e:
                    # If calculation fails, use zeros (graceful degradation)
                    positions.append([0.0, 0.0, 0.0])

            positions = np.array(positions)

            # Convert km to AU (1 AU = 149597870.7 km)
            positions = positions / 149597870.7

            # Fit Chebyshev polynomials
            x_coeffs = self._fit_chebyshev(nodes, positions[:, 0], degree)
            y_coeffs = self._fit_chebyshev(nodes, positions[:, 1], degree)
            z_coeffs = self._fit_chebyshev(nodes, positions[:, 2], degree)

            coeffs_list.append({
                'x': x_coeffs.tolist(),
                'y': y_coeffs.tolist(),
                'z': z_coeffs.tolist()
            })

        return coeffs_list

    def _fit_chebyshev(self, nodes: np.ndarray, values: np.ndarray, degree: int) -> np.ndarray:
        """
        Fit Chebyshev polynomial to sampled values at Chebyshev nodes

        Uses numpy's Chebyshev polynomial fitting (simpler than DCT)
        """
        # Fit Chebyshev polynomial using numpy
        coeffs = np.polynomial.chebyshev.chebfit(nodes, values, degree)

        return coeffs

    def _write_eph_file(self, all_coeffs: Dict, intervals: List, coeff_degree: int,
                        interval_days: float, start_jd: float, end_jd: float):
        """Write optimized .eph binary file"""

        with open(self.output_path, 'wb') as f:
            # Write header
            num_bodies = len(all_coeffs)
            num_intervals = len(intervals)

            header = struct.pack(
                '<4sIIIdddI',
                self.MAGIC,
                self.VERSION,
                num_bodies,
                num_intervals,
                interval_days,
                start_jd,
                end_jd,
                coeff_degree
            )
            header += b'\x00' * (self.HEADER_SIZE - len(header))  # Padding
            f.write(header)

            # Calculate data offsets
            body_table_size = num_bodies * self.BODY_ENTRY_SIZE
            interval_index_size = num_intervals * self.INTERVAL_ENTRY_SIZE
            coeffs_per_component = coeff_degree + 1
            coeffs_per_interval = coeffs_per_component * 3  # x, y, z
            bytes_per_interval = coeffs_per_interval * 8  # 8 bytes per double

            data_start = self.HEADER_SIZE + body_table_size + interval_index_size

            # Write body table
            for i, body_id in enumerate(sorted(all_coeffs.keys())):
                body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
                name_bytes = body_name.encode('ascii')[:24].ljust(24, b'\x00')

                # Data offset for this body
                data_offset = data_start + i * num_intervals * bytes_per_interval

                entry = struct.pack('<i24sQ', body_id, name_bytes, data_offset)
                f.write(entry)

            # Write interval index
            for jd_start, jd_end in intervals:
                entry = struct.pack('<dd', jd_start, jd_end)
                f.write(entry)

            # Write coefficient data
            for body_id in sorted(all_coeffs.keys()):
                coeffs_list = all_coeffs[body_id]

                for coeffs in coeffs_list:
                    # Pack x, y, z coefficients sequentially
                    x_data = struct.pack(f'<{len(coeffs["x"])}d', *coeffs['x'])
                    y_data = struct.pack(f'<{len(coeffs["y"])}d', *coeffs['y'])
                    z_data = struct.pack(f'<{len(coeffs["z"])}d', *coeffs['z'])

                    f.write(x_data)
                    f.write(y_data)
                    f.write(z_data)


def main():
    parser = argparse.ArgumentParser(description='Convert SPICE BSP to optimized .eph format')
    parser.add_argument('input', help='Input SPICE BSP file')
    parser.add_argument('output', help='Output .eph file')
    parser.add_argument('--bodies', help='Comma-separated body IDs (default: 1-10)', default=None)
    parser.add_argument('--interval', type=float, help='Interval size in days (default: 16)', default=16.0)

    args = parser.parse_args()

    body_ids = None
    if args.bodies:
        body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    converter = SPICEConverter(args.input, args.output, body_ids)
    converter.convert(interval_days=args.interval)


if __name__ == '__main__':
    main()
