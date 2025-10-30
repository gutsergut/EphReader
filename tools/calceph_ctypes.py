#!/usr/bin/env python3
"""
Direct calceph C library access using ctypes (no Cython needed).

This bypasses the Cython compilation issues by calling the compiled
calceph.dll/libcalceph.so directly using Python's ctypes FFI.
"""

import sys
import json
import ctypes
from pathlib import Path


# Find calceph library
calceph_dll = Path("vendor/calceph-4.0.1/build/libcalceph.dll")
if not calceph_dll.exists():
    calceph_dll = Path("vendor/calceph-4.0.1/install/bin/libcalceph.dll")
if not calceph_dll.exists():
    print(json.dumps({"error": "calceph library not found"}), file=sys.stderr)
    sys.exit(1)

# Load calceph library
try:
    calceph = ctypes.CDLL(str(calceph_dll))
except Exception as e:
    print(json.dumps({"error": f"Failed to load calceph: {e}"}), file=sys.stderr)
    sys.exit(1)

# Define C function signatures
# t_calcephbin* calceph_open(const char *filename)
calceph.calceph_open.argtypes = [ctypes.c_char_p]
calceph.calceph_open.restype = ctypes.c_void_p

# int calceph_compute(t_calcephbin *eph, double JD0, double time,
#                     int target, int center, double PV[6])
calceph.calceph_compute.argtypes = [
    ctypes.c_void_p,  # eph
    ctypes.c_double,  # JD0
    ctypes.c_double,  # time
    ctypes.c_int,     # target
    ctypes.c_int,     # center
    ctypes.POINTER(ctypes.c_double * 6)  # PV
]
calceph.calceph_compute.restype = ctypes.c_int

# void calceph_close(t_calcephbin *eph)
calceph.calceph_close.argtypes = [ctypes.c_void_p]
calceph.calceph_close.restype = None


def get_position(ephemeris_file, jd, target_id, center_id=0):
    """
    Get position and velocity from ephemeris.

    Args:
        ephemeris_file: Path to ephemeris file
        jd: Julian Day
        target_id: NAIF ID of target body
        center_id: NAIF ID of center (0 = Solar System Barycenter)

    Returns:
        dict with pos=[x,y,z] and vel=[vx,vy,vz] in AU and AU/day
    """
    # Open ephemeris
    eph = calceph.calceph_open(ephemeris_file.encode('utf-8'))
    if not eph:
        return {"error": f"Failed to open ephemeris: {ephemeris_file}"}

    try:
        # Allocate result array
        pv = (ctypes.c_double * 6)()

        # Compute position (using unit AU + velocity flag)
        # Units: CALCEPH_UNIT_AU (1) + CALCEPH_UNIT_DAY (2) + CALCEPH_USE_NAIFID (4) = 7
        result = calceph.calceph_compute(eph, jd, 0.0, target_id, center_id, pv)

        if result == 0:
            return {"error": f"Failed to compute position for body {target_id}"}

        return {
            "jd": jd,
            "target": target_id,
            "center": center_id,
            "pos": [pv[0], pv[1], pv[2]],
            "vel": [pv[3], pv[4], pv[5]]
        }

    finally:
        # Close ephemeris
        calceph.calceph_close(eph)


def main():
    if len(sys.argv) < 4:
        print(json.dumps({
            "error": "Usage: calceph_ctypes.py <ephemeris_file> <jd> <body_id> [center_id]"
        }))
        sys.exit(1)

    ephemeris_file = sys.argv[1]
    jd = float(sys.argv[2])
    body_id = int(sys.argv[3])
    center_id = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    result = get_position(ephemeris_file, jd, body_id, center_id)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
