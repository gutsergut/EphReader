#!/usr/bin/env python3
"""
Swiss Ephemeris .se1 → .eph Converter (via PHP FFI)
Использует PHP FFI для чтения Swiss Ephemeris и конвертирует в .eph формат
"""

import struct
import subprocess
import json
import sys
from pathlib import Path
from typing import List, Tuple
import numpy as np
from numpy.polynomial.chebyshev import Chebyshev

class SwissEphFFIConverter:
    """Конвертер Swiss Ephemeris через PHP FFI"""

    # NAIF ID → Swiss Ephemeris ID mapping
    NAIF_TO_SWEPH = {
        1: 2,    # Mercury
        2: 3,    # Venus
        3: 0,    # Earth (Sun-centric → geocentric)
        4: 4,    # Mars
        5: 5,    # Jupiter
        6: 6,    # Saturn
        7: 7,    # Uranus
        8: 8,    # Neptune
        9: 9,    # Pluto
        10: 0,   # Sun
        301: 1,  # Moon
        399: 13, # Earth (barycenter)
    }

    def __init__(self, dll_path: str, ephe_path: str, output_path: str,
                 body_ids: List[int], interval_days: float = 16.0, frame: str = 'geocentric'):
        self.dll_path = Path(dll_path)
        self.ephe_path = Path(ephe_path)
        self.output_path = Path(output_path)
        self.body_ids = body_ids
        self.interval_days = interval_days
        self.frame = frame  # 'geocentric' or 'barycentric'

        if frame not in ['geocentric', 'barycentric']:
            raise ValueError(f"Invalid frame: {frame}. Use 'geocentric' or 'barycentric'")

        if not self.dll_path.exists():
            raise FileNotFoundError(f"DLL not found: {self.dll_path}")
        if not self.ephe_path.exists():
            raise FileNotFoundError(f"Ephemeris path not found: {self.ephe_path}")

    def compute_position_ffi(self, body_id: int, jd: float) -> Tuple[np.ndarray, np.ndarray]:
        """Вычисляет позицию через PHP FFI"""
        sweph_id = self.NAIF_TO_SWEPH.get(body_id)
        if sweph_id is None:
            raise ValueError(f"Body {body_id} not supported in Swiss Ephemeris")

        # Используем standalone PHP скрипт
        standalone_script = Path(__file__).parent / 'swisseph_standalone.php'

        result = subprocess.run(
            ['php', str(standalone_script), str(body_id), str(jd), self.frame],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"PHP script failed: {result.stderr}")

        data = json.loads(result.stdout)
        if 'error' in data:
            raise RuntimeError(f"FFI error: {data['error']}")

        pos = np.array(data['pos'], dtype=np.float64)
        vel = np.array(data['vel'], dtype=np.float64)
        return pos, vel

    def fit_chebyshev(self, jd_start: float, jd_end: float, body_id: int,
                     degree: int = 7) -> np.ndarray:
        """Подгоняет полиномы Чебышёва к данным Swiss Ephemeris"""
        # Защита от нулевого интервала
        if abs(jd_end - jd_start) < 1e-10:
            jd_end = jd_start + 0.1  # Минимальный интервал

        # Создаём узлы интерполяции (Chebyshev nodes для лучшей точности)
        n_samples = degree + 3
        t = np.cos(np.pi * np.arange(n_samples) / (n_samples - 1))  # [-1, 1]
        jd_samples = jd_start + (jd_end - jd_start) * (t + 1) / 2

        positions = []
        velocities = []

        for jd in jd_samples:
            pos, vel = self.compute_position_ffi(body_id, jd)
            positions.append(pos)
            velocities.append(vel)

        positions = np.array(positions)
        velocities = np.array(velocities)

        # Нормализуем время в [-1, 1]
        t_norm = 2 * (jd_samples - jd_start) / (jd_end - jd_start) - 1

        # Подгоняем полиномы для X, Y, Z
        coeffs = np.zeros((3, degree + 1))
        for i in range(3):
            try:
                poly = Chebyshev.fit(t_norm, positions[:, i], degree)
                coeffs[i] = poly.coef
            except np.linalg.LinAlgError:
                # Если SVD не сходится, используем меньший degree
                poly = Chebyshev.fit(t_norm, positions[:, i], degree - 2)
                # Дополняем нулями до нужного размера
                coeffs[i, :len(poly.coef)] = poly.coef

        return coeffs.flatten()

    def convert(self, start_jd: float = 2451545.0, end_jd: float = 2488070.0):
        """Конвертирует Swiss Ephemeris в .eph формат"""
        print(f"🔄 Converting Swiss Ephemeris to {self.output_path}")
        print(f"   Time range: JD {start_jd} - {end_jd}")
        print(f"   Interval: {self.interval_days} days")
        print(f"   Bodies: {self.body_ids}")
        print(f"   Frame: {self.frame}")

        degree = 7
        num_intervals = int((end_jd - start_jd) / self.interval_days) + 1

        with open(self.output_path, 'wb') as f:
            # Header (512 bytes)
            header = bytearray(512)
            header[0:4] = b'EPH\0'
            struct.pack_into('<I', header, 4, 1)  # version
            struct.pack_into('<I', header, 8, len(self.body_ids))  # num_bodies
            struct.pack_into('<I', header, 12, num_intervals)  # num_intervals
            struct.pack_into('<d', header, 16, self.interval_days)
            struct.pack_into('<d', header, 24, start_jd)
            struct.pack_into('<d', header, 32, end_jd)
            struct.pack_into('<I', header, 40, degree)
            f.write(header)

            # Body table
            offset = 512 + len(self.body_ids) * 32 + num_intervals * 16
            for body_id in self.body_ids:
                body_name = f"Body_{body_id}".ljust(24, '\0')[:24]
                f.write(struct.pack('<i', body_id))
                f.write(body_name.encode('ascii'))
                f.write(struct.pack('<Q', offset))
                offset += num_intervals * 3 * (degree + 1) * 8

            # Interval index
            for i in range(num_intervals):
                jd_start = start_jd + i * self.interval_days
                jd_end = min(jd_start + self.interval_days, end_jd)
                f.write(struct.pack('<dd', jd_start, jd_end))

            # Coefficients
            for body_id in self.body_ids:
                print(f"   Processing body {body_id}...", end=' ')
                for i in range(num_intervals):
                    jd_start = start_jd + i * self.interval_days
                    jd_end = min(jd_start + self.interval_days, end_jd)

                    coeffs = self.fit_chebyshev(jd_start, jd_end, body_id, degree)
                    f.write(struct.pack(f'<{len(coeffs)}d', *coeffs))

                    if (i + 1) % 10 == 0:
                        print(f"{i+1}/{num_intervals}", end=' ', flush=True)
                print("✅")

        file_size = self.output_path.stat().st_size
        print(f"\n✅ Conversion complete!")
        print(f"   Output: {self.output_path}")
        print(f"   Size: {file_size / 1024 / 1024:.2f} MB")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert Swiss Ephemeris to .eph format via FFI')
    parser.add_argument('--dll', default='vendor/swisseph/swedll64.dll',
                       help='Path to swedll64.dll')
    parser.add_argument('--ephe', default='ephe',
                       help='Path to ephemeris directory with .se1 files')
    parser.add_argument('--output', required=True,
                       help='Output .eph file path')
    parser.add_argument('--bodies', default='1,2,3,4,5,6,7,8,9,10,301,399',
                       help='Comma-separated NAIF body IDs')
    parser.add_argument('--interval', type=float, default=16.0,
                       help='Interval in days (default: 16.0)')
    parser.add_argument('--start-jd', type=float, default=2451545.0,
                       help='Start Julian Date (default: J2000.0)')
    parser.add_argument('--end-jd', type=float, default=2488070.0,
                       help='End Julian Date (default: J2100.0)')
    parser.add_argument('--frame', default='geocentric', choices=['geocentric', 'barycentric'],
                       help='Coordinate frame (default: geocentric)')

    args = parser.parse_args()

    body_ids = [int(x.strip()) for x in args.bodies.split(',')]

    converter = SwissEphFFIConverter(
        dll_path=args.dll,
        ephe_path=args.ephe,
        output_path=args.output,
        body_ids=body_ids,
        interval_days=args.interval,
        frame=args.frame
    )

    converter.convert(start_jd=args.start_jd, end_jd=args.end_jd)


if __name__ == '__main__':
    main()
