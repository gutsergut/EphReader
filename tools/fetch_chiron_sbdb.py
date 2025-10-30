#!/usr/bin/env python3
"""
Fetch Chiron orbital elements from JPL Small Body Database Browser (SBDB).

This is an alternative to Lowell Observatory's astorb.dat, which is currently unavailable.
SBDB provides detailed orbital elements and physical properties via a JSON API.

Author: AI Assistant
Date: 2025
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime


def fetch_chiron_sbdb():
    """
    Fetch Chiron orbital elements from JPL SBDB API.

    API Documentation:
    https://ssd-api.jpl.nasa.gov/doc/sbdb.html

    Returns:
        dict with orbital elements and physical properties
    """
    print("=" * 70)
    print("JPL Small Body Database Browser - Chiron Fetcher")
    print("=" * 70)
    print()

    # SBDB API endpoint
    # Chiron designation: 2060 Chiron (primary)
    # Also known as: 95 P/Chiron (comet designation)
    url = "https://ssd-api.jpl.nasa.gov/sbdb.api"
    params = {
        'sstr': '2060',  # Chiron's number
        'cov': 'mat',    # Include covariance matrix
        'phys-par': '1', # Include physical parameters
        'full-prec': '1' # Full precision for orbital elements
    }

    print(f"Querying JPL SBDB API for Chiron (2060)...")
    print(f"  URL: {url}")
    print(f"  Parameters: {params}")
    print()

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        raw_data = response.json()

        print(f"✓ Received data from SBDB")
        print()

        # Parse orbital elements
        orbit = raw_data.get('orbit', {})
        elements = orbit.get('elements', [])

        # Physical parameters
        phys = raw_data.get('phys_par', [])

        # Object information
        obj_info = raw_data.get('object', {})

        # Build structured data
        data = {
            'metadata': {
                'source': 'JPL Small Body Database Browser',
                'query_date': datetime.now().isoformat(),
                'body_id': 2060,
                'body_name': obj_info.get('fullname', 'Chiron'),
                'des': obj_info.get('des', '2060 Chiron'),
                'spkid': obj_info.get('spkid'),  # NAIF ID
                'kind': obj_info.get('kind'),    # 'an' = asteroid, 'cn' = comet
                'orbit_class': obj_info.get('orbit_class', {}).get('name'),
                'neo': obj_info.get('neo', False),  # Near-Earth Object?
                'pha': obj_info.get('pha', False),  # Potentially Hazardous Asteroid?
            },
            'orbital_elements': {},
            'physical_parameters': {}
        }

        # Extract orbital elements (from 'elements' list)
        # Format: [value, sigma, label, units]
        element_map = {
            'e': 'eccentricity',
            'a': 'semimajor_axis',
            'q': 'perihelion_distance',
            'i': 'inclination',
            'om': 'longitude_ascending_node',  # Ω (Omega)
            'w': 'argument_perihelion',        # ω (omega)
            'ma': 'mean_anomaly',
            'tp': 'time_perihelion',
            'per': 'orbital_period',
            'n': 'mean_motion',
            'ad': 'aphelion_distance'
        }

        for elem in elements:
            name = elem.get('name')
            if name in element_map:
                data['orbital_elements'][element_map[name]] = {
                    'value': elem.get('value'),
                    'sigma': elem.get('sigma'),
                    'units': elem.get('units'),
                    'label': elem.get('label')
                }

        # Add epoch information
        epoch_data = orbit.get('epoch', {})
        data['orbital_elements']['epoch'] = {
            'jd': epoch_data,
            'label': orbit.get('epoch_label', '')
        }

        # Extract covariance matrix if available
        if 'covariance' in orbit:
            data['covariance_matrix'] = orbit['covariance']

        # Extract physical parameters
        for param in phys:
            name = param.get('name')
            if name:
                data['physical_parameters'][name] = {
                    'value': param.get('value'),
                    'sigma': param.get('sigma'),
                    'units': param.get('units'),
                    'title': param.get('title'),
                    'ref': param.get('ref')  # Reference/source
                }

        # Print summary
        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"Object: {data['metadata']['body_name']}")
        print(f"NAIF ID: {data['metadata']['spkid']}")
        print(f"Class: {data['metadata']['orbit_class']}")
        print()

        if 'semimajor_axis' in data['orbital_elements']:
            a = data['orbital_elements']['semimajor_axis']
            print(f"Semi-major axis: {a['value']} {a['units']}")

        if 'eccentricity' in data['orbital_elements']:
            e = data['orbital_elements']['eccentricity']
            print(f"Eccentricity: {e['value']}")

        if 'inclination' in data['orbital_elements']:
            i = data['orbital_elements']['inclination']
            print(f"Inclination: {i['value']}°")

        if 'orbital_period' in data['orbital_elements']:
            per = data['orbital_elements']['orbital_period']
            print(f"Orbital period: {per['value']} {per['units']}")

        print()
        print(f"Physical parameters available: {len(data['physical_parameters'])}")
        for key, val in data['physical_parameters'].items():
            print(f"  - {val.get('title', key)}: {val['value']} {val.get('units', '')}")

        print()

        return data

    except requests.exceptions.RequestException as e:
        print(f"ERROR querying SBDB: {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"ERROR parsing SBDB response: missing key {e}")
        sys.exit(1)


def save_json(data, filepath):
    """Save data to JSON file with pretty formatting."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    size_kb = filepath.stat().st_size / 1024
    print(f"✓ Saved to: {filepath}")
    print(f"  Size: {size_kb:.1f} KB")


def main():
    # Fetch Chiron data from SBDB
    data = fetch_chiron_sbdb()

    # Save to JSON
    output_path = "data/chiron/chiron_elements_sbdb.json"
    save_json(data, output_path)

    print()
    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Compare JPL Horizons vectors with Swiss Ephemeris")
    print("  2. Verify orbital elements match vector data")
    print("  3. Create unified Chiron .eph file")
    print()


if __name__ == '__main__':
    main()
