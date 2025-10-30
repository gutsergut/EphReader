import spiceypy as sp
import numpy as np

sp.furnsh('data/ephemerides/epm/2021/spice/epm2021.bsp')

# Test Moon at problematic interval
jd_start = 2451536.5
jd_end = jd_start + 32.0

degree = 7
n_samples = degree + 1

# Chebyshev nodes
nodes = np.cos(np.pi * (2 * np.arange(n_samples) + 1) / (2 * n_samples))

# Map to JD interval
jd_mid = (jd_start + jd_end) / 2
jd_half = (jd_end - jd_start) / 2
jd_samples = jd_mid + jd_half * nodes

print(f"Testing Moon (ID 301) for interval [{jd_start}, {jd_end}]")
print(f"Sample points: {len(jd_samples)}")

# Get positions
positions = []
for i, jd in enumerate(jd_samples):
    et = (jd - 2451545.0) * 86400.0
    try:
        state, _ = sp.spkgps(301, et, 'J2000', 0)
        pos_au = [x / 149597870.7 for x in state[:3]]
        positions.append(pos_au)
        print(f"  Sample {i}: JD={jd:.2f}, ET={et:.0f}s, pos={pos_au[0]:.6f} AU")
    except Exception as e:
        print(f"  Sample {i}: ERROR - {e}")
        positions.append([0, 0, 0])

positions = np.array(positions)
print(f"\nPositions shape: {positions.shape}")
print(f"X range: [{positions[:, 0].min():.6f}, {positions[:, 0].max():.6f}] AU")

# Try fitting
print("\nAttempting Chebyshev fit...")
try:
    x_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 0], degree)
    print(f"✓ X coefficients fitted: {len(x_coeffs)} values")
    print(f"  First 3 coeffs: {x_coeffs[:3]}")

    y_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 1], degree)
    print(f"✓ Y coefficients fitted: {len(y_coeffs)} values")

    z_coeffs = np.polynomial.chebyshev.chebfit(nodes, positions[:, 2], degree)
    print(f"✓ Z coefficients fitted: {len(z_coeffs)} values")

    print("\n✅ Moon fitting works!")
except Exception as e:
    print(f"\n❌ ERROR during fitting: {e}")
    import traceback
    traceback.print_exc()
