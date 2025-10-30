#!/usr/bin/env python3
"""
Convert SPICE BSP to Hybrid format (.heph + .hidx)

Hybrid approach combines best of both worlds:
- SQLite index (.hidx): Fast lookup, SQL queries, metadata
- Binary data (.heph): Compact coefficient storage, mmap-able

Advantages:
- Fast random access (SQL index)
- Compact storage (binary coefficients)
- Easy metadata queries (SQL)
- Can mmap coefficient file for zero-copy access
- Separate index/data allows parallel processing

Files:
- output.hidx: SQLite index (metadata, body table, interval→offset mapping)
- output.heph: Raw binary coefficients (doubles, sequential)

Usage:
    python spice2hybrid.py input.bsp output [--bodies 1,2,3,399,301]
    Creates: output.hidx + output.heph
"""

import sys
import struct
import argparse
import sqlite3
from pathlib import Path
from typing import List, Dict
import numpy as np

try:
    import spiceypy as spice
except ImportError:
    print("ERROR: spiceypy not installed. Run: pip install spiceypy", file=sys.stderr)
    sys.exit(1)


BODY_NAMES = {
    0: "SSB", 1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
    5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune", 9: "Pluto",
    10: "Sun", 199: "Mercury", 299: "Venus", 399: "Earth", 499: "Mars",
    599: "Jupiter", 699: "Saturn", 799: "Uranus", 899: "Neptune",
    999: "Pluto", 301: "Moon",
}


class SPICEtoHybrid:
    """Convert SPICE BSP to Hybrid format"""

    def __init__(self, input_path: str, output_base: str, body_ids: List[int] = None):
        self.input_path = Path(input_path)

        # If output_base is a directory, derive filename from input
        output_path = Path(output_base)
        if output_path.is_dir():
            base_name = self.input_path.stem  # e.g., "de440" from "de440.bsp"
            self.output_idx = output_path / f"{base_name}.hidx"
            self.output_data = output_path / f"{base_name}.heph"
        else:
            self.output_idx = Path(output_base + '.hidx')
            self.output_data = Path(output_base + '.heph')

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
            raise RuntimeError("No coverage intervals found")

        start_et, end_et = intervals_spice[0]
        J2000_JD = 2451545.0
        start_jd = J2000_JD + start_et / 86400.0
        end_jd = J2000_JD + end_et / 86400.0

        print(f"Time range: JD {start_jd:.2f} to {end_jd:.2f}")

        # Generate intervals
        intervals = self._generate_intervals(start_jd, end_jd, interval_days)
        num_intervals = len(intervals)
        print(f"Intervals: {num_intervals} x {interval_days} days")

        # Create SQLite index
        print(f"Creating index: {self.output_idx}")
        if self.output_idx.exists():
            self.output_idx.unlink()

        conn = sqlite3.connect(str(self.output_idx))
        self._create_schema(conn)
        self._store_metadata(conn, {
            'version': '1.0',
            'format': 'hybrid',
            'source': str(self.input_path.name),
            'start_jd': str(start_jd),
            'end_jd': str(end_jd),
            'interval_days': str(interval_days),
            'num_intervals': str(num_intervals),
            'num_bodies': str(len(self.body_ids)),
            'chebyshev_degree': '7',
            'data_file': str(self.output_data.name)
        })

        # Open binary data file
        print(f"Creating data file: {self.output_data}")
        if self.output_data.exists():
            self.output_data.unlink()

        with open(self.output_data, 'wb') as data_file:
            current_offset = 0

            # Process bodies
            print(f"Processing {len(self.body_ids)} bodies...")
            for body_id in self.body_ids:
                body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
                print(f"  {body_name} (ID {body_id})...", end="", flush=True)

                try:
                    # Extract coefficients
                    coeffs_list = self._extract_coefficients(body_id, intervals)

                    # Store body in index
                    conn.execute('INSERT INTO bodies (id, name) VALUES (?, ?)',
                               (body_id, body_name))

                    # Write intervals and coefficients
                    for interval_idx, ((jd_start, jd_end), coeffs) in enumerate(zip(intervals, coeffs_list)):
                        # Write coefficients to binary file
                        x_data = struct.pack(f'{len(coeffs["x"])}d', *coeffs['x'])
                        y_data = struct.pack(f'{len(coeffs["y"])}d', *coeffs['y'])
                        z_data = struct.pack(f'{len(coeffs["z"])}d', *coeffs['z'])

                        coeff_data = x_data + y_data + z_data
                        data_offset = current_offset
                        data_size = len(coeff_data)

                        data_file.write(coeff_data)
                        current_offset += data_size

                        # Store interval in index with offset
                        conn.execute('''
                            INSERT INTO intervals (body_id, jd_start, jd_end, data_offset, data_size)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (body_id, jd_start, jd_end, data_offset, data_size))

                    print(f" OK ({len(coeffs_list)} intervals)")
                except Exception as e:
                    print(f" SKIP ({e})")
                    continue

        # Create indexes
        print("Creating SQL indexes...")
        conn.execute('CREATE INDEX idx_intervals_body ON intervals(body_id)')
        conn.execute('CREATE INDEX idx_intervals_jd ON intervals(jd_start, jd_end)')

        conn.commit()
        conn.close()
        spice.unload(str(self.input_path))

        # Statistics
        idx_size = self.output_idx.stat().st_size
        data_size = self.output_data.stat().st_size
        total_size = idx_size + data_size
        input_size = self.input_path.stat().st_size
        compression_ratio = input_size / total_size if total_size > 0 else 0

        print(f"\nConversion complete!")
        print(f"  Input size:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
        print(f"  Index size:  {idx_size:,} bytes ({idx_size / 1024 / 1024:.2f} MB)")
        print(f"  Data size:   {data_size:,} bytes ({data_size / 1024 / 1024:.2f} MB)")
        print(f"  Total size:  {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        print(f"  Compression: {compression_ratio:.2f}x smaller")

    def _create_schema(self, conn: sqlite3.Connection):
        """Create database schema"""
        conn.execute('''
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE bodies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE intervals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                body_id INTEGER NOT NULL,
                jd_start REAL NOT NULL,
                jd_end REAL NOT NULL,
                data_offset INTEGER NOT NULL,
                data_size INTEGER NOT NULL,
                FOREIGN KEY (body_id) REFERENCES bodies(id)
            )
        ''')

    def _store_metadata(self, conn: sqlite3.Connection, metadata: Dict[str, str]):
        """Store metadata"""
        for key, value in metadata.items():
            conn.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', (key, value))

    def _generate_intervals(self, start_jd: float, end_jd: float, interval_days: float) -> List:
        """Generate intervals"""
        intervals = []
        current = start_jd

        while current < end_jd:
            interval_end = min(current + interval_days, end_jd)
            intervals.append((current, interval_end))
            current = interval_end

        return intervals

    def _extract_coefficients(self, body_id: int, intervals: List) -> List[Dict]:
        """Extract Chebyshev coefficients"""
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

            positions = np.array(positions) / 149597870.7

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
    parser = argparse.ArgumentParser(description='Convert SPICE BSP to Hybrid format')
    parser.add_argument('input', help='Input SPICE BSP file')
    parser.add_argument('output', help='Output base name (creates .hidx + .heph)')
    parser.add_argument('--bodies', help='Comma-separated body IDs', default=None)
    parser.add_argument('--interval', type=float, help='Interval size in days (default: 32)', default=32.0)

    args = parser.parse_args()

    body_ids = None
    if args.bodies:
        body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    converter = SPICEtoHybrid(args.input, args.output, body_ids)
    converter.convert(interval_days=args.interval)


if __name__ == '__main__':
    main()
