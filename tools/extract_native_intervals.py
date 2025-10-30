#!/usr/bin/env python3
"""
Извлечение ТОЧНЫХ нативных интервалов Чебышёва из SPK файлов.
Читает сырую структуру DAF напрямую без полагания на документацию.
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


def read_daf_summary(file_path: str) -> Dict[int, List[float]]:
    """
    Читает сырую структуру DAF и извлекает интервалы Чебышёва.

    Структура SPK Type 2 (Chebyshev):
    - Каждый сегмент содержит массив коэффициентов
    - В конце массива идёт directory с временными границами
    - Анализируем разницу между последовательными временными метками
    """

    intervals_by_body = {}

    with open(file_path, 'rb') as f:
        # Читаем File Record (первые 1024 байта)
        file_record = f.read(1024)

        # Проверяем формат (должно быть 'DAF/SPK')
        format_id = file_record[:8].decode('ascii', errors='ignore').strip()
        if not format_id.startswith('DAF/'):
            print(f"⚠️  Not a DAF file: {format_id}")
            return intervals_by_body

        # Определяем endianness
        # Байты 88-91 содержат ND (number of double precision)
        # Байты 92-95 содержат NI (number of integers)
        nd = struct.unpack('>i', file_record[88:92])[0]
        ni = struct.unpack('>i', file_record[92:96])[0]

        # Если значения слишком большие, пробуем little-endian
        if nd > 100 or ni > 100:
            nd = struct.unpack('<i', file_record[88:92])[0]
            ni = struct.unpack('<i', file_record[92:96])[0]
            endian = '<'
        else:
            endian = '>'

        print(f"File format: {format_id}, ND={nd}, NI={ni}, endian={'little' if endian == '<' else 'big'}")

        # Forward record pointer (байты 76-79)
        fward_ptr = struct.unpack(f'{endian}i', file_record[76:80])[0]

        # Backward record pointer (байты 80-83)
        bward_ptr = struct.unpack(f'{endian}i', file_record[80:84])[0]

        print(f"Forward ptr: {fward_ptr}, Backward ptr: {bward_ptr}")

        # Читаем summary records
        # Каждый summary record = 1024 bytes
        # Первые 24 байта - next/prev pointers
        # Остальное - summary entries

        current_record = 2  # Первый summary record после file record

        while current_record <= bward_ptr:
            f.seek((current_record - 1) * 1024)
            summary_record = f.read(1024)

            # Next pointer
            next_ptr = struct.unpack(f'{endian}d', summary_record[0:8])[0]
            # Prev pointer
            prev_ptr = struct.unpack(f'{endian}d', summary_record[8:16])[0]
            # Number of summaries in this record
            n_summaries = int(struct.unpack(f'{endian}d', summary_record[16:24])[0])

            if n_summaries == 0:
                break

            # Каждый summary: ND doubles + NI integers + 2 integers (begin/end addresses)
            summary_size = (nd + ni + 2) * 8  # все в doubles

            offset = 24  # После заголовка

            for i in range(n_summaries):
                if offset + summary_size > 1024:
                    break

                summary_data = summary_record[offset:offset + summary_size]

                # Первые ND doubles - временной диапазон
                start_time = struct.unpack(f'{endian}d', summary_data[0:8])[0]
                end_time = struct.unpack(f'{endian}d', summary_data[8:16])[0]

                # Следующие NI integers - target, center, frame, type, begin_addr, end_addr
                # Они хранятся как doubles!
                target_offset = nd * 8
                target_id = int(struct.unpack(f'{endian}d', summary_data[target_offset:target_offset+8])[0])

                center_id = int(struct.unpack(f'{endian}d', summary_data[target_offset+8:target_offset+16])[0])

                frame_id = int(struct.unpack(f'{endian}d', summary_data[target_offset+16:target_offset+24])[0])

                spk_type = int(struct.unpack(f'{endian}d', summary_data[target_offset+24:target_offset+32])[0])

                begin_addr = int(struct.unpack(f'{endian}d', summary_data[target_offset+32:target_offset+40])[0])

                end_addr = int(struct.unpack(f'{endian}d', summary_data[target_offset+40:target_offset+48])[0])

                # Читаем данные сегмента для Type 2 (Chebyshev)
                if spk_type == 2:
                    # Читаем последние записи сегмента - там directory
                    segment_size = end_addr - begin_addr + 1

                    # Переходим к началу сегмента данных
                    f.seek((begin_addr - 1) * 8)

                    # Читаем первые несколько double для определения структуры
                    first_doubles = struct.unpack(f'{endian}10d', f.read(80))

                    # first_doubles[0] = начало первого интервала (TDB seconds)
                    # first_doubles[1] = конец первого интервала
                    # first_doubles[2] = rsize (количество double в одной записи)

                    interval_start = first_doubles[0]
                    interval_end = first_doubles[1]
                    interval_length_sec = interval_end - interval_start
                    interval_length_days = interval_length_sec / 86400.0

                    if target_id not in intervals_by_body:
                        intervals_by_body[target_id] = []

                    intervals_by_body[target_id].append(interval_length_days)

                offset += summary_size

            if next_ptr == 0:
                break

            current_record = int(next_ptr)

    return intervals_by_body


def analyze_spk_file(file_path: str):
    """Анализирует SPK файл и выводит нативные интервалы."""

    print(f"\n{'='*80}")
    print(f"Analyzing: {file_path}")
    print(f"{'='*80}\n")

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return None

    try:
        intervals = read_daf_summary(file_path)

        if not intervals:
            print("⚠️  No Chebyshev intervals found")
            return None

        print(f"\nFound {len(intervals)} bodies with interval data:\n")

        results = {}

        for body_id in sorted(intervals.keys()):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")
            interval_list = intervals[body_id]

            # Берём первый интервал (обычно все одинаковые для одного тела)
            native_interval = interval_list[0]

            # Проверяем, все ли интервалы одинаковые
            all_same = all(abs(i - native_interval) < 0.01 for i in interval_list)

            print(f"Body {body_id:10d}: {body_name:25s} - {native_interval:8.2f} days", end='')

            if not all_same:
                min_i = min(interval_list)
                max_i = max(interval_list)
                print(f"  (range: {min_i:.2f} - {max_i:.2f})")
            else:
                print()

            results[body_id] = {
                'name': body_name,
                'interval_days': native_interval,
                'all_same': all_same
            }

        return results

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_files(file_paths: List[str]):
    """Сравнивает интервалы в нескольких файлах."""

    all_results = {}

    for file_path in file_paths:
        results = analyze_spk_file(file_path)
        if results:
            file_name = Path(file_path).name
            all_results[file_name] = results

    if len(all_results) > 1:
        print(f"\n{'='*80}")
        print("COMPARISON ACROSS FILES")
        print(f"{'='*80}\n")

        # Собираем все уникальные body_id
        all_bodies = set()
        for results in all_results.values():
            all_bodies.update(results.keys())

        print(f"{'Body':<30s} ", end='')
        for file_name in all_results.keys():
            print(f"{file_name[:20]:>20s} ", end='')
        print()
        print("-" * 80)

        for body_id in sorted(all_bodies):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")
            print(f"{body_id:3d} {body_name:25s} ", end='')

            for file_name, results in all_results.items():
                if body_id in results:
                    interval = results[body_id]['interval_days']
                    print(f"{interval:8.2f} days       ", end='')
                else:
                    print(f"{'---':>20s} ", end='')
            print()

        # Генерируем рекомендованную конфигурацию
        print(f"\n{'='*80}")
        print("RECOMMENDED CONFIGURATION (JSON)")
        print(f"{'='*80}\n")

        print('"body_intervals": {')

        # Берём интервалы из первого файла (или усредняем)
        first_results = list(all_results.values())[0]

        for body_id in sorted(all_bodies):
            body_name = BODY_NAMES.get(body_id, f"Body {body_id}")

            # Собираем интервалы из всех файлов
            intervals_from_files = []
            for results in all_results.values():
                if body_id in results:
                    intervals_from_files.append(results[body_id]['interval_days'])

            if intervals_from_files:
                # Берём минимальный (наиболее детальный)
                recommended = min(intervals_from_files)

                print(f'  "{body_id}": {{')
                print(f'    "name": "{body_name}",')
                print(f'    "interval_days": {recommended:.1f},')
                print(f'    "comment": "Native from source files"')
                print(f'  }},')

        print('}')


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_native_intervals.py <spk_file1> [spk_file2 ...]")
        print("\nExample:")
        print("  python extract_native_intervals.py data/ephemerides/jpl/de431/de431_part-1.bsp")
        print("  python extract_native_intervals.py data/ephemerides/*/**.bsp")
        sys.exit(1)

    file_paths = sys.argv[1:]

    if len(file_paths) == 1:
        analyze_spk_file(file_paths[0])
    else:
        compare_files(file_paths)


if __name__ == "__main__":
    main()
