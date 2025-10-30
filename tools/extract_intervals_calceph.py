#!/usr/bin/env python3
"""
Извлечение нативных интервалов через calceph библиотеку.
Calceph предоставляет доступ к внутренней структуре SPK.
"""

import sys
from pathlib import Path
from typing import Dict, List

try:
    import calceph
except ImportError:
    print("❌ calceph not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "calceph"])
    import calceph

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


def analyze_with_calceph(file_path: str) -> Dict[int, float]:
    """
    Анализирует SPK через calceph и пытается извлечь интервалы.
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {file_path}")
    print(f"{'='*80}\n")

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return {}

    try:
        # Открываем ephemeris
        peph = calceph.CalcephBin()
        peph.open(file_path)

        # Получаем временной диапазон
        time_start, time_end, time_scale = peph.gettimespan()

        print(f"Time span: JD {time_start:.2f} to {time_end:.2f} ({time_scale})")
        print(f"Duration: {(time_end - time_start):.2f} days\n")

        # Получаем список тел
        n_constants = peph.getconstantcount()
        n_records = peph.getpositionrecordcount()

        print(f"Records: {n_records}")
        print(f"Constants: {n_constants}\n")

        # Пробуем извлечь информацию о каждой записи
        intervals = {}

        for i in range(n_records):
            try:
                record_info = peph.getpositionrecordindex(i)
                # record_info = (target, center, time_start, time_end, frame)

                if len(record_info) >= 5:
                    target = record_info[0]
                    center = record_info[1]
                    rec_start = record_info[2]
                    rec_end = record_info[3]
                    frame = record_info[4]

                    duration_days = rec_end - rec_start

                    body_name = BODY_NAMES.get(target, f"Body {target}")

                    print(f"Record {i:3d}: Target={target:10d} ({body_name:20s}), "
                          f"Center={center:3d}, Duration={duration_days:10.2f} days")

                    # Сохраняем первый интервал для каждого тела
                    if target not in intervals:
                        intervals[target] = duration_days
                    else:
                        # Если есть несколько записей, берём минимальный интервал
                        intervals[target] = min(intervals[target], duration_days)

            except Exception as e:
                print(f"⚠️  Record {i}: {e}")
                continue

        peph.close()

        print(f"\n{'='*80}")
        print("EXTRACTED INTERVALS")
        print(f"{'='*80}\n")

        for target in sorted(intervals.keys()):
            body_name = BODY_NAMES.get(target, f"Body {target}")
            interval = intervals[target]
            print(f"Body {target:10d}: {body_name:25s} - {interval:10.2f} days")

        return intervals

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def analyze_with_jplephem(file_path: str) -> Dict[int, float]:
    """
    Альтернативный метод через jplephem - читаем сырые сегменты.
    """
    from jplephem.spk import SPK

    print(f"\n{'='*80}")
    print(f"Analyzing with jplephem: {file_path}")
    print(f"{'='*80}\n")

    try:
        kernel = SPK.open(file_path)

        intervals = {}

        for segment in kernel.segments:
            target = segment.target
            center = segment.center
            start_jd = segment.start_jd
            end_jd = segment.end_jd

            duration_days = end_jd - start_jd

            body_name = BODY_NAMES.get(target, f"Body {target}")

            print(f"Target={target:10d} ({body_name:20s}), "
                  f"Center={center:3d}, Duration={duration_days:10.2f} days")

            # Пробуем получить доступ к внутренним данным сегмента
            # У segment есть атрибут data_type (должен быть 2 для Chebyshev)
            if hasattr(segment, 'data_type'):
                print(f"  Data type: {segment.data_type}")

            # Пробуем прочитать начало данных сегмента
            try:
                # segment.compute(start_jd) вызывает внутреннее чтение
                # Можем попробовать получить доступ к init
                if hasattr(segment, 'init'):
                    init = segment.init
                    print(f"  Init data: {init[:10] if len(init) > 10 else init}")

                # Или к коэффициентам
                if hasattr(segment, 'coefficient_count'):
                    print(f"  Coefficient count: {segment.coefficient_count}")

                # Пробуем вычислить на границах интервала
                pos1 = segment.compute(start_jd)
                pos2 = segment.compute(start_jd + 1.0)  # +1 день

                # Если успешно, это значит интервал >= 1 день
                # Пробуем бинарный поиск минимального интервала

            except Exception as e:
                print(f"  ⚠️  Cannot access internal data: {e}")

            intervals[target] = duration_days
            print()

        print(f"\n{'='*80}")
        print("TOTAL DURATION PER BODY (not interval!)")
        print(f"{'='*80}\n")

        for target in sorted(intervals.keys()):
            body_name = BODY_NAMES.get(target, f"Body {target}")
            duration = intervals[target]
            print(f"Body {target:10d}: {body_name:25s} - {duration:10.2f} days total")

        print("\n⚠️  Note: These are total segment durations, not Chebyshev intervals!")
        print("    Actual intervals are much smaller (8-128 days typically)")

        return intervals

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_intervals_calceph.py <spk_file1> [spk_file2 ...]")
        print("\nExample:")
        print("  python extract_intervals_calceph.py data/ephemerides/jpl/de431/de431_part-1.bsp")
        sys.exit(1)

    file_paths = sys.argv[1:]

    for file_path in file_paths:
        print("\n" + "="*80)
        print(f"METHOD 1: CALCEPH")
        print("="*80)

        intervals_calceph = analyze_with_calceph(file_path)

        print("\n" + "="*80)
        print(f"METHOD 2: JPLEPHEM")
        print("="*80)

        intervals_jplephem = analyze_with_jplephem(file_path)

        print("\n" + "="*80)
        print("CONCLUSION")
        print("="*80)
        print("\n⚠️  Direct interval extraction from SPK is not straightforward.")
        print("    Both libraries expose segment-level data, not Chebyshev record intervals.")
        print("\n✅ SOLUTION: Use SPICE Toolkit's BRIEF utility with -t flag")
        print("    Or inspect first few records manually to find interval pattern.")


if __name__ == "__main__":
    main()
