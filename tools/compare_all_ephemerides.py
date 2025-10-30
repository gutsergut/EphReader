#!/usr/bin/env python3
"""
Comprehensive ephemeris accuracy comparison.

Compares geocentric ecliptic longitude accuracy across multiple ephemerides:
- JPL DE440 (reference/gold standard)
- EPM2021 (Russian high-precision)
- Swiss Ephemeris (widely used in astrology)

Uses ANGULAR SEPARATION (arcseconds) as the primary metric - most meaningful
for practical astronomy/astrology applications.

Author: AI Assistant
Date: 2025-10-30
"""

import numpy as np
from pathlib import Path
import sys

try:
    import calceph
    HAS_CALCEPH = True
except ImportError:
    HAS_CALCEPH = False
    print("WARNING: calceph not found, DE440/EPM2021 comparison skipped")
    print("  Build calceph first: cd vendor/calceph-4.0.1 && cmake --build build")
    print()


class EphemerisComparison:
    """Compare ephemeris accuracy using geocentric ecliptic coordinates."""

    # Body IDs (NAIF)
    BODIES = {
        'Sun': 10,
        'Moon': 301,
        'Mercury': 1,
        'Venus': 2,
        'Mars': 4,
        'Jupiter': 5,
        'Saturn': 6,
        'Uranus': 7,
        'Neptune': 8,
        'Pluto': 9,
        'Earth': 399,
    }

    # Swiss Ephemeris body IDs (different!)
    SE_BODIES = {
        'Sun': 0,
        'Moon': 1,
        'Mercury': 2,
        'Venus': 3,
        'Mars': 4,
        'Jupiter': 5,
        'Saturn': 6,
        'Uranus': 7,
        'Neptune': 8,
        'Pluto': 9,
    }

    # Test epochs (covering different centuries)
    TEST_EPOCHS = [
        ('J1900.0', 2415020.0),
        ('J1950.0', 2433282.5),
        ('J2000.0', 2451545.0),
        ('2010-01-01', 2455197.5),
        ('2020-01-01', 2458849.5),
        ('2030-01-01', 2462502.5),
        ('2050-01-01', 2469807.5),
    ]

    def __init__(self):
        self.de440_file = Path("data/ephemerides/jpl/de440/linux_p1550p2650.440")
        self.epm2021_file = Path("data/ephemerides/epm/2021/epm2021.eph")
        self.ephe_path = Path("ephe")

        self.de440 = None
        self.epm2021 = None

    def load_ephemerides(self):
        """Load CALCEPH ephemerides."""
        if not HAS_CALCEPH:
            return False

        print("Loading ephemerides...")

        # Load JPL DE440
        if self.de440_file.exists():
            self.de440 = calceph.CalcephBin()
            self.de440.open(str(self.de440_file))
            print(f"  ✓ JPL DE440: {self.de440_file}")
        else:
            print(f"  ⚠ JPL DE440 not found: {self.de440_file}")

        # Load EPM2021
        if self.epm2021_file.exists():
            self.epm2021 = calceph.CalcephBin()
            self.epm2021.open(str(self.epm2021_file))
            print(f"  ✓ EPM2021: {self.epm2021_file}")
        else:
            print(f"  ⚠ EPM2021 not found: {self.epm2021_file}")

        print()
        return True

    def compute_geocentric_ecliptic(self, eph, body_id, jd):
        """
        Compute geocentric ecliptic longitude/latitude.

        Returns:
            tuple: (longitude_deg, latitude_deg, distance_au) or None
        """
        if eph is None:
            return None

        try:
            # Get heliocentric position of body
            pos_body = eph.compute(jd, 0.0, body_id, 0,
                                   calceph.Constants.UNIT_AU + calceph.Constants.USECSUN)

            # Get heliocentric position of Earth
            pos_earth = eph.compute(jd, 0.0, 399, 0,
                                    calceph.Constants.UNIT_AU + calceph.Constants.USECSUN)

            if pos_body is None or pos_earth is None:
                return None

            # Geocentric position
            dx = pos_body[0] - pos_earth[0]
            dy = pos_body[1] - pos_earth[1]
            dz = pos_body[2] - pos_earth[2]

            # Convert to ecliptic longitude/latitude
            # Ecliptic longitude: arctan2(y, x)
            lon_rad = np.arctan2(dy, dx)
            lon_deg = np.degrees(lon_rad) % 360.0

            # Distance
            r = np.sqrt(dx*dx + dy*dy + dz*dz)

            # Ecliptic latitude: arcsin(z/r)
            lat_rad = np.arcsin(dz / r)
            lat_deg = np.degrees(lat_rad)

            return (lon_deg, lat_deg, r)

        except Exception as e:
            print(f"    Error computing {body_id}: {e}")
            return None

    def angular_separation(self, lon1, lat1, lon2, lat2):
        """
        Calculate angular separation between two points on sphere.

        Uses haversine formula for accuracy.

        Returns:
            float: Angular separation in arcseconds
        """
        # Convert to radians
        lon1_rad = np.radians(lon1)
        lat1_rad = np.radians(lat1)
        lon2_rad = np.radians(lon2)
        lat2_rad = np.radians(lat2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))

        # Convert to arcseconds
        return np.degrees(c) * 3600.0

    def compare_calceph_sources(self):
        """Compare EPM2021 vs JPL DE440."""
        if not HAS_CALCEPH or self.de440 is None or self.epm2021 is None:
            return

        print("=" * 80)
        print("EPM2021 vs JPL DE440 Accuracy Comparison")
        print("=" * 80)
        print()
        print("Metric: Geocentric ecliptic angular separation (arcseconds)")
        print()

        # Results storage
        results = {body: [] for body in self.BODIES.keys() if body not in ['Earth']}

        for epoch_name, jd in self.TEST_EPOCHS:
            print(f"Epoch: {epoch_name} (JD {jd})")
            print("-" * 80)

            for body_name, body_id in self.BODIES.items():
                if body_name == 'Earth':
                    continue

                # Compute from both sources
                de440_pos = self.compute_geocentric_ecliptic(self.de440, body_id, jd)
                epm_pos = self.compute_geocentric_ecliptic(self.epm2021, body_id, jd)

                if de440_pos is None or epm_pos is None:
                    print(f"  {body_name:10s}: Data unavailable")
                    continue

                lon_de, lat_de, r_de = de440_pos
                lon_epm, lat_epm, r_epm = epm_pos

                # Angular separation
                sep_arcsec = self.angular_separation(lon_de, lat_de, lon_epm, lat_epm)

                # Longitude difference (for debugging)
                dlon = abs(lon_epm - lon_de)
                if dlon > 180:
                    dlon = 360 - dlon
                dlon_arcsec = dlon * 3600

                results[body_name].append(sep_arcsec)

                # Format output
                if sep_arcsec < 1.0:
                    status = "✅"
                elif sep_arcsec < 60.0:
                    status = "⚠️"
                else:
                    status = "❌"

                print(f"  {body_name:10s}: {sep_arcsec:8.3f}\" {status}  " +
                      f"(lon: {lon_epm:7.3f}° vs {lon_de:7.3f}°, Δ={dlon_arcsec:.1f}\")")

            print()

        # Summary statistics
        print("=" * 80)
        print("SUMMARY: EPM2021 Accuracy vs JPL DE440")
        print("=" * 80)
        print()
        print(f"{'Body':<12} {'Samples':>8} {'Mean':>10} {'Median':>10} {'Max':>10} {'Status'}")
        print("-" * 80)

        for body_name in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars',
                          'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
            if body_name not in results or len(results[body_name]) == 0:
                continue

            errors = np.array(results[body_name])
            mean_err = np.mean(errors)
            median_err = np.median(errors)
            max_err = np.max(errors)

            # Status
            if median_err < 1.0:
                status = "✅ Excellent"
            elif median_err < 10.0:
                status = "✅ Good"
            elif median_err < 60.0:
                status = "⚠️ Acceptable"
            else:
                status = "❌ Poor"

            print(f"{body_name:<12} {len(errors):>8} " +
                  f"{mean_err:>9.2f}\" {median_err:>9.2f}\" {max_err:>9.2f}\" {status}")

        print()

    def compare_with_swisseph(self):
        """Compare Swiss Ephemeris vs JPL DE440 using FFI."""
        print("=" * 80)
        print("Swiss Ephemeris vs JPL DE440 Accuracy Comparison")
        print("=" * 80)
        print()
        print("Implementation: PHP FFI (run separate script)")
        print("Script: php/examples/compare_all_ephemerides.php")
        print()
        print("This will be implemented in PHP due to better Swiss Eph integration.")
        print()

    def run(self):
        """Run comparison."""
        print("=" * 80)
        print("Comprehensive Ephemeris Accuracy Comparison")
        print("=" * 80)
        print()

        if self.load_ephemerides():
            self.compare_calceph_sources()

        self.compare_with_swisseph()

        # Cleanup
        if self.de440:
            self.de440.close()
        if self.epm2021:
            self.epm2021.close()


def main():
    """Main entry point."""
    comparison = EphemerisComparison()
    comparison.run()

    print("=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)
    print()
    print("Note: For Swiss Ephemeris comparison, run:")
    print("  php php/examples/compare_all_ephemerides.php")
    print()


if __name__ == '__main__':
    main()
