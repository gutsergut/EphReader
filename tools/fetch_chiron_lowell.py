#!/usr/bin/env python3
"""
Fetch Chiron orbital elements from Lowell Observatory.

This script downloads the astorb.dat database from Lowell Observatory
and extracts orbital elements for Chiron (2060).

Requirements:
    pip install requests

Usage:
    python tools/fetch_chiron_lowell.py
"""

import sys
import json
import gzip
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests package not installed!")
    print("Please run: pip install requests")
    sys.exit(1)


def download_astorb():
    """
    Download astorb.dat.gz from Lowell Observatory.

    Returns:
        Path: Path to downloaded file
    """
    url = "https://asteroid.lowell.edu/main/astorb/astorb.dat.gz"
    output_dir = Path("data/chiron")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "astorb.dat.gz"

    print("Downloading astorb.dat.gz from Lowell Observatory...")
    print(f"  URL: {url}")
    print()

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        print(f"  File size: {total_size / 1024 / 1024:.1f} MB")

        downloaded = 0
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

                # Progress indicator
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    sys.stdout.write(f"\r  Progress: {percent:.1f}%")
                    sys.stdout.flush()

        print(f"\n✓ Downloaded to: {output_file}")
        print(f"  Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
        return output_file

    except Exception as e:
        print(f"\nERROR downloading astorb.dat: {e}")
        sys.exit(1)


def parse_astorb_line(line):
    """
    Parse a line from astorb.dat.

    Format documentation:
    https://asteroid.lowell.edu/main/astorb/astorbformat.html

    Args:
        line: String line from astorb.dat

    Returns:
        dict: Orbital elements or None if parse error
    """
    try:
        # Fixed-width format
        data = {
            'number': line[0:7].strip(),
            'name': line[7:25].strip(),
            'computer': line[25:27].strip(),
            'H': float(line[27:32].strip()) if line[27:32].strip() else None,  # Absolute magnitude
            'G': float(line[32:37].strip()) if line[32:37].strip() else None,  # Slope parameter
            'arc': line[37:42].strip(),
            'num_obs': int(line[42:47].strip()) if line[42:47].strip() else None,
            'epoch': line[47:53].strip(),  # Packed date
            'a': float(line[53:63].strip()) if line[53:63].strip() else None,   # Semi-major axis (AU)
            'e': float(line[63:73].strip()) if line[63:73].strip() else None,   # Eccentricity
            'i': float(line[73:82].strip()) if line[73:82].strip() else None,   # Inclination (deg)
            'Om': float(line[82:91].strip()) if line[82:91].strip() else None,  # Longitude of ascending node (deg)
            'w': float(line[91:100].strip()) if line[91:100].strip() else None, # Argument of perihelion (deg)
            'M': float(line[100:110].strip()) if line[100:110].strip() else None, # Mean anomaly (deg)
            'n': float(line[110:120].strip()) if line[110:120].strip() else None, # Mean daily motion (deg/day)
        }
        return data
    except Exception as e:
        print(f"Warning: Failed to parse line: {e}")
        return None


def unpack_epoch(packed_date):
    """
    Unpack epoch from astorb.dat format (KYYMD).

    Examples:
        K2479 = 2024-07-09

    Args:
        packed_date: String like 'K2479'

    Returns:
        str: ISO date string
    """
    if not packed_date or len(packed_date) != 5:
        return None

    try:
        # Century code (I=1800, J=1900, K=2000, L=2100)
        century_codes = {'I': 1800, 'J': 1900, 'K': 2000, 'L': 2100}
        century = century_codes.get(packed_date[0])
        if not century:
            return None

        # Year (2 digits)
        year = century + int(packed_date[1:3])

        # Month (0=Jan, 1=Feb, ..., 9=Oct, A=Nov, B=Dec)
        month_code = packed_date[3]
        if month_code.isdigit():
            month = int(month_code) + 1
        elif month_code == 'A':
            month = 11
        elif month_code == 'B':
            month = 12
        else:
            return None

        # Day (0-9 for 0-9, A-V for 10-31)
        day_code = packed_date[4]
        if day_code.isdigit():
            day = int(day_code)
        else:
            day = ord(day_code) - ord('A') + 10

        return f"{year:04d}-{month:02d}-{day:02d}"

    except Exception:
        return None


def extract_chiron(astorb_file):
    """
    Extract Chiron (2060) orbital elements from astorb.dat.gz.

    Args:
        astorb_file: Path to astorb.dat.gz

    Returns:
        dict: Chiron orbital elements
    """
    print("\nSearching for Chiron (2060) in astorb.dat...")

    try:
        with gzip.open(astorb_file, 'rt', encoding='latin-1') as f:
            for line_num, line in enumerate(f, 1):
                if line_num % 100000 == 0:
                    sys.stdout.write(f"\r  Processed {line_num} asteroids...")
                    sys.stdout.flush()

                # Check if this is Chiron (number = 2060)
                number = line[0:7].strip()
                if number == '2060':
                    print(f"\n✓ Found Chiron at line {line_num}!")

                    data = parse_astorb_line(line)
                    if data:
                        # Add metadata
                        data['source'] = 'Lowell Observatory astorb.dat'
                        data['query_date'] = datetime.now().isoformat()
                        data['naif_id'] = 2002060
                        data['epoch_iso'] = unpack_epoch(data['epoch'])

                        # Compute orbital period (years)
                        if data['a']:
                            data['period_years'] = data['a'] ** 1.5  # Kepler's 3rd law

                        # Compute perihelion/aphelion
                        if data['a'] and data['e']:
                            data['q'] = data['a'] * (1 - data['e'])  # Perihelion distance (AU)
                            data['Q'] = data['a'] * (1 + data['e'])  # Aphelion distance (AU)

                        return data

        print("\n✗ Chiron (2060) not found in astorb.dat!")
        return None

    except Exception as e:
        print(f"\nERROR reading astorb.dat: {e}")
        sys.exit(1)


def save_json(data, filepath):
    """Save data to JSON file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Saved to: {filepath}")
    print(f"  Size: {filepath.stat().st_size / 1024:.1f} KB")


def print_orbital_elements(data):
    """Pretty-print orbital elements."""
    print("\n" + "=" * 70)
    print("CHIRON ORBITAL ELEMENTS (Lowell Observatory)")
    print("=" * 70)
    print(f"Number:        {data['number']}")
    print(f"Name:          {data['name']}")
    print(f"NAIF ID:       {data['naif_id']}")
    print()
    print(f"Epoch:         {data['epoch']} ({data['epoch_iso']})")
    print(f"H (abs mag):   {data['H']}")
    print(f"G (slope):     {data['G']}")
    print(f"Arc:           {data['arc']}")
    print(f"Observations:  {data['num_obs']}")
    print()
    print("ORBITAL ELEMENTS:")
    print(f"  a (semi-major axis):        {data['a']:.6f} AU")
    print(f"  e (eccentricity):           {data['e']:.6f}")
    print(f"  i (inclination):            {data['i']:.4f}°")
    print(f"  Ω (ascending node):         {data['Om']:.4f}°")
    print(f"  ω (arg of perihelion):      {data['w']:.4f}°")
    print(f"  M (mean anomaly):           {data['M']:.4f}°")
    print(f"  n (mean daily motion):      {data['n']:.8f}°/day")
    print()
    print("COMPUTED:")
    print(f"  Period:                     {data['period_years']:.2f} years")
    print(f"  q (perihelion):             {data['q']:.3f} AU (near Saturn)")
    print(f"  Q (aphelion):               {data['Q']:.3f} AU (near Uranus)")
    print()


def main():
    """Main execution."""
    print("=" * 70)
    print("Lowell Observatory Chiron Orbital Elements Fetcher")
    print("=" * 70)
    print()

    # Download astorb.dat.gz
    astorb_file = download_astorb()
    print()

    # Extract Chiron
    chiron_data = extract_chiron(astorb_file)

    if chiron_data:
        # Save to JSON
        output_dir = Path("data/chiron")
        save_json(chiron_data, output_dir / "chiron_elements_lowell.json")

        # Pretty print
        print_orbital_elements(chiron_data)

        print("=" * 70)
        print("✓ SUCCESS")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Compare with JPL Horizons data")
        print("  2. Use elements for numerical integration")
        print("  3. Validate against Swiss Ephemeris")
    else:
        print("FAILED to extract Chiron data!")
        sys.exit(1)


if __name__ == '__main__':
    main()
