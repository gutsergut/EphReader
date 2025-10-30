#!/usr/bin/env python3
"""
ПРЯМОЕ чтение интервалов Чебышёва из SPK файлов без внешних библиотек.
Работает с сырой структурой DAF/SPK напрямую.
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


def read_chebyshev_intervals_raw(file_path: str) -> Dict[int, float]:
    """
    Читает SPK файл как сырой бинарник и извлекает интервалы Чебышёва.

    Метод:
    1. Находим начало каждого сегмента данных через DAF структуру
    2. Читаем первые double значения - это времена начала/конца интервалов
    3. Разница = длина интервала
    """

    print(f"\n{'='*80}")
    print(f"RAW BINARY ANALYSIS: {file_path}")
    print(f"{'='*80}\n")

    intervals = {}

    with open(file_path, 'rb') as f:
        # Читаем File Record
        f.seek(0)
        file_record = f.read(1024)

        # Формат файла
        format_str = file_record[:7].decode('ascii', errors='ignore')
        print(f"Format: {format_str}")

        # Определяем endianness - пробуем оба варианта
        endian = '<'  # little-endian для большинства современных файлов

        # Читаем ND (number of doubles in summary) и NI (number of integers)
        nd_offset = 8  # После 'DAF/SPK '
        try:
            nd = struct.unpack(f'{endian}i', file_record[nd_offset:nd_offset+4])[0]
            ni = struct.unpack(f'{endian}i', file_record[nd_offset+4:nd_offset+8])[0]

            if nd > 100 or ni > 100:  # Неразумные значения
                endian = '>'
                nd = struct.unpack(f'{endian}i', file_record[nd_offset:nd_offset+4])[0]
                ni = struct.unpack(f'{endian}i', file_record[nd_offset+4:nd_offset+8])[0]
        except:
            # Пробуем другие офсеты
            nd, ni = 2, 6  # Стандартные значения для SPK

        print(f"Summary format: ND={nd}, NI={ni}, endian={'little' if endian == '<' else 'big'}")

        # Forward pointer (указатель на первую Summary Record)
        fward_offset = 76  # Стандартный офсет в DAF
        try:
            fward = struct.unpack(f'{endian}i', file_record[fward_offset:fward_offset+4])[0]
            bward = struct.unpack(f'{endian}i', file_record[fward_offset+4:fward_offset+8])[0]
        except:
            fward, bward = 2, 2

        print(f"Summary records: {fward} to {bward}\n")

        # Читаем Summary Records
        for record_num in range(fward, bward + 1):
            f.seek((record_num - 1) * 1024)
            summary_record = f.read(1024)

            # Первые 24 байта - заголовок (next, prev, n_summaries)
            try:
                next_rec = struct.unpack(f'{endian}d', summary_record[0:8])[0]
                prev_rec = struct.unpack(f'{endian}d', summary_record[8:16])[0]
                n_summaries = int(struct.unpack(f'{endian}d', summary_record[16:24])[0])
            except:
                continue

            if n_summaries == 0 or n_summaries > 100:
                continue

            print(f"Summary Record {record_num}: {n_summaries} segments")

            # Размер одного summary
            summary_size = (nd + (ni + 2)) * 8  # все как doubles
            offset = 24

            for seg_idx in range(n_summaries):
                if offset + summary_size > 1024:
                    break

                summary = summary_record[offset:offset + summary_size]

                try:
                    # Первые nd doubles - временной диапазон
                    seg_start = struct.unpack(f'{endian}d', summary[0:8])[0]
                    seg_end = struct.unpack(f'{endian}d', summary[8:16])[0]

                    # После nd doubles идут ni integers (как doubles)
                    int_offset = nd * 8
                    target = int(struct.unpack(f'{endian}d', summary[int_offset:int_offset+8])[0])
                    center = int(struct.unpack(f'{endian}d', summary[int_offset+8:int_offset+16])[0])
                    frame = int(struct.unpack(f'{endian}d', summary[int_offset+16:int_offset+24])[0])
                    seg_type = int(struct.unpack(f'{endian}d', summary[int_offset+24:int_offset+32])[0])
                    begin_addr = int(struct.unpack(f'{endian}d', summary[int_offset+32:int_offset+40])[0])
                    end_addr = int(struct.unpack(f'{endian}d', summary[int_offset+40:int_offset+48])[0])

                    body_name = BODY_NAMES.get(target, f"Body {target}")

                    print(f"  Segment {seg_idx}: Target={target:4d} ({body_name:20s}), "
                          f"Type={seg_type}, Addresses={begin_addr}-{end_addr}")

                    # Читаем данные сегмента
                    if seg_type in [2, 3, 20, 21]:  # Chebyshev types
                        # Переходим к началу данных
                        data_offset = (begin_addr - 1) * 8
                        f.seek(data_offset)

                        # Читаем первые 10 doubles
                        try:
                            first_data = struct.unpack(f'{endian}10d', f.read(80))

                            # first_data[0] = начало первого интервала
                            # first_data[1] = конец первого интервала
                            interval_start_sec = first_data[0]
                            interval_end_sec = first_data[1]

                            interval_sec = interval_end_sec - interval_start_sec
                            interval_days = interval_sec / 86400.0

                            if 0.1 < interval_days < 1000:  # Разумный диапазон
                                print(f"    ✅ Interval: {interval_days:.2f} days ({interval_sec:.0f} sec)")

                                if target not in intervals:
                                    intervals[target] = interval_days
                                else:
                                    # Берём минимальный
                                    intervals[target] = min(intervals[target], interval_days)
                            else:
                                print(f"    ⚠️  Unreasonable interval: {interval_days:.2f} days")

                        except Exception as e:
                            print(f"    ❌ Cannot read data: {e}")

                except Exception as e:
                    print(f"  ⚠️  Error reading summary {seg_idx}: {e}")

                offset += summary_size

            print()

    return intervals


def analyze_file(file_path: str):
    """Анализирует один файл."""

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return {}

    intervals = read_chebyshev_intervals_raw(file_path)

    if not intervals:
        print("⚠️  No intervals extracted!")
        return {}

    print(f"\n{'='*80}")
    print("EXTRACTED INTERVALS")
    print(f"{'='*80}\n")

    for target in sorted(intervals.keys()):
        body_name = BODY_NAMES.get(target, f"Body {target}")
        interval = intervals[target]

        # Округляем до стандартных значений
        standard_intervals = [8, 16, 32, 64, 128, 256]
        closest = min(standard_intervals, key=lambda x: abs(x - interval))

        if abs(interval - closest) < 1.0:
            print(f"Body {target:10d}: {body_name:25s} - {interval:8.2f} days  ≈ {closest} days ✅")
        else:
            print(f"Body {target:10d}: {body_name:25s} - {interval:8.2f} days")

    return intervals


def compare_files(file_paths: List[str]):
    """Сравнивает интервалы из нескольких файлов."""

    all_intervals = {}

    for file_path in file_paths:
        file_name = Path(file_path).name
        intervals = analyze_file(file_path)
        if intervals:
            all_intervals[file_name] = intervals

    if len(all_intervals) > 1:
        print(f"\n\n{'='*80}")
        print("COMPARISON")
        print(f"{'='*80}\n")

        all_bodies = set()
        for intervals in all_intervals.values():
            all_bodies.update(intervals.keys())

        print(f"{'Body':^35s} | ", end='')
        for fname in all_intervals.keys():
            print(f"{fname[:18]:^20s} | ", end='')
        print()
        print("-" * (35 + 23 * len(all_intervals)))

        for body_id in sorted(all_bodies):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")
            name_str = f"{body_id:3d} {body_name}"
            print(f"{name_str:<35s} | ", end='')

            for fname, intervals in all_intervals.items():
                if body_id in intervals:
                    interval = intervals[body_id]
                    print(f"{interval:8.2f} days      | ", end='')
                else:
                    print(f"{'N/A':^20s} | ", end='')
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python raw_spk_reader.py <spk_file1> [spk_file2 ...]")
        print("\nExamples:")
        print("  python raw_spk_reader.py data/ephemerides/epm/2021/spice/epm2021.bsp")
        print("  python raw_spk_reader.py data/ephemerides/jpl/de431/de431_part-1.bsp")
        print("  python raw_spk_reader.py data/ephemerides/*/**.bsp")
        sys.exit(1)

    file_paths = sys.argv[1:]

    if len(file_paths) == 1:
        analyze_file(file_paths[0])
    else:
        compare_files(file_paths)


if __name__ == "__main__":
    main()
