#!/usr/bin/env python3
"""
Parse Chiron orbital elements from MPCORB.DAT file.

MPCORB.DAT format documentation:
https://minorplanetcenter.net/iau/info/MPOrbitFormat.html
"""

import re
import json
from datetime import datetime

def parse_mpcorb_line(line: str) -> dict:
    """
    Parse one line from MPCORB.DAT according to MPC format.

    Format (columns):
    1-7:    Number (packed format)
    8-20:   Provisional designation or name
    21-25:  H (absolute magnitude)
    26-30:  G (slope parameter)
    31-35:  Epoch (packed format YYYYMMDD)
    36-45:  M (mean anomaly at epoch, degrees)
    46-55:  Peri (argument of perihelion, degrees)
    56-65:  Node (longitude of ascending node, degrees)
    66-75:  i (inclination, degrees)
    76-85:  e (eccentricity)
    86-95:  n (mean daily motion, degrees/day)
    96-106: a (semi-major axis, AU)
    """

    # Extract fields based on column positions (fixed for actual MPCORB format)
    number = line[0:7].strip()
    H = line[8:13].strip()
    G = line[14:19].strip()
    epoch = line[20:25].strip()
    M = line[26:35].strip()
    Peri = line[37:46].strip()
    Node = line[48:57].strip()
    i = line[59:68].strip()
    e = line[70:79].strip()
    n = line[80:91].strip()
    a = line[92:103].strip()

    # Uncertainties and observation info
    U = line[105:106].strip()
    reference = line[107:116].strip()
    num_obs = line[117:122].strip()
    num_opps = line[123:126].strip()
    arc = line[127:136].strip()
    rms = line[137:141].strip()

    # Perturbers and computer
    perturbers = line[142:149].strip()
    computer = line[150:160].strip()
    flags = line[161:165].strip()

    # Readable name
    readable_name = line[166:194].strip()

    # Last observation date
    last_obs = line[195:203].strip()    # Decode packed epoch (K25BL format)
    # K = 2020s, 25 = 2025, BL = Oct 27
    def decode_packed_date(packed: str) -> tuple:
        """Decode MPC packed date format."""
        if len(packed) < 5:
            return None, None

        # First char: century/decade
        century_map = {
            'I': 1800, 'J': 1900, 'K': 2000, 'L': 2100
        }
        century = century_map.get(packed[0], 2000)

        # Next 2 digits: year within century
        year_offset = int(packed[1:3])
        year = century + year_offset

        # Month (A=10, B=11, C=12, or digit)
        month_char = packed[3]
        if month_char.isdigit():
            month = int(month_char)
        else:
            month = ord(month_char) - ord('A') + 10

        # Day (A=10, B=11, ..., V=31, or digit)
        day_char = packed[4]
        if day_char.isdigit():
            day = int(day_char)
        else:
            day = ord(day_char) - ord('A') + 10

        return year, month, day

    year, month, day = decode_packed_date(epoch)

    # Convert epoch to JD (approximate)
    if year and month and day:
        # Simple JD calculation
        a = (14 - month) // 12
        y = year + 4800 - a
        m = month + 12 * a - 3
        jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        epoch_jd = jdn + 0.5
        epoch_cal = f"{year:04d}-{month:02d}-{day:02d}"
    else:
        epoch_jd = None
        epoch_cal = None

    return {
        'number': number,
        'readable_name': readable_name,
        'epoch': epoch,
        'epoch_jd': epoch_jd,
        'epoch_cal': epoch_cal,
        'elements': {
            'H': float(H) if H else None,
            'G': float(G) if G else None,
            'e': float(e) if e else None,
            'a': float(a) if a else None,
            'i': float(i) if i else None,
            'om': float(Node) if Node else None,
            'w': float(Peri) if Peri else None,
            'ma': float(M) if M else None,
            'n': float(n) if n else None
        },
        'uncertainty': U,
        'observations': {
            'num_obs': int(num_obs) if num_obs else None,
            'num_opps': int(num_opps) if num_opps else None,
            'arc': arc,
            'rms': float(rms) if rms else None
        },
        'reference': reference,
        'perturbers': perturbers,
        'computer': computer,
        'flags': flags,
        'last_obs': last_obs,
        'source': 'Minor Planet Center MPCORB.DAT'
    }


def find_chiron(mpcorb_file: str) -> dict:
    """Find and parse Chiron (2060) from MPCORB.DAT."""

    print(f"Searching for Chiron in {mpcorb_file}...")

    with open(mpcorb_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # Look for 02060 at the beginning (packed number)
            if line.startswith('02060'):
                print(f"✓ Found Chiron at line {line_num}")
                print()
                print("Raw line:")
                print(line)
                print()

                elements = parse_mpcorb_line(line)

                # Calculate period from mean motion
                if elements['elements']['n']:
                    period_days = 360.0 / elements['elements']['n']
                    period_years = period_days / 365.25
                    elements['elements']['per'] = period_years

                # Calculate perihelion and aphelion
                if elements['elements']['a'] and elements['elements']['e']:
                    a = elements['elements']['a']
                    e = elements['elements']['e']
                    elements['elements']['q'] = a * (1 - e)
                    elements['elements']['Q'] = a * (1 + e)

                return elements

    print("✗ Chiron not found in file")
    return None


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parse_mpcorb_chiron.py <MPCORB.DAT> [output.json]")
        sys.exit(1)

    mpcorb_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    elements = find_chiron(mpcorb_file)

    if not elements:
        sys.exit(1)

    print("=" * 80)
    print("CHIRON ORBITAL ELEMENTS (MPC)")
    print("=" * 80)
    print(f"Number:           {elements['number']}")
    print(f"Name:             {elements['readable_name']}")
    print(f"Epoch:            JD {elements['epoch_jd']} ({elements['epoch_cal']})")
    print()
    print("Elements:")
    for key, val in elements['elements'].items():
        if val is not None:
            print(f"  {key:6s} = {val}")
    print()
    print("Observations:")
    print(f"  Number:         {elements['observations']['num_obs']}")
    print(f"  Oppositions:    {elements['observations']['num_opps']}")
    print(f"  Arc:            {elements['observations']['arc']}")
    print(f"  RMS:            {elements['observations']['rms']}")
    print(f"  Last obs:       {elements['last_obs']}")
    print()
    print(f"Uncertainty:      {elements['uncertainty']}")
    print(f"Reference:        {elements['reference']}")
    print(f"Computer:         {elements['computer']}")
    print()

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(elements, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to: {output_file}")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
