#!/usr/bin/env python3
"""
Fetch orbital elements from JPL Small-Body Database (SBDB)
https://ssd-api.jpl.nasa.gov/doc/sbdb.html
"""

import requests
import json
import sys
from datetime import datetime

def fetch_sbdb_elements(designation: str, output_file: str = None):
    """
    Fetch orbital elements from JPL SBDB API

    Args:
        designation: Object designation (e.g., "2060" for Chiron)
        output_file: Optional output JSON file path
    """

    # SBDB API endpoint
    url = "https://ssd-api.jpl.nasa.gov/sbdb.api"

    # Request parameters
    params = {
        'sstr': designation,      # Object designation
        'full-prec': 'true',      # Full precision output
        'phys-par': 'true',       # Include physical parameters
        'close-appr': 'false',    # No close approach data needed
        'alt-orbits': 'false'     # No alternate orbit solutions
    }

    print(f"Fetching SBDB data for object {designation}...")
    print(f"URL: {url}")
    print(f"Parameters: {params}")
    print()

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()

        # Check for errors
        if 'message' in data:
            print(f"ERROR: {data['message']}")
            return None

        # Extract object info
        obj = data.get('object', {})
        orbit = data.get('orbit', {})
        phys_par = data.get('phys_par', {})

        print("=" * 80)
        print("OBJECT INFORMATION")
        print("=" * 80)
        print(f"Designation:    {obj.get('des', 'N/A')}")
        print(f"Name:           {obj.get('fullname', 'N/A')}")
        print(f"Object Type:    {obj.get('kind', 'N/A')}")
        print(f"Orbit ID:       {orbit.get('orbit_id', 'N/A')}")
        print(f"Epoch (JD):     {orbit.get('epoch', 'N/A')}")
        print()

        print("=" * 80)
        print("ORBITAL ELEMENTS")
        print("=" * 80)
        print(f"Eccentricity (e):           {orbit.get('e', 'N/A')}")
        print(f"Semi-major axis (a):        {orbit.get('a', 'N/A')} AU")
        print(f"Perihelion dist (q):        {orbit.get('q', 'N/A')} AU")
        print(f"Aphelion dist (Q):          {orbit.get('ad', 'N/A')} AU")
        print(f"Inclination (i):            {orbit.get('i', 'N/A')} deg")
        print(f"Long. asc. node (Ω):        {orbit.get('om', 'N/A')} deg")
        print(f"Arg. perihelion (ω):        {orbit.get('w', 'N/A')} deg")
        print(f"Mean anomaly (M):           {orbit.get('ma', 'N/A')} deg")
        print(f"Mean motion (n):            {orbit.get('n', 'N/A')} deg/day")
        print(f"Orbital period:             {orbit.get('per', 'N/A')} years")
        print()

        print("=" * 80)
        print("PHYSICAL PARAMETERS")
        print("=" * 80)
        if phys_par:
            print(f"Absolute mag (H):           {phys_par.get('H', 'N/A')}")
            print(f"Diameter:                   {phys_par.get('diameter', 'N/A')} km")
            print(f"Albedo:                     {phys_par.get('albedo', 'N/A')}")
            print(f"Rotation period:            {phys_par.get('rot_per', 'N/A')} hr")
        else:
            print("No physical parameters available")
        print()

        # Save to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Data saved to: {output_file}")
            print()

        # Create simplified orbital elements dictionary
        elements = {
            'designation': obj.get('des', ''),
            'name': obj.get('fullname', ''),
            'orbit_id': orbit.get('orbit_id', ''),
            'epoch_jd': float(orbit.get('epoch', 0)),
            'epoch_cal': orbit.get('epoch_cal', ''),
            'elements': {
                'e': float(orbit.get('e', 0)),          # Eccentricity
                'a': float(orbit.get('a', 0)),          # Semi-major axis (AU)
                'q': float(orbit.get('q', 0)),          # Perihelion distance (AU)
                'i': float(orbit.get('i', 0)),          # Inclination (deg)
                'om': float(orbit.get('om', 0)),        # Long. of ascending node (deg)
                'w': float(orbit.get('w', 0)),          # Argument of perihelion (deg)
                'ma': float(orbit.get('ma', 0)),        # Mean anomaly at epoch (deg)
                'n': float(orbit.get('n', 0)),          # Mean motion (deg/day)
                'per': float(orbit.get('per', 0))       # Period (years)
            },
            'uncertainty': {
                'e': orbit.get('sigma_e'),
                'a': orbit.get('sigma_a'),
                'q': orbit.get('sigma_q'),
                'i': orbit.get('sigma_i'),
                'om': orbit.get('sigma_om'),
                'w': orbit.get('sigma_w'),
                'ma': orbit.get('sigma_ma')
            },
            'data_arc': orbit.get('data_arc', ''),
            'n_obs': orbit.get('n_obs_used', 0),
            'condition_code': orbit.get('condition_code', ''),
            'fetched_at': datetime.utcnow().isoformat() + 'Z'
        }

        print("=" * 80)
        print("ELEMENTS READY FOR INTEGRATION")
        print("=" * 80)
        print(f"Epoch:        JD {elements['epoch_jd']} ({elements['epoch_cal']})")
        print(f"Elements:     {len(elements['elements'])} parameters")
        print(f"Data arc:     {elements['data_arc']}")
        print(f"Observations: {elements['n_obs']}")
        print(f"Orbit ID:     {elements['orbit_id']}")
        print()

        return elements

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch data: {e}")
        return None
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: Failed to parse response: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_sbdb_elements.py <designation> [output.json]")
        print()
        print("Examples:")
        print("  python fetch_sbdb_elements.py 2060")
        print("  python fetch_sbdb_elements.py 2060 chiron_sbdb.json")
        print("  python fetch_sbdb_elements.py 5145  # Pholus")
        sys.exit(1)

    designation = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    elements = fetch_sbdb_elements(designation, output_file)

    if elements:
        print("✓ SUCCESS: Orbital elements fetched successfully")
        return 0
    else:
        print("✗ FAILED: Could not fetch orbital elements")
        return 1


if __name__ == '__main__':
    sys.exit(main())
