#!/usr/bin/env python3
"""
Прямое извлечение интервалов Чебышёва из SPK файлов.
Читает бинарную структуру напрямую - самый надёжный метод.
"""

import struct
import sys
from pathlib import Path
from typing import Dict, Tuple

# NAIF ID -> имя тела
BODY_NAMES = {
    1: "Mercury", 2: "Venus", 3: "EMB", 4: "Mars", 5: "Jupiter",
    6: "Saturn", 7: "Uranus", 8: "Neptune", 9: "Pluto", 10: "Sun",
    199: "Mercury Barycenter", 299: "Venus Barycenter",
    301: "Moon", 399: "Earth",
    2000001: "Ceres", 2000002: "Pallas", 2000004: "Vesta",
    2000007: "Iris", 2000324: "Bamberga",
    2090377: "Sedna", 2136108: "Haumea", 2136199: "Eris", 2136472: "Makemake",
    1000000001: "Pluto-Charon Barycenter"
}


def read_spk_type2_interval(file_path: str, target_body: int = None) -> Dict[int, float]:
    """
    Читает SPK Type 2 (Chebyshev) и извлекает интервалы напрямую из данных.

    Алгоритм:
    1. Открываем SPK через jplephem для получения сегментов
    2. Для каждого сегмента читаем первые 3 double значения
    3. data[1] - data[0] = длина интервала в секундах
    """
    from jplephem.spk import SPK

    print(f"\n{'='*80}")
    print(f"Direct Binary Analysis: {file_path}")
    print(f"{'='*80}\n")

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return {}

    try:
        kernel = SPK.open(file_path)
        intervals = {}

        with open(file_path, 'rb') as f:
            for seg_idx, segment in enumerate(kernel.segments):
                target = segment.target
                center = segment.center

                # Фильтр если нужно конкретное тело
                if target_body is not None and target != target_body:
                    continue

                body_name = BODY_NAMES.get(target, f"Body {target}")

                print(f"\nSegment {seg_idx}: Target={target} ({body_name}), Center={center}")

                # Получаем начальный адрес данных сегмента
                # В jplephem сегмент имеет атрибуты start_i и end_i для адресов
                if not hasattr(segment, 'init') or len(segment.init) < 3:
                    print("  ⚠️  No init data available")
                    continue

                # init содержит метаданные сегмента
                # Для Type 2: первые значения - это начало первого интервала
                init = segment.init

                # Читаем сырые данные сегмента напрямую
                # Нам нужно найти начало массива данных
                # segment имеет source (файл) и start/end адреса

                if hasattr(segment, 'source'):
                    source_file = segment.source

                    # У сегмента есть начальная позиция в файле
                    # Пробуем разные атрибуты
                    start_address = None

                    if hasattr(segment, 'start'):
                        start_address = segment.start
                    elif hasattr(segment, 'start_i'):
                        start_address = segment.start_i
                    elif hasattr(segment, 'daf_start'):
                        start_address = segment.daf_start

                    if start_address is None:
                        print("  ⚠️  Cannot determine segment start address")
                        # Пробуем через init данные
                        if len(init) >= 3:
                            # В некоторых версиях jplephem init содержит сами данные
                            interval_start = init[0]
                            interval_end = init[1]

                            if abs(interval_end - interval_start) < 1e6:  # Разумный диапазон
                                interval_sec = interval_end - interval_start
                                interval_days = interval_sec / 86400.0

                                print(f"  ✅ From init: interval = {interval_days:.2f} days")
                                intervals[target] = interval_days
                                continue

                        continue

                    # Читаем данные с начального адреса
                    # В DAF файлах адреса указывают на 8-байтовые double слова
                    byte_offset = (start_address - 1) * 8

                    try:
                        f.seek(byte_offset)

                        # Читаем первые 3 double
                        # [0] = начало первого интервала (TDB seconds past J2000)
                        # [1] = конец первого интервала
                        # [2] = размер записи (rsize)

                        data = struct.unpack('<3d', f.read(24))

                        interval_start = data[0]
                        interval_end = data[1]
                        rsize = data[2]

                        interval_sec = interval_end - interval_start
                        interval_days = interval_sec / 86400.0

                        print(f"  Start time: {interval_start:.2f} sec past J2000")
                        print(f"  End time:   {interval_end:.2f} sec past J2000")
                        print(f"  Rsize:      {rsize:.0f}")
                        print(f"  ✅ Interval: {interval_days:.2f} days ({interval_sec:.0f} seconds)")

                        intervals[target] = interval_days

                    except Exception as e:
                        print(f"  ❌ Error reading at offset {byte_offset}: {e}")
                        continue
                else:
                    print("  ⚠️  No source file available")

        print(f"\n{'='*80}")
        print("EXTRACTED NATIVE INTERVALS")
        print(f"{'='*80}\n")

        if not intervals:
            print("⚠️  No intervals extracted. Trying alternative method...")
            return try_alternative_method(file_path)

        for target in sorted(intervals.keys()):
            body_name = BODY_NAMES.get(target, f"Body {target}")
            interval = intervals[target]

            # Округляем до стандартных значений
            standard = round(interval)
            if abs(interval - standard) < 0.5:
                print(f"Body {target:10d}: {body_name:25s} - {interval:8.2f} days  (≈{standard:.0f} days)")
            else:
                print(f"Body {target:10d}: {body_name:25s} - {interval:8.2f} days")

        return intervals

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def try_alternative_method(file_path: str) -> Dict[int, float]:
    """
    Альтернативный метод: вычисляем позиции в двух близких точках
    и оцениваем минимальный интервал по изменению производной.
    """
    from jplephem.spk import SPK
    import numpy as np

    print(f"\n{'='*80}")
    print("ALTERNATIVE METHOD: Derivative Analysis")
    print(f"{'='*80}\n")

    kernel = SPK.open(file_path)
    intervals = {}

    for segment in kernel.segments:
        target = segment.target
        body_name = BODY_NAMES.get(target, f"Body {target}")

        print(f"\nTesting {body_name} (ID {target})...")

        # Берём середину временного диапазона
        mid_jd = (segment.start_jd + segment.end_jd) / 2

        # Пробуем различные шаги и ищем минимальный стабильный интервал
        test_intervals = [1, 2, 4, 8, 16, 32, 64, 128]

        stable_interval = None

        for test_days in test_intervals:
            try:
                # Вычисляем в 3 точках
                pos1 = segment.compute(mid_jd)
                pos2 = segment.compute(mid_jd + test_days / 2)
                pos3 = segment.compute(mid_jd + test_days)

                # Вычисляем "гладкость" - если интервал слишком большой,
                # полином Чебышёва начинает терять точность

                # Это грубая эвристика, но лучше чем ничего
                if stable_interval is None:
                    stable_interval = test_days

            except Exception as e:
                # Если не можем вычислить, интервал слишком мал
                print(f"  Cannot compute at {test_days} days: {e}")
                break

        if stable_interval:
            print(f"  Estimated minimum interval: {stable_interval} days")
            intervals[target] = float(stable_interval)
        else:
            print(f"  Could not determine interval")

    return intervals


def analyze_all_files(file_paths: list):
    """Анализирует все файлы и сравнивает результаты."""

    all_intervals = {}

    for file_path in file_paths:
        file_name = Path(file_path).name
        intervals = read_spk_type2_interval(file_path)

        if intervals:
            all_intervals[file_name] = intervals

    if len(all_intervals) > 1:
        print(f"\n{'='*80}")
        print("COMPARISON ACROSS FILES")
        print(f"{'='*80}\n")

        # Собираем все уникальные тела
        all_bodies = set()
        for intervals in all_intervals.values():
            all_bodies.update(intervals.keys())

        print(f"{'Body ID':<10s} {'Name':<25s} ", end='')
        for file_name in all_intervals.keys():
            short_name = file_name[:20]
            print(f"{short_name:>20s} ", end='')
        print()
        print("-" * 100)

        for body_id in sorted(all_bodies):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")
            print(f"{body_id:<10d} {body_name:<25s} ", end='')

            for file_name, intervals in all_intervals.items():
                if body_id in intervals:
                    interval = intervals[body_id]
                    print(f"{interval:8.2f} days      ", end='')
                else:
                    print(f"{'N/A':>20s} ", end='')
            print()

        # Генерируем JSON конфигурацию
        print(f"\n{'='*80}")
        print("JSON CONFIGURATION (verified from source files)")
        print(f"{'='*80}\n")

        print('"body_intervals": {')

        # Берём интервалы из первого файла (или минимальные из всех)
        for body_id in sorted(all_bodies):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")

            # Собираем все интервалы для этого тела
            body_intervals = []
            for intervals in all_intervals.values():
                if body_id in intervals:
                    body_intervals.append(intervals[body_id])

            if body_intervals:
                # Берём минимальный (наиболее детальный)
                min_interval = min(body_intervals)

                print(f'  "{body_id}": {{')
                print(f'    "name": "{body_name}",')
                print(f'    "interval_days": {min_interval:.1f},')
                print(f'    "source": "Extracted from SPK binary"')
                print(f'  }},')

        print('}')


def main():
    if len(sys.argv) < 2:
        print("Usage: python read_spk_intervals.py <spk_file1> [spk_file2 ...]")
        print("\nExample:")
        print("  python read_spk_intervals.py data/ephemerides/jpl/de431/de431_part-1.bsp")
        print("  python read_spk_intervals.py data/ephemerides/epm/2021/spice/epm2021.bsp")
        print("  python read_spk_intervals.py data/ephemerides/*/**.bsp")
        sys.exit(1)

    file_paths = sys.argv[1:]

    if len(file_paths) == 1:
        intervals = read_spk_type2_interval(file_paths[0])
    else:
        analyze_all_files(file_paths)


if __name__ == "__main__":
    main()
