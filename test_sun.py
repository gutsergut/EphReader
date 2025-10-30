import spiceypy as sp

sp.furnsh('data/ephemerides/epm/2021/spice/epm2021.bsp')

# Test Sun (ID 10) at different times
test_jds = [
    2374000.5,  # Start of EPM2021 range
    2451545.0,  # J2000.0
    2500000.0,  # Mid range
    2530000.5   # End of EPM2021 range
]

print("Testing Sun (ID 10) availability:")
for jd in test_jds:
    et = (jd - 2451545.0) * 86400.0
    try:
        state, _ = sp.spkgps(10, et, 'J2000', 0)
        print(f"  JD {jd}: ✓ OK (X={state[0]/149597870.7:.3f} AU)")
    except Exception as e:
        print(f"  JD {jd}: ✗ ERROR - {e}")

# Test during conversion interval
print("\nTesting Sun during conversion interval (32-day steps):")
jd_start = 2451536.5
jd_end = jd_start + 32.0
for i in range(3):
    jd = jd_start + i * 10.0  # Sample 3 points
    et = (jd - 2451545.0) * 86400.0
    try:
        state, _ = sp.spkgps(10, et, 'J2000', 0)
        print(f"  JD {jd}: ✓ OK")
    except Exception as e:
        print(f"  JD {jd}: ✗ ERROR - {e}")
