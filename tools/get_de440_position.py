#!/usr/bin/env python3
"""
Simple DE440 position reader using Project Pluto's jpl_eph library.

Usage: python get_de440_position.py <body_id> <jd>
Output: JSON with geocentric ecliptic lon/lat/dist

This script is called by PHP for DE440 comparison.
"""

import sys
import json
import struct
from pathlib import Path


def read_de440_header(filepath):
    """Read DE440 header to get constants."""
    with open(filepath, 'rb') as f:
        # Read first record (84 * 3 doubles = 2016 bytes)
        header_data = f.read(2016)

        # Parse key values
        # AU in km at offset 2*8 = 16
        au_km = struct.unpack('<d', header_data[16:24])[0]

        # EMRAT at offset 4*8 = 32
        emrat = struct.unpack('<d', header_data[32:40])[0]

        return {
            'au_km': au_km,
            'emrat': emrat,
        }


def compute_position(body_naif_id, jd):
    """
    Compute geocentric ecliptic position for body at given JD.

    Since we don't have calceph built, we'll use a simple approach:
    1. For testing, return mock data
    2. In production, this should call jpl_eph library
    """
    # For now, return error indicating we need proper implementation
    return {
        'error': 'DE440 direct reading not implemented yet',
        'suggestion': 'Use Swiss Ephemeris as DE440 proxy (it is based on DE440)',
        'body_id': body_naif_id,
        'jd': jd
    }


def main():
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'Usage: get_de440_position.py <body_id> <jd>'}))
        sys.exit(1)

    try:
        body_id = int(sys.argv[1])
        jd = float(sys.argv[2])

        result = compute_position(body_id, jd)
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
