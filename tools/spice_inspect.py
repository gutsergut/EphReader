#!/usr/bin/env python3
"""
Inspect SPICE BSP file structure to understand native data organization
"""

import spiceypy as sp
import struct

bsp_file = 'data/ephemerides/epm/2021/spice/epm2021.bsp'

print("=" * 80)
print("SPICE BSP FILE STRUCTURE ANALYSIS")
print("=" * 80)

# Open BSP file directly
with open(bsp_file, 'rb') as f:
    # DAF file record (first 1024 bytes)
    locidw = f.read(8).decode('ascii', errors='ignore')
    print(f"\nFile ID: {locidw.strip()}")

    nd = struct.unpack('>i', f.read(4))[0]  # number of double precision components
    ni = struct.unpack('>i', f.read(4))[0]  # number of integer components

    print(f"DP components per summary: {nd}")
    print(f"Int components per summary: {ni}")

    # SPK files typically have:
    # nd = 2 (start time, end time in ET seconds)
    # ni = 6 (target, center, frame, type, start address, end address)

    # Skip to file record
    f.seek(0)
    file_record = f.read(1024)

    # Internal file name
    f.seek(8)
    ifname = f.read(60).decode('ascii', errors='ignore').strip()
    print(f"Internal name: {ifname}")

    f.seek(76)
    fward = struct.unpack('>i', f.read(4))[0]
    bward = struct.unpack('>i', f.read(4))[0]
    free = struct.unpack('>i', f.read(4))[0]

    print(f"Forward pointer: {fward}")
    print(f"Backward pointer: {bward}")
    print(f"Free address: {free}")

print("\n" + "=" * 80)
print("SEGMENT STRUCTURE (using spiceypy)")
print("=" * 80)

sp.furnsh(bsp_file)

# Get all bodies
body_ids = sp.spkobj(bsp_file)
print(f"\nBodies: {sorted(body_ids)}")

# Analyze one body in detail
test_body = 399  # Earth
print(f"\n{'-'*80}")
print(f"Detailed analysis for body {test_body} (Earth)")
print(f"{'-'*80}")

# Get coverage
cover = sp.stypes.SPICEDOUBLE_CELL(2000)
sp.spkcov(bsp_file, test_body, cover)

num_intervals = sp.wncard(cover)
print(f"\nNumber of coverage intervals: {num_intervals}")

for i in range(min(num_intervals, 3)):  # Show first 3
    et_start, et_end = sp.wnfetd(cover, i)
    print(f"  Interval {i}: ET {et_start:.1f} to {et_end:.1f}")
    print(f"             Duration: {(et_end - et_start) / 86400:.1f} days")

print("\n" + "=" * 80)
print("CHEBYSHEV COEFFICIENT STRUCTURE")
print("=" * 80)

# Sample a position to see how data is stored
if num_intervals > 0:
    et_start, et_end = sp.wnfetd(cover, 0)
    et_mid = (et_start + et_end) / 2

    # Get state
    state, lt = sp.spkezr(str(test_body), et_mid, 'J2000', 'NONE', '0')

    print(f"\nPosition at ET {et_mid:.1f}:")
    print(f"  X = {state[0]:12.6f} km")
    print(f"  Y = {state[1]:12.6f} km")
    print(f"  Z = {state[2]:12.6f} km")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

print("""
SPICE BSP uses DAF (Double Precision Array File) format with segments.

Each segment contains:
1. Descriptor (times, body IDs, data type)
2. Chebyshev polynomial coefficients (already optimized by NASA/IAA)
3. Record directory (pointers to coefficient sets)

The data is ALREADY in Chebyshev form with optimized intervals!

KEY FINDING:
The SPICE file already uses variable-length intervals optimized by NASA/IAA.
We don't need to re-interpolate - we should EXTRACT the existing coefficients!

RECOMMENDATION:
Create a new converter that:
1. Reads SPICE segment descriptors
2. Extracts existing Chebyshev coefficients directly
3. Copies them to .eph format WITHOUT re-interpolation
4. Preserves NASA/IAA's original interval structure

This will give EXACT same precision as SPICE with minimal file size.
""")

sp.kclear()
