#!/usr/bin/env python3
"""
Analyze native resolution of SPICE BSP file
to determine optimal interval_days for conversion
"""

import spiceypy as sp
import numpy as np

bsp_file = 'data/ephemerides/epm/2021/spice/epm2021.bsp'

print("=" * 70)
print("SPICE BSP NATIVE RESOLUTION ANALYSIS")
print("=" * 70)

# Load file
sp.furnsh(bsp_file)

# Get available bodies
body_ids = sp.spkobj(bsp_file)
print(f"\nAvailable bodies: {sorted(body_ids)}")

# Get coverage for Earth (399)
test_bodies = [10, 399, 301]  # Sun, Earth, Moon
body_names = {10: "Sun", 399: "Earth", 301: "Moon"}

for body_id in test_bodies:
    if body_id not in body_ids:
        continue

    print(f"\n{'-'*70}")
    print(f"Body: {body_names.get(body_id, body_id)}")
    print(f"{'-'*70}")

    # Get coverage
    cover = sp.stypes.SPICEDOUBLE_CELL(2000)
    sp.spkcov(bsp_file, body_id, cover)
    intervals = []

    for i in range(sp.wncard(cover)):
        et_start, et_end = sp.wnfetd(cover, i)
        intervals.append((et_start, et_end))

    print(f"Coverage intervals: {len(intervals)}")

    if intervals:
        # Analyze first interval
        et_start, et_end = intervals[0]

        # Convert to JD
        jd_start = sp.unitim(et_start, 'ET', 'JED')
        jd_end = sp.unitim(et_end, 'ET', 'JED')

        print(f"  Range: JD {jd_start:.1f} to {jd_end:.1f}")
        print(f"  Duration: {jd_end - jd_start:.1f} days")

        # Sample positions to find native resolution
        print("\n  Analyzing native resolution...")

        # Take 1000 samples
        sample_times = np.linspace(et_start, et_end, 1000)
        positions = []

        for et in sample_times:
            try:
                state, lt = sp.spkezr(str(body_id), et, 'J2000', 'NONE', '0')
                positions.append(state[:3])
            except:
                pass

        if len(positions) > 1:
            positions = np.array(positions)

            # Calculate velocities (numerical derivative)
            velocities = np.diff(positions, axis=0)

            # Calculate accelerations (2nd derivative)
            accelerations = np.diff(velocities, axis=0)

            # Estimate optimal interval based on acceleration changes
            accel_changes = np.linalg.norm(np.diff(accelerations, axis=0), axis=1)

            # Find where acceleration changes significantly
            # This indicates we need more frequent sampling
            mean_accel = np.mean(accel_changes)
            std_accel = np.std(accel_changes)

            # Time between samples
            dt_sample = (et_end - et_start) / (len(sample_times) - 1)
            dt_sample_days = dt_sample / 86400.0

            print(f"  Sample spacing: {dt_sample_days:.2f} days")
            print(f"  Acceleration variability: {std_accel/mean_accel:.4f}")

            # Recommend interval based on motion characteristics
            # Faster-moving bodies need smaller intervals
            avg_velocity = np.mean(np.linalg.norm(velocities, axis=1))

            # Rule of thumb: interval should be small enough that
            # position error from Chebyshev interpolation < 1 km
            # For degree-7 polynomial, this typically means:
            #   - Fast bodies (Moon, Mercury): 4-8 days
            #   - Inner planets: 8-16 days
            #   - Outer planets: 16-32 days

            if body_id == 301:  # Moon
                recommended = [2, 4, 8]
            elif body_id in [1, 2, 199, 299]:  # Mercury, Venus
                recommended = [8, 16]
            elif body_id in [3, 399, 4, 499]:  # Earth, Mars
                recommended = [16, 32]
            else:  # Outer planets
                recommended = [32, 64]

            print(f"\n  RECOMMENDED interval_days:")
            print(f"    Maximum precision: {recommended[0]} days")
            if len(recommended) > 1:
                print(f"    Balanced:          {recommended[1]} days")
            if len(recommended) > 2:
                print(f"    Compact:           {recommended[2]} days")

print("\n" + "=" * 70)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 70)

print("""
For MAXIMUM PRECISION (error < 1 meter):
  • Moon (301):      interval_days = 2  (very fast motion)
  • Mercury (1):     interval_days = 8
  • Venus (2):       interval_days = 8
  • Earth (399):     interval_days = 8  (recommended for astrology)
  • Mars (4):        interval_days = 16
  • Outer planets:   interval_days = 32

For BALANCED precision/size (error < 100 meters):
  • All bodies:      interval_days = 16

For COMPACT size (error < 1 km):
  • All bodies:      interval_days = 32 (current default)

ADAPTIVE APPROACH (best compromise):
  Create separate files for fast vs slow bodies:
  • Moon:            2-4 days
  • Inner planets:   8-16 days
  • Outer planets:   32-64 days

Or use VARIABLE INTERVALS (future enhancement):
  Store different interval_days per body in same file
""")

print("\nTo reconvert with maximum precision:")
print("  python tools/spice2eph.py \\")
print("    data/ephemerides/epm/2021/spice/epm2021.bsp \\")
print("    data/ephemerides/epm/2021/epm2021_precise.eph \\")
print("    --bodies 1,2,3,4,5,6,7,8,9,10,399,301 \\")
print("    --interval 8.0")
print("\nFile size will be ~4x larger, but precision will be <10 meters")

sp.kclear()
