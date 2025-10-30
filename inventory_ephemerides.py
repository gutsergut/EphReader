#!/usr/bin/env python3
"""
Complete inventory of SPICE ephemeris files:
- Available bodies
- Coverage periods
- File size and body count

Simple and reliable - works with jplephem's actual API.
"""

import sys
from pathlib import Path
from typing import Dict, List
import argparse

try:
    from jplephem.spk import SPK
except ImportError:
    print("ERROR: jplephem not installed. Run: pip install jplephem", file=sys.stderr)
    sys.exit(1)


BODY_NAMES = {
    # Planets
    1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
    5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune", 9: "Pluto",
    10: "Sun", 301: "Moon", 399: "Earth",

    # Barycenters
    199: "Mercury Barycenter", 299: "Venus Barycenter",

    # Main belt asteroids
    2000001: "1 Ceres", 2000002: "2 Pallas", 2000003: "3 Juno", 2000004: "4 Vesta",
    2000007: "7 Iris", 2000010: "10 Hygiea", 2000015: "15 Eunomia",
    2000016: "16 Psyche", 2000324: "324 Bamberga",

    # TNOs/Centaurs/Dwarf planets
    2002060: "2060 Chiron", 2005145: "5145 Pholus",
    2090377: "90377 Sedna",
    2136108: "136108 Haumea",
    2136199: "136199 Eris",
    2136472: "136472 Makemake",

    # SSB
    0: "Solar System Barycenter",
    1000000001: "Pluto-Charon Barycenter",
}


def analyze_file(filepath: str):
    """Analyze a single SPICE file"""

    path = Path(filepath)
    print(f"\n{'='*100}")
    print(f"File: {path.name}")
    print(f"Path: {filepath}")
    print(f"Size: {path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"{'='*100}\n")

    kernel = SPK.open(filepath)

    print(f"{'ID':<6} {'Body Name':<35} {'Coverage':<35} {'Years':<8}")
    print(f"{'-'*6} {'-'*35} {'-'*35} {'-'*8}")

    results = []

    for seg in kernel.segments:
        target_id = seg.target
        target_name = BODY_NAMES.get(target_id, f"Body {target_id}")

        # Coverage
        duration_days = seg.end_jd - seg.start_jd
        coverage_years = duration_days / 365.25

        # Get time range
        start_year = 2000 + (seg.start_jd - 2451545.0) / 365.25
        end_year = 2000 + (seg.end_jd - 2451545.0) / 365.25
        coverage_str = f"{start_year:.0f} to {end_year:.0f} AD"

        print(f"{target_id:<6} {target_name:<35} {coverage_str:<35} {coverage_years:.0f}")

        results.append({
            'target': target_id,
            'target_name': target_name,
            'center': seg.center,
            'coverage_years': coverage_years,
            'start_jd': seg.start_jd,
            'end_jd': seg.end_jd,
            'start_year': start_year,
            'end_year': end_year,
        })

    kernel.close()

    print(f"\nTotal bodies: {len(results)}")

    return results


def compare_files(files: List[str]):
    """Compare multiple files"""

    all_results = {}

    for filepath in files:
        if not Path(filepath).exists():
            print(f"⚠️  File not found: {filepath}")
            continue

        results = analyze_file(filepath)
        all_results[filepath] = results

    # Cross-file comparison
    if len(all_results) > 1:
        print(f"\n\n{'='*100}")
        print("CROSS-FILE COMPARISON")
        print(f"{'='*100}\n")

        # Collect all unique targets
        all_targets = set()
        for results in all_results.values():
            for r in results:
                all_targets.add(r['target'])

        # Header
        file_cols = [Path(f).stem[:20] for f in all_results.keys()]
        print(f"{'Body':<35} " + " | ".join(f"{col:<12}" for col in file_cols))
        print(f"{'-'*35} " + "-+-".join("-"*12 for _ in file_cols))

        for target_id in sorted(all_targets):
            target_name = BODY_NAMES.get(target_id, f"Body {target_id}")[:35]
            row = [target_name]

            for filepath, results in all_results.items():
                target_data = [r for r in results if r['target'] == target_id]
                if target_data:
                    val = "✓"
                else:
                    val = "—"
                row.append(f"{val:<12}")

            print(f"{row[0]:<35} " + " | ".join(row[1:]))

        # Summary
        print(f"\n\n{'='*100}")
        print("SUMMARY & RECOMMENDATIONS")
        print(f"{'='*100}\n")

        for filepath, results in all_results.items():
            fname = Path(filepath).name
            print(f"\n{fname}:")
            print(f"  Bodies: {len(results)}")

            # Group by category
            planets = [r for r in results if r['target'] in [1,2,3,4,5,6,7,8,9,10,301,399]]
            barycenters = [r for r in results if r['target'] in [199,299,0,1000000001]]
            asteroids = [r for r in results if 2000000 <= r['target'] < 3000000]
            tno_centaurs = [r for r in results if r['target'] > 2000000 and r['target'] not in [t['target'] for t in asteroids]]

            if planets:
                print(f"    Planets/Sun/Moon: {len(planets)}")
                planet_ids = ",".join(str(r['target']) for r in planets)
                print(f"      IDs: {planet_ids}")

            if barycenters:
                print(f"    Barycenters: {len(barycenters)}")
                barycenter_ids = ",".join(str(r['target']) for r in barycenters)
                print(f"      IDs: {barycenter_ids}")

            if asteroids:
                print(f"    Asteroids: {len(asteroids)}")
                asteroid_ids = ",".join(str(r['target']) for r in asteroids[:10])  # First 10
                if len(asteroids) > 10:
                    print(f"      IDs: {asteroid_ids},... ({len(asteroids)} total)")
                else:
                    print(f"      IDs: {asteroid_ids}")

            if tno_centaurs:
                print(f"    TNOs/Centaurs: {len(tno_centaurs)}")
                tno_ids = ",".join(str(r['target']) for r in tno_centaurs)
                print(f"      IDs: {tno_ids}")

            # Coverage
            if results:
                min_year = min(r['start_year'] for r in results)
                max_year = max(r['end_year'] for r in results)
                print(f"  Coverage: {min_year:.0f} to {max_year:.0f} AD ({max_year-min_year:.0f} years)")

        print()


def main():
    parser = argparse.ArgumentParser(
        description='Inventory of SPICE ephemeris bodies and coverage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file
  python inventory_ephemerides.py data/ephemerides/epm/2021/spice/epm2021.bsp

  # Compare multiple files
  python inventory_ephemerides.py \\
      data/ephemerides/jpl/de431/de431_part-1.bsp \\
      data/ephemerides/epm/2021/spice/epm2021.bsp \\
      --compare
        """
    )
    parser.add_argument('files', nargs='+', help='SPICE SPK files to analyze')
    parser.add_argument('--compare', action='store_true', help='Compare multiple files')

    args = parser.parse_args()

    if args.compare or len(args.files) > 1:
        compare_files(args.files)
    else:
        analyze_file(args.files[0])

    print("\n✅ Analysis complete!\n")


if __name__ == '__main__':
    main()
