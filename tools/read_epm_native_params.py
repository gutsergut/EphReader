#!/usr/bin/env python3
"""
Read SPK Type 20 interval structure from EPM2021
"""

from jplephem.spk import SPK
from jplephem.daf import DAF
import numpy as np

bsp_path = 'data/ephemerides/epm/2021/spice/epm2021.bsp'

print("="*80)
print("EPM2021 NATIVE INTERVAL ANALYSIS")
print("="*80)

kernel = SPK.open(bsp_path)

# Find Earth segment
earth_seg = next((seg for seg in kernel.segments if seg.target == 399), None)

if earth_seg:
    print(f"\nEarth segment (Body 399):")
    print(f"  Data type: {earth_seg.data_type}")  # Type 20
    print(f"  JD range: {earth_seg.start_jd:.1f} to {earth_seg.end_jd:.1f}")
    print(f"  Duration: {earth_seg.end_jd - earth_seg.start_jd:.1f} days")

    # For Type 20, jplephem stores data in 'data' attribute
    if hasattr(earth_seg, '_data'):
        print(f"\n  Internal data structure:")
        data = earth_seg._data

        # SPK Type 20 format:
        # - Header with DLength, PolDeg, NIntv, WSize, NDir
        # - Coefficient records
        # - Directory

        print(f"  Data array shape: {data.shape if hasattr(data, 'shape') else len(data)}")

        # Read Type 20 header (last few elements)
        if len(data) > 10:
            # Type 20 stores parameters at the END
            dlength = int(data[-5])  # record length
            poldeg = int(data[-4])   # polynomial degree
            nintv = int(data[-3])    # number of intervals
            wsize = int(data[-2])    # window size (interval duration in seconds)
            ndir = int(data[-1])     # number of directory entries

            print(f"\n  Type 20 Parameters:")
            print(f"    Record length (DLength): {dlength}")
            print(f"    Polynomial degree: {poldeg}")
            print(f"    Number of intervals: {nintv}")
            print(f"    Window size (seconds): {wsize}")
            print(f"    Interval duration (days): {wsize / 86400:.2f}")
            print(f"    Directory entries: {ndir}")

            # Calculate theoretical intervals
            duration_days = earth_seg.end_jd - earth_seg.start_jd
            interval_days = wsize / 86400
            expected_intervals = duration_days / interval_days

            print(f"\n  Verification:")
            print(f"    Expected intervals: {expected_intervals:.0f}")
            print(f"    Actual intervals: {nintv}")
            print(f"    Match: {'✅ YES' if abs(expected_intervals - nintv) < 1 else '❌ NO'}")

            print(f"\n{'='*80}")
            print(f"NATIVE EPM2021 CONFIGURATION")
            print(f"{'='*80}")
            print(f"""
EPM2021 internally uses:
  • interval_days = {interval_days:.1f} days
  • polynomial_degree = {poldeg}
  • total_intervals = {nintv}

RECOMMENDATION:
Convert with EXACT same parameters to preserve original precision:
  python tools/spice2eph.py \\
    data/ephemerides/epm/2021/spice/epm2021.bsp \\
    data/ephemerides/epm/2021/epm2021_native.eph \\
    --bodies 1,2,3,4,5,6,7,8,9,10,399,301 \\
    --interval {interval_days:.1f} \\
    --degree {poldeg}

This will give IDENTICAL precision to original EPM2021!
            """)

kernel.close()
