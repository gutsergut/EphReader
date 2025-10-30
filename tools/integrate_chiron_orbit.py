#!/usr/bin/env python3
"""
Simple orbital integrator for Chiron using Keplerian elements
with perturbations from major planets.

This is a simplified N-body integrator for comparison purposes.
"""

import numpy as np
import json
import sys
from datetime import datetime
from typing import Dict, Tuple, List

# Astronomical constants
AU = 149597870.691  # km
MU_SUN = 132712440018.0  # km^3/s^2 (GM of Sun)

# Gravitational parameters of major planets (km^3/s^2)
PLANET_GM = {
    'Jupiter': 126686534.0,
    'Saturn': 37931187.0,
    'Uranus': 5793939.0,
    'Neptune': 6836529.0
}

# Mean orbital elements for planets (simplified, epoch J2000)
PLANET_ELEMENTS = {
    'Jupiter': {
        'a': 5.2044,      # AU
        'e': 0.0489,
        'i': 1.303,       # deg
        'om': 100.464,    # deg
        'w': 273.867,     # deg
        'L': 34.351,      # mean longitude
        'period': 11.86   # years
    },
    'Saturn': {
        'a': 9.5826,
        'e': 0.0565,
        'i': 2.485,
        'om': 113.665,
        'w': 339.392,
        'L': 50.077,
        'period': 29.46
    },
    'Uranus': {
        'a': 19.2184,
        'e': 0.0472,
        'i': 0.773,
        'om': 74.006,
        'w': 96.998,
        'L': 314.055,
        'period': 84.01
    },
    'Neptune': {
        'a': 30.1104,
        'e': 0.0086,
        'i': 1.770,
        'om': 131.784,
        'w': 276.336,
        'L': 304.880,
        'period': 164.79
    }
}


def elements_to_cartesian(a: float, e: float, i: float, om: float, w: float,
                         ma: float, mu: float = MU_SUN) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert Keplerian orbital elements to Cartesian position and velocity.

    Args:
        a: Semi-major axis (AU)
        e: Eccentricity
        i: Inclination (degrees)
        om: Longitude of ascending node (degrees)
        w: Argument of perihelion (degrees)
        ma: Mean anomaly (degrees)
        mu: Gravitational parameter (km^3/s^2)

    Returns:
        (position, velocity) in km and km/s
    """
    # Convert to radians
    i_rad = np.radians(i)
    om_rad = np.radians(om)
    w_rad = np.radians(w)
    ma_rad = np.radians(ma)

    # Convert AU to km
    a_km = a * AU

    # Solve Kepler's equation for eccentric anomaly
    E = ma_rad
    for _ in range(10):  # Newton-Raphson iteration
        E = ma_rad + e * np.sin(E)

    # True anomaly
    nu = 2 * np.arctan2(
        np.sqrt(1 + e) * np.sin(E / 2),
        np.sqrt(1 - e) * np.cos(E / 2)
    )

    # Distance from focus
    r = a_km * (1 - e * np.cos(E))

    # Position in orbital plane
    x_orb = r * np.cos(nu)
    y_orb = r * np.sin(nu)

    # Velocity in orbital plane
    h = np.sqrt(mu * a_km * (1 - e**2))  # Specific angular momentum
    vx_orb = -mu / h * np.sin(nu)
    vy_orb = mu / h * (e + np.cos(nu))

    # Rotation matrices
    # R3(-Omega) * R1(-i) * R3(-omega)
    cos_om = np.cos(om_rad)
    sin_om = np.sin(om_rad)
    cos_i = np.cos(i_rad)
    sin_i = np.sin(i_rad)
    cos_w = np.cos(w_rad)
    sin_w = np.sin(w_rad)

    # Transform to ecliptic frame
    x = (cos_om * cos_w - sin_om * sin_w * cos_i) * x_orb + \
        (-cos_om * sin_w - sin_om * cos_w * cos_i) * y_orb
    y = (sin_om * cos_w + cos_om * sin_w * cos_i) * x_orb + \
        (-sin_om * sin_w + cos_om * cos_w * cos_i) * y_orb
    z = (sin_w * sin_i) * x_orb + (cos_w * sin_i) * y_orb

    vx = (cos_om * cos_w - sin_om * sin_w * cos_i) * vx_orb + \
         (-cos_om * sin_w - sin_om * cos_w * cos_i) * vy_orb
    vy = (sin_om * cos_w + cos_om * sin_w * cos_i) * vx_orb + \
         (-sin_om * sin_w + cos_om * cos_w * cos_i) * vy_orb
    vz = (sin_w * sin_i) * vx_orb + (cos_w * sin_i) * vy_orb

    position = np.array([x, y, z])
    velocity = np.array([vx, vy, vz])

    return position, velocity


def cartesian_to_spherical(pos: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert Cartesian coordinates to spherical (longitude, latitude, distance).

    Args:
        pos: Position vector [x, y, z] in km

    Returns:
        (longitude, latitude, distance) in degrees, degrees, AU
    """
    x, y, z = pos
    r = np.linalg.norm(pos)

    lon = np.degrees(np.arctan2(y, x))
    if lon < 0:
        lon += 360

    lat = np.degrees(np.arcsin(z / r))

    dist_au = r / AU

    return lon, lat, dist_au


def compute_planet_position(planet_name: str, jd: float) -> np.ndarray:
    """
    Compute approximate position of a major planet at given JD.
    Uses simplified Keplerian motion from J2000 epoch.

    Args:
        planet_name: Name of planet
        jd: Julian Date

    Returns:
        Position vector [x, y, z] in km
    """
    elem = PLANET_ELEMENTS[planet_name]

    # Days from J2000.0
    t = jd - 2451545.0
    t_cent = t / 36525.0  # Julian centuries

    # Mean longitude at epoch
    L0 = elem['L']
    n = 360.0 / (elem['period'] * 365.25)  # Mean motion (deg/day)
    L = L0 + n * t

    # Mean anomaly
    ma = L - elem['w']
    ma = ma % 360.0

    # Compute position
    pos, _ = elements_to_cartesian(
        elem['a'], elem['e'], elem['i'],
        elem['om'], elem['w'], ma
    )

    return pos


def compute_perturbation(chiron_pos: np.ndarray, chiron_vel: np.ndarray,
                        jd: float) -> np.ndarray:
    """
    Compute gravitational perturbation on Chiron from major planets.

    Args:
        chiron_pos: Chiron position [x, y, z] in km
        chiron_vel: Chiron velocity [vx, vy, vz] in km/s
        jd: Julian Date

    Returns:
        Acceleration vector [ax, ay, az] in km/s^2
    """
    accel = np.zeros(3)

    for planet_name, gm in PLANET_GM.items():
        # Get planet position
        planet_pos = compute_planet_position(planet_name, jd)

        # Vector from planet to Chiron
        d = chiron_pos - planet_pos
        r = np.linalg.norm(d)

        # Avoid division by zero
        if r < 1.0:
            continue

        # Gravitational acceleration
        # a = -GM * (r / |r|^3)
        accel -= gm * d / r**3

    return accel


def integrate_orbit(elements: Dict, start_jd: float, end_jd: float,
                   step_days: float = 1.0) -> List[Dict]:
    """
    Integrate Chiron orbit from start to end JD using simple integrator.

    Args:
        elements: Orbital elements dictionary
        start_jd: Start Julian Date
        end_jd: End Julian Date
        step_days: Integration step size in days

    Returns:
        List of dictionaries with JD, lon, lat, dist
    """
    print(f"Starting integration from JD {start_jd} to {end_jd}")
    print(f"Step size: {step_days} days")
    print()

    # Extract elements
    elem = elements['elements']
    epoch_jd = elements['epoch_jd']

    # If a is None, compute from period
    if elem['a'] is None:
        if 'per' in elem and elem['per'] is not None:
            # Kepler's third law: a³ = μ·T²/(4π²)
            # For Sun, μ = 1 in units where a is in AU and T in years
            # a³ = T² → a = T^(2/3)
            T_years = elem['per']
            elem['a'] = T_years**(2.0/3.0)
            print(f"Computed a from period: {elem['a']:.8f} AU (T={T_years:.2f} years)")
        elif 'n' in elem and elem['n'] is not None:
            # Fallback: compute from mean motion
            # n in deg/day, period T = 360/n days
            T_days = 360.0 / elem['n']
            T_years = T_days / 365.25
            elem['a'] = T_years**(2.0/3.0)
            print(f"Computed a from n: {elem['a']:.8f} AU (T={T_years:.2f} years)")
        else:
            raise ValueError("Semi-major axis 'a' is None and neither 'per' nor 'n' available")

    # Convert to Cartesian at epoch
    pos, vel = elements_to_cartesian(
        elem['a'], elem['e'], elem['i'],
        elem['om'], elem['w'], elem['ma']
    )

    # Propagate to start_jd if needed
    if abs(start_jd - epoch_jd) > 0.1:
        print(f"Propagating from epoch {epoch_jd} to start {start_jd}...")
        dt_days = start_jd - epoch_jd
        dt_sec = dt_days * 86400.0

        # Simple Keplerian propagation
        pos += vel * dt_sec

    # Integration loop
    results = []
    jd = start_jd
    step_sec = step_days * 86400.0

    n_steps = int((end_jd - start_jd) / step_days)
    print(f"Integration steps: {n_steps}")
    print()

    for i in range(n_steps + 1):
        # Compute spherical coordinates
        lon, lat, dist = cartesian_to_spherical(pos)

        results.append({
            'jd': jd,
            'lon': lon,
            'lat': lat,
            'dist': dist
        })

        if i % 365 == 0:
            year = 2000 + (jd - 2451545.0) / 365.25
            print(f"Progress: {i}/{n_steps} steps, Year {year:.1f}, "
                  f"Lon={lon:.2f}°, Lat={lat:.2f}°, Dist={dist:.3f} AU")

        # Integration step (simple Euler for now)
        # In production, use RK4 or better integrator

        # Solar gravity (two-body)
        r = np.linalg.norm(pos)
        accel_sun = -MU_SUN * pos / r**3

        # Planetary perturbations
        accel_pert = compute_perturbation(pos, vel, jd)

        # Total acceleration
        accel = accel_sun + accel_pert

        # Update velocity and position
        vel += accel * step_sec
        pos += vel * step_sec

        jd += step_days

    print()
    print(f"✓ Integration complete: {len(results)} points")

    return results


def main():
    if len(sys.argv) < 4:
        print("Usage: python integrate_chiron_orbit.py <elements.json> <start_jd> <end_jd> [step_days]")
        print()
        print("Example:")
        print("  python integrate_chiron_orbit.py chiron_elements_manual.json 2451545.0 2451910.0 16.0")
        sys.exit(1)

    elements_file = sys.argv[1]
    start_jd = float(sys.argv[2])
    end_jd = float(sys.argv[3])
    step_days = float(sys.argv[4]) if len(sys.argv) > 4 else 16.0

    # Load elements
    with open(elements_file, 'r') as f:
        elements = json.load(f)

    print("=" * 80)
    print("CHIRON ORBIT INTEGRATION")
    print("=" * 80)

    # Handle both formats: manual (name+designation) and MPC (readable_name)
    name = elements.get('readable_name') or f"{elements.get('name', 'Unknown')} ({elements.get('designation', 'N/A')})"
    print(f"Object:       {name}")
    print(f"Epoch:        JD {elements['epoch_jd']}")
    print(f"Elements:")
    for key, val in elements['elements'].items():
        print(f"  {key:6s} = {val}")
    print()

    # Integrate
    results = integrate_orbit(elements, start_jd, end_jd, step_days)

    # Save results
    output_file = elements_file.replace('.json', '_integrated.json')
    output_data = {
        'source': 'Simple Keplerian integrator with planetary perturbations',
        'elements': elements,
        'integration': {
            'start_jd': start_jd,
            'end_jd': end_jd,
            'step_days': step_days,
            'n_points': len(results)
        },
        'positions': results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Results saved to: {output_file}")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
