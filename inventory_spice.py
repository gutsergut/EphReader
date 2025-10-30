#!/usr/bin/env python3
"""
Comprehensive analysis of SPICE ephemeris files:
1. Available bodies and their coverage
2. Native intervals for each body
3. Polynomial degrees used
4. Optimal conversion parameters

Supports: JPL DE, EPM, asteroid files
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
    2000010: "10 Hygiea", 2000015: "15 Eunomia", 2000016: "16 Psyche",

    # Centaurs
    2002060: "2060 Chiron", 2005145: "5145 Pholus",
}


def analyze_file(filepath: str):
    """Analyze a single SPICE file"""

    print(f"\n{'='*90}")
    print(f"File: {Path(filepath).name}")
    print(f"Path: {filepath}")
    print(f"Size: {Path(filepath).stat().st_size / 1024 / 1024:.1f} MB")
    print(f"{'='*90}\n")

    kernel = SPK.open(filepath)

    print(f"{'Body':<30} {'Interval':<12} {'Degree':<8} {'Records':<10} {'Coverage (years)'}")
    print(f"{'-'*30} {'-'*12} {'-'*8} {'-'*10} {'-'*20}")

    results = []

    for seg in kernel.segments:
        target_name = BODY_NAMES.get(seg.target, f"Body {seg.target}")
        center_name = BODY_NAMES.get(seg.center, f"Center {seg.center}")

        # Initialize variables
        interval_days = None
        interval_str = "N/A"
        degree = None
        degree_str = "N/A"
        records = "N/A"

        # Get interval information from DAF array
        try:
            # Load segment data
            array = seg.load_array()

            # SPK Type 2 (Chebyshev) structure:
            # array[0] = initial epoch (TDB seconds)
            # array[1] = interval length (seconds)
            # array[2] = rsize (record size)
            # array[3] = n_records (number of records)

            if len(array) >= 4:
                interval_sec = array[1]
                rsize = int(array[2])
                n_records = int(array[3])

                interval_days = interval_sec / 86400.0
                interval_hours = interval_days * 24.0

                # Format interval
                if interval_days >= 1:
                    interval_str = f"{interval_days:.2f} days"
                else:
                    interval_str = f"{interval_hours:.1f} hours"

                # Calculate polynomial degree
                # rsize = (degree+1) * components + 2
                # components = 3 (pos only) or 6 (pos+vel)
                for comp in [6, 3]:
                    for d in range(1, 50):
                        if (d + 1) * comp + 2 == rsize:
                            degree = d
                            break
                    if degree:
                        break

                degree_str = str(degree) if degree else "?"
                records = n_records

        except (AttributeError, IndexError, ValueError) as e:
            pass        # Coverage
        duration_days = seg.end_jd - seg.start_jd
        coverage_years = duration_days / 365.25

        # Get time range
        start_year = 2000 + (seg.start_jd - 2451545.0) / 365.25
        end_year = 2000 + (seg.end_jd - 2451545.0) / 365.25
        coverage_str = f"{coverage_years:.0f}y ({start_year:.0f}-{end_year:.0f})"

        print(f"{target_name:<30} {interval_str:<12} {degree_str:<8} {str(records):<10} {coverage_str}")

        results.append({
            'target': seg.target,
            'target_name': target_name,
            'center': seg.center,
            'interval_days': interval_days,
            'degree': degree,
            'records': records if isinstance(records, int) else None,
            'coverage_years': coverage_years,
            'start_jd': seg.start_jd,
            'end_jd': seg.end_jd,
        })

    kernel.close()

    print()

    return results


def print_statistics(results: List[Dict], filename: str):
    """Print interval statistics"""

    intervals = [r['interval_days'] for r in results if r['interval_days'] is not None]

    if not intervals:
        return

    print(f"\nInterval Statistics for {filename}:")
    print(f"  Minimum: {min(intervals):.4f} days ({min(intervals)*24:.2f} hours)")
    print(f"  Maximum: {max(intervals):.4f} days ({max(intervals)*24:.2f} hours)")
    print(f"  Median:  {sorted(intervals)[len(intervals)//2]:.4f} days")

    # Unique intervals
    unique = sorted(set(intervals))
    print(f"  Unique intervals: {len(unique)}")
    for iv in unique:
        count = intervals.count(iv)
        print(f"    {iv:.4f} days ({iv*24:.1f}h): {count} bodies")

    print()


def compare_files(files: List[str]):
    """Compare multiple files"""

    all_results = {}

    for filepath in files:
        if not Path(filepath).exists():
            print(f"⚠️  File not found: {filepath}")
            continue

        results = analyze_file(filepath)
        print_statistics(results, Path(filepath).name)
        all_results[filepath] = results

    # Cross-file comparison
    if len(all_results) > 1:
        print(f"\n{'='*90}")
        print("CROSS-FILE COMPARISON: Body Availability")
        print(f"{'='*90}\n")

        # Collect all unique targets
        all_targets = set()
        for results in all_results.values():
            for r in results:
                all_targets.add(r['target'])

        # Header
        file_cols = [Path(f).stem[:15] for f in all_results.keys()]
        print(f"{'Body':<30} " + " | ".join(f"{col:<15}" for col in file_cols))
        print(f"{'-'*30} " + "-+-".join("-"*15 for _ in file_cols))

        for target_id in sorted(all_targets):
            target_name = BODY_NAMES.get(target_id, f"Body {target_id}")
            row = [target_name[:30]]

            for filepath, results in all_results.items():
                target_data = [r for r in results if r['target'] == target_id]
                if target_data:
                    r = target_data[0]
                    if r['interval_days']:
                        val = f"{r['interval_days']:.2f}d"
                    else:
                        val = "✓"
                else:
                    val = "—"
                row.append(f"{val:<15}")

            print(f"{row[0]:<30} " + " | ".join(row[1:]))

        print()

        # Recommendation
        print(f"\n{'='*90}")
        print("CONVERSION RECOMMENDATIONS")
        print(f"{'='*90}\n")

        for filepath, results in all_results.items():
            print(f"\n{Path(filepath).name}:")

            intervals = [r['interval_days'] for r in results if r['interval_days'] is not None]
            if intervals:
                max_interval = max(intervals)
                print(f"  Max native interval: {max_interval:.2f} days")
                print(f"  Recommended --interval: {max_interval:.1f} (preserve native resolution)")
                print(f"  Alternative (smaller): {max_interval/2:.1f} (2x oversampling)")
                print(f"  Alternative (larger): {max_interval*2:.1f} (2x compression, faster)")

            # List bodies
            bodies = sorted(set(r['target'] for r in results if r['target'] in BODY_NAMES))
            body_str = ",".join(map(str, bodies))
            print(f"  Bodies: {body_str}")
            print(f"  Count: {len(bodies)}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze SPICE ephemeris intervals and available bodies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  python inventory_spice.py data/ephemerides/epm/2021/spice/epm2021.bsp

  # Compare multiple files
  python inventory_spice.py data/ephemerides/jpl/de431/de431_part-1.bsp \\
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
        results = analyze_file(args.files[0])
        print_statistics(results, Path(args.files[0]).name)

    print("\n✅ Analysis complete!\n")


if __name__ == '__main__':
    main()
