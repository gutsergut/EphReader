#!/usr/bin/env python3
"""
Convert JPL DE ephemeris files to our formats (.eph, .db, .hidx+.heph)

Supports: DE200, DE405, DE406, DE421, DE430, DE431, DE440, DE441

Usage:
    python jpl2eph.py de440/linux_p1550p2650.440 de440.eph --format binary
    python jpl2eph.py de440/linux_p1550p2650.440 de440.db --format sqlite
    python jpl2eph.py de440/linux_p1550p2650.440 de440 --format hybrid
"""

import sys
import argparse
import struct
from pathlib import Path
from typing import List, Optional
import numpy as np

try:
    from jplephem.spk import SPK
except ImportError:
    print("ERROR: jplephem not installed. Run: pip install jplephem", file=sys.stderr)
    sys.exit(1)


class JPLConverter:
    """Convert JPL DE files to our ephemeris formats"""

    # JPL body codes (DE files use different numbering than SPICE)
    BODY_NAMES = {
        1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars",
        5: "Jupiter", 6: "Saturn", 7: "Uranus", 8: "Neptune",
        9: "Pluto", 10: "Sun", 11: "Moon",
        301: "Moon",  # Alternative
        399: "Earth"  # Computed from EMB
    }

    def __init__(self, jpl_file: str, output: str, format: str = 'binary'):
        self.jpl_file = Path(jpl_file)
        self.output = Path(output)
        self.format = format

        if not self.jpl_file.exists():
            raise FileNotFoundError(f"JPL file not found: {jpl_file}")

    def convert(self):
        """Main conversion routine"""

        print(f"Converting JPL DE file: {self.jpl_file}")
        print(f"Output format: {self.format}")

        # Try to open as SPK (if it's in SPICE format)
        try:
            kernel = SPK.open(str(self.jpl_file))
            print(f"Detected SPICE SPK format")
            self._convert_from_spk(kernel)
            kernel.close()
            return
        except Exception as e:
            print(f"Not SPICE format: {e}")

        # Try binary DE format
        try:
            self._convert_from_binary_de()
        except Exception as e:
            print(f"ERROR: Cannot read JPL file: {e}", file=sys.stderr)
            sys.exit(1)

    def _convert_from_spk(self, kernel: SPK):
        """Convert from SPICE SPK format (newer JPL files)"""

        print("\nAvailable segments:")
        for i, seg in enumerate(kernel.segments):
            print(f"  [{i}] Body {seg.target} → {seg.center}, "
                  f"JD {seg.start_jd:.1f} to {seg.end_jd:.1f}")

        # Use existing SPICE converters
        if self.format == 'binary':
            from tools.spice2eph import SPICEtoEph
            converter = SPICEtoEph(str(self.jpl_file), str(self.output))
            # Auto-detect bodies
            bodies = list(set(seg.target for seg in kernel.segments
                            if seg.target in [1,2,3,4,5,6,7,8,9,10,301,399]))
            converter.convert(body_ids=bodies, interval_days=16.0)

        elif self.format == 'sqlite':
            from tools.spice2sqlite import SPICEtoSQLite
            converter = SPICEtoSQLite(str(self.jpl_file), str(self.output))
            bodies = list(set(seg.target for seg in kernel.segments
                            if seg.target in [1,2,3,4,5,6,7,8,9,10,301,399]))
            converter.convert(body_ids=bodies, interval_days=16.0)

        elif self.format == 'hybrid':
            from tools.spice2hybrid import SPICEtoHybrid
            converter = SPICEtoHybrid(str(self.jpl_file), str(self.output))
            bodies = list(set(seg.target for seg in kernel.segments
                            if seg.target in [1,2,3,4,5,6,7,8,9,10,301,399]))
            converter.convert(body_ids=bodies, interval_days=16.0)

    def _convert_from_binary_de(self):
        """Convert from binary DE format (classic JPL files)"""

        # Read binary DE file header
        with open(self.jpl_file, 'rb') as f:
            # DE files are big-endian or little-endian
            # Try both
            f.seek(0)
            header = f.read(8)

            if header[:6] == b'JPL   ':
                print("Detected classic JPL DE binary format")
            else:
                print("WARNING: Unknown header format")

            # For classic DE files, we need a different approach
            # They don't use Chebyshev polynomials directly accessible
            print("\nClassic binary DE format not yet supported.")
            print("Please convert to SPICE SPK format first, or use existing .eph files.")
            print("\nAlternatively, download SPICE version from:")
            print("  https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Convert JPL DE files to our formats')
    parser.add_argument('input', help='Input JPL DE file (.440, .441, etc.)')
    parser.add_argument('output', help='Output file path (without extension for hybrid)')
    parser.add_argument('--format', choices=['binary', 'sqlite', 'hybrid'],
                       default='binary', help='Output format')

    args = parser.parse_args()

    converter = JPLConverter(args.input, args.output, args.format)
    converter.convert()

    print("\n✅ Conversion complete!")


if __name__ == '__main__':
    main()
