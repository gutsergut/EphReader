#!/usr/bin/env python3
"""
Convert SPICE BSP to MessagePack format (.msgpack)

Advantages:
- Compact binary serialization (smaller than JSON, faster than SQLite)
- Native support in many languages (msgpack-php extension)
- Easy to inspect/debug (can convert to JSON)
- Faster deserialization than SQLite
- No database overhead

Format:
{
  "metadata": {...},
  "bodies": {bodyId: {"name": str, "intervals": [...]}},
  "intervals": [{"start": float, "end": float}],
  "coefficients": {
    bodyId: [
      {"x": [c0, c1, ...], "y": [...], "z": [...]},  # interval 0
      ...
    ]
  }
}

Usage:
    python spice2msgpack.py input.bsp output.msgpack [--bodies 1,2,3,399,301]
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict
import numpy as np

try:
    import spiceypy as spice
except ImportError:
    print("ERROR: spiceypy not installed. Run: pip install spiceypy", file=sys.stderr)
    sys.exit(1)

try:
    import msgpack
except ImportError:
    print("ERROR: msgpack not installed. Run: pip install msgpack", file=sys.stderr)
    sys.exit(1)


# NAIF body IDs and names
BODY_NAMES = {
    0: "SSB", 1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
    5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune", 9: "Pluto",
    10: "Sun", 199: "Mercury", 299: "Venus", 399: "Earth", 499: "Mars",
    599: "Jupiter", 699: "Saturn", 799: "Uranus", 899: "Neptune",
    999: "Pluto", 301: "Moon",
}


class SPICEtoMessagePack:
    """Convert SPICE BSP to MessagePack format"""

    def __init__(self, input_path: str, output_path: str, body_ids: List[int] = None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.body_ids = body_ids or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input SPICE file not found: {input_path}")

    def convert(self, interval_days: float = 32.0):
        """Main conversion routine"""
        print(f"Opening SPICE file: {self.input_path}")
        spice.furnsh(str(self.input_path))

        # Get time range
        cover = spice.spkcov(str(self.input_path), self.body_ids[0])
        intervals_spice = [spice.wnfetd(cover, i) for i in range(spice.wncard(cover))]

        if not intervals_spice:
            raise RuntimeError("No coverage intervals found in SPICE file")

        start_et, end_et = intervals_spice[0]
        J2000_JD = 2451545.0
        start_jd = J2000_JD + start_et / 86400.0
        end_jd = J2000_JD + end_et / 86400.0

        print(f"Time range: JD {start_jd:.2f} to {end_jd:.2f} ({end_jd - start_jd:.1f} days)")

        # Generate intervals
        intervals = self._generate_intervals(start_jd, end_jd, interval_days)
        num_intervals = len(intervals)
        print(f"Intervals: {num_intervals} x {interval_days} days")

        # Build MessagePack structure
        data = {
            'metadata': {
                'version': '1.0',
                'format': 'msgpack',
                'source': str(self.input_path.name),
                'start_jd': start_jd,
                'end_jd': end_jd,
                'interval_days': interval_days,
                'num_intervals': num_intervals,
                'num_bodies': len(self.body_ids),
                'chebyshev_degree': 7
            },
            'bodies': {},
            'intervals': [{'start': s, 'end': e} for s, e in intervals],
            'coefficients': {}
        }

        # Process bodies
        print(f"Processing {len(self.body_ids)} bodies...")
        for body_id in self.body_ids:
            body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
            print(f"  {body_name} (ID {body_id})...", end="", flush=True)

            try:
                coeffs_list = self._extract_coefficients(body_id, intervals)

                data['bodies'][body_id] = {
                    'name': body_name,
                    'num_intervals': len(coeffs_list)
                }

                # Store coefficients as nested lists
                data['coefficients'][body_id] = coeffs_list

                print(f" OK ({len(coeffs_list)} intervals)")
            except Exception as e:
                print(f" SKIP ({e})")
                continue

        spice.unload(str(self.input_path))

        # Write MessagePack file
        print(f"Writing MessagePack: {self.output_path}")
        with open(self.output_path, 'wb') as f:
            packed = msgpack.packb(data, use_bin_type=True)
            f.write(packed)

        # Statistics
        output_size = self.output_path.stat().st_size
        input_size = self.input_path.stat().st_size
        compression_ratio = input_size / output_size if output_size > 0 else 0

        print(f"\nConversion complete!")
        print(f"  Input size:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
        print(f"  Output size: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
        print(f"  Compression: {compression_ratio:.2f}x smaller")

    def _generate_intervals(self, start_jd: float, end_jd: float, interval_days: float) -> List:
        """Generate evenly-spaced intervals"""
        intervals = []
        current = start_jd

        while current < end_jd:
            interval_end = min(current + interval_days, end_jd)
            intervals.append((current, interval_end))
            current = interval_end

        return intervals

    def _extract_coefficients(self, body_id: int, intervals: List) -> List[Dict]:
        """Extract Chebyshev coefficients by fitting positions"""
        coeffs_list = []

        for jd_start, jd_end in intervals:
            degree = 7
            n_samples = degree + 1

            nodes = np.cos(np.pi * (2 * np.arange(n_samples) + 1) / (2 * n_samples))

            jd_mid = (jd_start + jd_end) / 2
            jd_half = (jd_end - jd_start) / 2
            jd_samples = jd_mid + jd_half * nodes

            positions = []
            for jd in jd_samples:
                try:
                    J2000_JD = 2451545.0
                    et = (jd - J2000_JD) * 86400.0
                    state, _ = spice.spkgps(body_id, et, 'J2000', 0)
                    positions.append(state[:3])
                except Exception:
                    positions.append([0.0, 0.0, 0.0])

            positions = np.array(positions) / 149597870.7  # km to AU

            x_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 0], degree)
            y_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 1], degree)
            z_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 2], degree)

            coeffs_list.append({
                'x': x_coeffs.tolist(),
                'y': y_coeffs.tolist(),
                'z': z_coeffs.tolist()
            })

        return coeffs_list


def main():
    parser = argparse.ArgumentParser(description='Convert SPICE BSP to MessagePack')
    parser.add_argument('input', help='Input SPICE BSP file')
    parser.add_argument('output', help='Output .msgpack file')
    parser.add_argument('--bodies', help='Comma-separated body IDs (default: 1-10)', default=None)
    parser.add_argument('--interval', type=float, help='Interval size in days (default: 32)', default=32.0)

    args = parser.parse_args()

    body_ids = None
    if args.bodies:
        body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    converter = SPICEtoMessagePack(args.input, args.output, body_ids)
    converter.convert(interval_days=args.interval)


if __name__ == '__main__':
    main()
