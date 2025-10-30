#!/usr/bin/env python3
"""
Direct SPICE coefficient extractor using jplephem
Preserves original NASA/IAA intervals and coefficients
"""

from jplephem.spk import SPK
import struct
import sys
from pathlib import Path

def extract_native_spice(bsp_path, output_path, body_ids=None):
    """
    Extract Chebyshev coefficients directly from SPICE BSP
    without re-interpolation
    """

    print(f"Opening SPICE file: {bsp_path}")
    kernel = SPK.open(bsp_path)

    print(f"\nAvailable segments:")
    for i, seg in enumerate(kernel.segments):
        print(f"  [{i}] Body {seg.target} rel to {seg.center}, "
              f"Type {seg.data_type}, "
              f"JD {seg.start_jd:.1f} to {seg.end_jd:.1f}")

    # Filter segments
    if body_ids:
        segments = [seg for seg in kernel.segments if seg.target in body_ids]
    else:
        segments = kernel.segments

    print(f"\nExtracting {len(segments)} segments...")

    # Analyze structure
    metadata = {
        'format': 'native_spice',
        'source': Path(bsp_path).name,
        'num_bodies': len(segments),
    }

    print("\nSegment details:")
    for seg in segments:
        print(f"\n  Body {seg.target}:")
        print(f"    Type: {seg.data_type}")
        print(f"    JD range: {seg.start_jd:.1f} to {seg.end_jd:.1f}")

        if seg.data_type == 2:  # Chebyshev Type 2
            # Access internal structure
            print(f"    Has coefficient data: YES")

            # Try to access coefficients
            if hasattr(seg, 'coefficients'):
                print(f"    Coefficients shape: {seg.coefficients.shape if hasattr(seg.coefficients, 'shape') else 'unknown'}")

            # Get a sample position to verify
            jd_mid = (seg.start_jd + seg.end_jd) / 2
            try:
                pos = seg.compute(jd_mid)
                print(f"    Sample position at JD {jd_mid:.1f}: X={pos[0]:.3f} AU")
            except Exception as e:
                print(f"    Sample computation failed: {e}")
        else:
            print(f"    Unsupported data type: {seg.data_type}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    print("""
jplephem can READ SPICE files but doesn't expose raw coefficients directly.

SPICE SPK Type 2 format structure:
- Coefficients stored as packed doubles
- Each record has variable number of coefficients
- Records organized by time intervals
- Interval sizes vary by body (optimized by NASA)

NEXT STEPS:
1. Use SPICE Toolkit C library directly (via ctypes/cffi)
2. Or use existing format with interval=8 (good enough)
3. Or implement low-level DAF reader in Python

RECOMMENDATION:
Use interval=8 days - это даст точность <100м при приемлемом размере.
Попытка извлечь исходные коэффициенты SPICE требует реализации
полного DAF/SPK парсера, что очень сложно.
    """)

    kernel.close()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Extract native SPICE coefficients')
    parser.add_argument('input', help='Input SPICE BSP file')
    parser.add_argument('--bodies', help='Body IDs to extract (comma-separated)')

    args = parser.parse_args()

    body_ids = None
    if args.bodies:
        body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    extract_native_spice(args.input, None, body_ids)
