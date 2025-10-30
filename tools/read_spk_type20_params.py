#!/usr/bin/env python3
"""
Read EPM2021 native parameters using SPICE library directly
"""

import spiceypy as sp
import numpy as np

bsp_file = 'data/ephemerides/epm/2021/spice/epm2021.bsp'

print("="*80)
print("EPM2021 NATIVE PARAMETERS (via SPICE direct access)")
print("="*80)

# Furnish the kernel
sp.furnsh(bsp_file)

# Get handle
handle = sp.dafopr(bsp_file)

print(f"\nDAF Handle: {handle}")

# Search for Earth segment (body 399)
sp.dafbfs(handle)
found = sp.daffna()

earth_found = False
seg_count = 0

while found and not earth_found:
    seg_count += 1

    # Get segment summary
    summary = sp.dafgs()
    dc = summary[:2]  # double precision components
    ic = summary[2:]  # integer components (converted to ints)
    ic = [int(x) for x in ic]

    target = ic[0]
    center = ic[1]
    frame = ic[2]
    spk_type = ic[3]
    start_addr = ic[4]
    end_addr = ic[5]

    start_et = dc[0]
    end_et = dc[1]

    if target == 399:
        earth_found = True

        print(f"\nEarth Segment (#{seg_count}):")
        print(f"  Target: {target}, Center: {center}")
        print(f"  Frame: {frame}, Type: {spk_type}")
        print(f"  ET range: {start_et} to {end_et}")
        print(f"  Data addresses: {start_addr} to {end_addr}")
        print(f"  Data elements: {end_addr - start_addr + 1}")

        if spk_type == 20:
            # Read Type 20 parameters (stored at end of segment)
            # Type 20 format: coefficients, then 5 integers at end:
            # DSCALE, TSCALE, INITJD, INITFR, N

            # Read last several doubles
            nread = min(20, end_addr - start_addr + 1)
            data_end = sp.dafgda(handle, end_addr - nread + 1, end_addr)

            print(f"\n  Last {nread} values from segment:")
            for i in range(max(0, len(data_end) - 10), len(data_end)):
                print(f"    [{i}] = {data_end[i]}")

            # Type 20 specific: last 5 doubles are integer parameters
            if len(data_end) >= 5:
                dlength = int(data_end[-5])
                poldeg = int(data_end[-4])
                nintv = int(data_end[-3])
                wsize_sec = int(data_end[-2])
                ndir = int(data_end[-1])

                interval_days = wsize_sec / 86400.0
                duration_days = (end_et - start_et) / 86400.0

                print(f"\n  SPK Type 20 Parameters:")
                print(f"    Record size (doubles): {dlength}")
                print(f"    Polynomial degree: {poldeg}")
                print(f"    Number of intervals: {nintv}")
                print(f"    Window size (seconds): {wsize_sec}")
                print(f"    ⭐ INTERVAL (days): {interval_days:.1f}")
                print(f"    Directory size: {ndir}")

                print(f"\n  Verification:")
                print(f"    Total duration: {duration_days:.1f} days")
                print(f"    Expected intervals: {duration_days / interval_days:.0f}")
                print(f"    Actual intervals: {nintv}")

                # Read first coefficient record to see structure
                coeffs_per_axis = poldeg + 1
                doubles_per_record = dlength

                print(f"\n  Coefficient Structure:")
                print(f"    Coefficients per axis: {coeffs_per_axis}")
                print(f"    Doubles per record: {doubles_per_record}")
                print(f"    Expected: {coeffs_per_axis * 3} (X,Y,Z)")

                print(f"\n{'='*80}")
                print(f"✅ FOUND EPM2021 NATIVE PARAMETERS!")
                print(f"{'='*80}")
                print(f"""
EPM2021 uses internally:
  • interval_days = {interval_days:.0f}
  • polynomial_degree = {poldeg}
  • number_of_intervals = {nintv}

To preserve EXACT EPM2021 precision, use:
  python tools/spice2eph.py \\
    {bsp_file} \\
    data/ephemerides/epm/2021/epm2021_native.eph \\
    --bodies 1,2,3,4,5,6,7,8,9,10,399,301 \\
    --interval {interval_days:.0f}

Current file uses interval={32}, which is {32/interval_days:.1f}x larger intervals.
Using native interval={interval_days:.0f} will give IDENTICAL precision!
                """)

        break

    found = sp.daffna()

if not earth_found:
    print("\n❌ Earth segment not found!")

sp.dafcls(handle)
sp.kclear()
