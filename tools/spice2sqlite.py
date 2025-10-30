#!/usr/bin/env python3
"""
Convert SPICE BSP to SQLite database optimized for PHP

Advantages:
- Native PHP PDO support (no binary parsing)
- Indexed queries (faster than binary search for random access)
- Compressed BLOBs for coefficients
- SQL queries instead of manual offset calculations
- Easy to inspect/debug with sqlite3 command

Schema:
    metadata (key TEXT, value TEXT)
    bodies (id INTEGER, name TEXT, PRIMARY KEY)
    intervals (id INTEGER, body_id INTEGER, jd_start REAL, jd_end REAL,
               coeffs_x BLOB, coeffs_y BLOB, coeffs_z BLOB, PRIMARY KEY)

Usage:
    python spice2sqlite.py input.bsp output.db [--bodies 1,2,3,399,301]
"""

import sys
import struct
import argparse
import sqlite3
import zlib
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
    0: "SSB", 1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
    5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune", 9: "Pluto",
    10: "Sun", 199: "Mercury", 299: "Venus", 399: "Earth", 499: "Mars",
    599: "Jupiter", 699: "Saturn", 799: "Uranus", 899: "Neptune",
    999: "Pluto", 301: "Moon",
}


class SPICEtoSQLite:
    """Convert SPICE BSP to SQLite database"""

    def __init__(self, input_path: str, output_path: str, body_ids: List[int] = None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.body_ids = body_ids or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input SPICE file not found: {input_path}")

    def convert(self, interval_days: float = 32.0, compress: bool = True):
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

        # Create SQLite database
        print(f"Creating SQLite database: {self.output_path}")
        if self.output_path.exists():
            self.output_path.unlink()

        conn = sqlite3.connect(str(self.output_path))
        self._create_schema(conn)

        # Store metadata
        self._store_metadata(conn, {
            'version': '1.0',
            'source': str(self.input_path.name),
            'start_jd': str(start_jd),
            'end_jd': str(end_jd),
            'interval_days': str(interval_days),
            'num_intervals': str(num_intervals),
            'num_bodies': str(len(self.body_ids)),
            'chebyshev_degree': '7',
            'compressed': str(int(compress))
        })

        # Process bodies
        print(f"Processing {len(self.body_ids)} bodies...")
        for body_id in self.body_ids:
            body_name = BODY_NAMES.get(body_id, f"Body{body_id}")
            print(f"  {body_name} (ID {body_id})...", end="", flush=True)

            try:
                # Store body
                conn.execute('INSERT INTO bodies (id, name) VALUES (?, ?)',
                           (body_id, body_name))

                # Extract and store coefficients
                coeffs_list = self._extract_coefficients(body_id, intervals)
                self._store_intervals(conn, body_id, intervals, coeffs_list, compress)

                print(f" OK ({len(coeffs_list)} intervals)")
            except Exception as e:
                print(f" SKIP ({e})")
                continue

        # Create indexes
        print("Creating indexes...")
        conn.execute('CREATE INDEX idx_intervals_body ON intervals(body_id)')
        conn.execute('CREATE INDEX idx_intervals_jd ON intervals(jd_start, jd_end)')

        conn.commit()
        conn.close()
        spice.unload(str(self.input_path))

        # Statistics
        output_size = self.output_path.stat().st_size
        input_size = self.input_path.stat().st_size
        compression_ratio = input_size / output_size if output_size > 0 else 0

        print(f"\nConversion complete!")
        print(f"  Input size:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
        print(f"  Output size: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
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
                coeffs_x BLOB NOT NULL,
                coeffs_y BLOB NOT NULL,
                coeffs_z BLOB NOT NULL,
                FOREIGN KEY (body_id) REFERENCES bodies(id)
            )
        ''')

    def _store_metadata(self, conn: sqlite3.Connection, metadata: Dict[str, str]):
        """Store metadata key-value pairs"""
        for key, value in metadata.items():
            conn.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', (key, value))

    def _store_intervals(self, conn: sqlite3.Connection, body_id: int,
                        intervals: List[Tuple[float, float]],
                        coeffs_list: List[Dict], compress: bool):
        """Store intervals with coefficients"""
        for (jd_start, jd_end), coeffs in zip(intervals, coeffs_list):
            # Pack coefficients as doubles
            x_bytes = struct.pack(f'{len(coeffs["x"])}d', *coeffs['x'])
            y_bytes = struct.pack(f'{len(coeffs["y"])}d', *coeffs['y'])
            z_bytes = struct.pack(f'{len(coeffs["z"])}d', *coeffs['z'])

            # Optionally compress
            if compress:
                x_bytes = zlib.compress(x_bytes, level=6)
                y_bytes = zlib.compress(y_bytes, level=6)
                z_bytes = zlib.compress(z_bytes, level=6)

            conn.execute('''
                INSERT INTO intervals (body_id, jd_start, jd_end, coeffs_x, coeffs_y, coeffs_z)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (body_id, jd_start, jd_end, x_bytes, y_bytes, z_bytes))

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
                except Exception as e:
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
    parser = argparse.ArgumentParser(description='Convert SPICE BSP to SQLite database for PHP')
    parser.add_argument('input', help='Input SPICE BSP file')
    parser.add_argument('output', help='Output SQLite database file')
    parser.add_argument('--bodies', help='Comma-separated body IDs (default: 1-10)', default=None)
    parser.add_argument('--interval', type=float, help='Interval size in days (default: 32)', default=32.0)
    parser.add_argument('--no-compress', action='store_true', help='Disable BLOB compression')

    args = parser.parse_args()

    body_ids = None
    if args.bodies:
        body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    converter = SPICEtoSQLite(args.input, args.output, body_ids)
    converter.convert(interval_days=args.interval, compress=not args.no_compress)


if __name__ == '__main__':
    main()
