#!/usr/bin/env python3
"""
Fetch Chiron ephemeris data from JPL Horizons.

This script downloads Chiron (2060) position vectors from NASA JPL Horizons system
and saves them in a format compatible with our ephemeris tools.

Requirements:
    pip install astroquery numpy

Usage:
    python tools/fetch_chiron_horizons.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from astroquery.jplhorizons import Horizons
    import numpy as np
except ImportError as e:
    print("ERROR: Required packages not installed!")
    print("Please run: pip install astroquery numpy")
    print(f"Details: {e}")
    sys.exit(1)


def fetch_chiron_vectors(start_jd, stop_jd, step_days=16):
    """
    Fetch Chiron position vectors from JPL Horizons.

    Args:
        start_jd: Start Julian Date
        stop_jd: Stop Julian Date
        step_days: Step size in days

    Returns:
        dict: Vectors data with metadata
    """
    print(f"Fetching Chiron data from JPL Horizons...")
    print(f"  Start JD: {start_jd}")
    print(f"  Stop JD:  {stop_jd}")
    print(f"  Step:     {step_days} days")
    print()

    # Chiron = small body #2060
    # Location: @sun (heliocentric)
    # Generate epoch list (JPL Horizons doesn't support JD ranges for small bodies)
    import numpy as np
    all_epochs = np.arange(start_jd, stop_jd, step_days).tolist()

    # Split into chunks to avoid 414 URI Too Large error
    chunk_size = 100  # Max ~100 epochs per query
    num_chunks = (len(all_epochs) + chunk_size - 1) // chunk_size

    print(f"Total epochs: {len(all_epochs)}, splitting into {num_chunks} chunks...")
    print()

    all_vectors = []

    try:
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min(start_idx + chunk_size, len(all_epochs))
            epoch_chunk = all_epochs[start_idx:end_idx]

            print(f"Querying chunk {chunk_idx + 1}/{num_chunks} ({len(epoch_chunk)} epochs)...")

            obj = Horizons(
                id='2060',
                location='@sun',
                epochs=epoch_chunk,
                id_type='smallbody'
            )

            vectors = obj.vectors()
            all_vectors.extend(vectors)
            print(f"  ✓ Received {len(vectors)} points")

        print(f"\n✓ Total received: {len(all_vectors)} data points\n")
        vectors = all_vectors  # Replace with combined data

        # Extract data
        data = {
            'metadata': {
                'body_id': 2060,
                'body_name': 'Chiron',
                'naif_id': 2002060,
                'source': 'JPL Horizons',
                'query_date': datetime.now().isoformat(),
                'coordinate_system': 'Heliocentric J2000 Ecliptic',
                'units': 'AU, AU/day',
                'start_jd': float(start_jd),
                'stop_jd': float(stop_jd),
                'step_days': step_days,
                'num_points': len(vectors)
            },
            'epochs': [],
            'vectors': []
        }

        for row in vectors:
            data['epochs'].append(float(row['datetime_jd']))
            data['vectors'].append({
                'x': float(row['x']),
                'y': float(row['y']),
                'z': float(row['z']),
                'vx': float(row['vx']),
                'vy': float(row['vy']),
                'vz': float(row['vz'])
            })

        return data

    except Exception as e:
        print(f"ERROR querying Horizons: {e}")
        sys.exit(1)


def fetch_chiron_ephemeris(start_jd, stop_jd, step_days=1):
    """
    Fetch Chiron observer ephemeris (RA/Dec/distance) from JPL Horizons.

    Args:
        start_jd: Start Julian Date
        stop_jd: Stop Julian Date
        step_days: Step size in days

    Returns:
        dict: Ephemeris data with metadata
    """
    print(f"Fetching Chiron observer ephemeris from JPL Horizons...")
    print(f"  Start JD: {start_jd}")
    print(f"  Stop JD:  {stop_jd}")
    print(f"  Step:     {step_days} days")
    print()

    # Generate epoch list
    import numpy as np
    all_epochs = np.arange(start_jd, stop_jd, step_days).tolist()

    # Split into chunks to avoid 414 URI Too Large error
    chunk_size = 100
    num_chunks = (len(all_epochs) + chunk_size - 1) // chunk_size

    print(f"Total epochs: {len(all_epochs)}, splitting into {num_chunks} chunks...")
    print()

    all_eph = []

    try:
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min(start_idx + chunk_size, len(all_epochs))
            epoch_chunk = all_epochs[start_idx:end_idx]

            print(f"Querying chunk {chunk_idx + 1}/{num_chunks} ({len(epoch_chunk)} epochs)...")

            obj = Horizons(
                id='2060',
                location='500@399',
                epochs=epoch_chunk,
                id_type='smallbody'
            )

            eph_chunk = obj.ephemerides()
            all_eph.extend(eph_chunk)
            print(f"  ✓ Received {len(eph_chunk)} points")

        print(f"\n✓ Total received: {len(all_eph)} data points\n")
        eph = all_eph  # Replace with combined data

        data = {
            'metadata': {
                'body_id': 2060,
                'body_name': 'Chiron',
                'source': 'JPL Horizons',
                'query_date': datetime.now().isoformat(),
                'coordinate_system': 'Geocentric J2000 Equatorial',
                'observer': 'Earth geocenter',
                'start_jd': float(start_jd),
                'stop_jd': float(stop_jd),
                'step_days': step_days,
                'num_points': len(eph)
            },
            'epochs': [],
            'ephemeris': []
        }

        for row in eph:
            data['epochs'].append(float(row['datetime_jd']))
            data['ephemeris'].append({
                'RA': float(row['RA']),           # degrees
                'DEC': float(row['DEC']),         # degrees
                'delta': float(row['delta']),     # AU (distance from observer)
                'deldot': float(row['delta_rate']), # AU/day
                'V': float(row['V']),             # Visual magnitude
                'elongation': float(row['elong']),  # degrees
                'phase_angle': float(row['alpha'])  # degrees
            })

        return data

    except Exception as e:
        print(f"ERROR querying Horizons ephemeris: {e}")
        sys.exit(1)


def save_json(data, filepath):
    """Save data to JSON file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved to: {filepath}")
    print(f"  Size: {filepath.stat().st_size / 1024:.1f} KB")


def main():
    """Main execution."""
    print("=" * 70)
    print("JPL Horizons Chiron Data Fetcher")
    print("=" * 70)
    print()

    # Configuration
    output_dir = Path("data/chiron")

    # Time range: J2000 ± 50 years (conservative, Chiron is reliable 700-4650 CE)
    start_jd = 2451545.0 - (50 * 365.25)  # ~1950
    stop_jd = 2451545.0 + (50 * 365.25)   # ~2050

    # Fetch heliocentric vectors (16-day intervals for efficiency)
    print("TASK 1: Heliocentric Vectors")
    print("-" * 70)
    vectors_data = fetch_chiron_vectors(start_jd, stop_jd, step_days=16)
    save_json(vectors_data, output_dir / "chiron_vectors_jpl.json")
    print()

    # Fetch geocentric ephemeris (daily for astrology)
    print("TASK 2: Geocentric Ephemeris (sample: 10 years)")
    print("-" * 70)
    sample_start = 2451545.0  # J2000
    sample_stop = 2451545.0 + (10 * 365.25)  # +10 years
    eph_data = fetch_chiron_ephemeris(sample_start, sample_stop, step_days=1)
    save_json(eph_data, output_dir / "chiron_ephemeris_geocentric_jpl.json")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Heliocentric vectors: {vectors_data['metadata']['num_points']} points")
    print(f"  Coverage: {vectors_data['metadata']['start_jd']:.1f} - {vectors_data['metadata']['stop_jd']:.1f} JD")
    print(f"  (~{(stop_jd - start_jd) / 365.25:.0f} years)")
    print()
    print(f"✓ Geocentric ephemeris: {eph_data['metadata']['num_points']} points")
    print(f"  Coverage: {eph_data['metadata']['start_jd']:.1f} - {eph_data['metadata']['stop_jd']:.1f} JD")
    print(f"  (~{(sample_stop - sample_start) / 365.25:.0f} years)")
    print()
    print("Files saved to: data/chiron/")
    print()
    print("Next steps:")
    print("  1. Run: python tools/fetch_chiron_lowell.py")
    print("  2. Compare JPL vs Swiss Ephemeris accuracy")
    print("  3. Create unified Chiron .eph file")


if __name__ == '__main__':
    main()
