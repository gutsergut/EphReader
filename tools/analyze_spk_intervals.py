#!/usr/bin/env python3
"""
Анализ нативных интервалов Чебышёва в SPK файлах через SPICE Toolkit.
Использует утилиту BRIEF из SPICE для получения детальной информации о сегментах.
"""

import subprocess
import sys
import os
import re
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


def run_spice_brief(spk_file: str, cspice_path: str = "vendor/spice/cspice") -> str:
    """
    Запускает SPICE утилиту BRIEF для анализа SPK файла.

    Args:
        spk_file: Путь к SPK файлу
        cspice_path: Путь к CSPICE toolkit

    Returns:
        Вывод команды BRIEF
    """
    brief_exe = os.path.join(cspice_path, "exe", "brief.exe")

    if not os.path.exists(brief_exe):
        raise FileNotFoundError(f"BRIEF executable not found: {brief_exe}")

    if not os.path.exists(spk_file):
        raise FileNotFoundError(f"SPK file not found: {spk_file}")

    # Запускаем BRIEF с опцией -t для подробной информации
    # -c для показа центра координат
    # -n 1000 для показа всех сегментов
    cmd = [brief_exe, "-t", "-c", spk_file]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd()
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running BRIEF: {e}")
        print(f"STDERR: {e.stderr}")
        raise


def parse_brief_output(output: str) -> Dict[int, Dict]:
    """
    Парсит вывод BRIEF для извлечения информации об интервалах.

    Returns:
        Dict[body_id, {
            'name': str,
            'segments': List[{
                'start': float,
                'end': float,
                'interval_length': float (days),
                'num_intervals': int,
                'type': str
            }]
        }]
    """
    bodies = {}
    current_body = None

    # Регулярные выражения для парсинга
    body_pattern = re.compile(r"Body:\s+(\d+)\s+(.+)")
    segment_pattern = re.compile(r"Segment:\s+(\d+)")
    start_pattern = re.compile(r"Start Time:\s+(.+)")
    end_pattern = re.compile(r"End Time:\s+(.+)")
    interval_pattern = re.compile(r"Interval Length:\s+([\d.]+)\s+seconds")
    count_pattern = re.compile(r"Interval Count:\s+(\d+)")
    type_pattern = re.compile(r"Type:\s+(\d+)")

    lines = output.split('\n')
    current_segment = {}

    for line in lines:
        # Новое тело
        body_match = body_pattern.search(line)
        if body_match:
            body_id = int(body_match.group(1))
            body_name = body_match.group(2).strip()
            current_body = body_id
            if body_id not in bodies:
                bodies[body_id] = {
                    'name': body_name,
                    'segments': []
                }
            continue

        # Информация об интервалах (в секундах)
        interval_match = interval_pattern.search(line)
        if interval_match and current_body is not None:
            interval_sec = float(interval_match.group(1))
            interval_days = interval_sec / 86400.0
            current_segment['interval_length'] = interval_days
            continue

        # Количество интервалов
        count_match = count_pattern.search(line)
        if count_match and current_body is not None:
            count = int(count_match.group(1))
            current_segment['num_intervals'] = count
            continue

        # Тип сегмента
        type_match = type_pattern.search(line)
        if type_match and current_body is not None:
            seg_type = int(type_match.group(1))
            current_segment['type'] = f"Type {seg_type}"

            # Если накопили информацию о сегменте, сохраняем
            if 'interval_length' in current_segment:
                bodies[current_body]['segments'].append(current_segment.copy())
                current_segment = {}
            continue

    return bodies


def analyze_spk_file(spk_file: str, cspice_path: str = "vendor/spice/cspice") -> Dict:
    """
    Полный анализ SPK файла с извлечением нативных интервалов.
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {spk_file}")
    print(f"{'='*80}\n")

    # Запускаем BRIEF
    brief_output = run_spice_brief(spk_file, cspice_path)

    # Парсим вывод
    bodies = parse_brief_output(brief_output)

    # Выводим результаты
    if not bodies:
        print("⚠️  No Chebyshev interval data found in BRIEF output.")
        print("\nRaw BRIEF output:")
        print(brief_output[:2000])
        return {}

    print(f"Found {len(bodies)} bodies with interval data:\n")

    # Сортируем по ID
    for body_id in sorted(bodies.keys()):
        info = bodies[body_id]
        body_name = BODY_NAMES.get(body_id, info['name'])

        print(f"Body {body_id:10d}: {body_name}")

        if not info['segments']:
            print("  No segment data available")
            continue

        # Усредняем интервалы по всем сегментам
        intervals = [seg['interval_length'] for seg in info['segments'] if 'interval_length' in seg]

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)

            print(f"  Segments: {len(info['segments'])}")
            print(f"  Native interval: {avg_interval:.2f} days (avg)")
            if len(intervals) > 1:
                print(f"  Range: {min_interval:.2f} - {max_interval:.2f} days")

            # Рекомендация для конвертера
            if avg_interval <= 8:
                print(f"  ✅ Recommended: {avg_interval:.1f} days (use native)")
            elif avg_interval <= 16:
                print(f"  ✅ Recommended: 16.0 days (standard)")
            elif avg_interval <= 32:
                print(f"  ✅ Recommended: 32.0 days")
            else:
                print(f"  ✅ Recommended: {int(avg_interval)} days")
        else:
            print("  ⚠️  No interval data in segments")

        print()

    return bodies


def generate_recommendations(file_analyses: Dict[str, Dict]) -> Dict[int, float]:
    """
    Генерирует рекомендации по интервалам для каждого тела на основе анализа всех файлов.

    Returns:
        Dict[body_id, recommended_interval_days]
    """
    recommendations = {}

    # Собираем все интервалы для каждого тела из всех файлов
    body_intervals = {}

    for filename, bodies in file_analyses.items():
        for body_id, info in bodies.items():
            if body_id not in body_intervals:
                body_intervals[body_id] = []

            for seg in info['segments']:
                if 'interval_length' in seg:
                    body_intervals[body_id].append(seg['interval_length'])

    # Определяем оптимальный интервал для каждого тела
    for body_id, intervals in body_intervals.items():
        if not intervals:
            continue

        # Используем минимальный интервал из всех эфемерид
        # (наиболее детальный)
        min_interval = min(intervals)

        # Округляем до стандартных значений: 8, 16, 32, 64, 128, 256
        standard_intervals = [8, 16, 32, 64, 128, 256]

        # Выбираем ближайший стандартный интервал, не меньше нативного
        recommended = min([si for si in standard_intervals if si >= min_interval], default=256)

        recommendations[body_id] = float(recommended)

    return recommendations


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_spk_intervals.py <spk_file1> [spk_file2 ...]")
        print("\nExample:")
        print("  python analyze_spk_intervals.py data/ephemerides/jpl/de431/de431_part-1.bsp")
        print("  python analyze_spk_intervals.py data/ephemerides/*/**.bsp")
        sys.exit(1)

    cspice_path = "vendor/spice/cspice"

    if not os.path.exists(os.path.join(cspice_path, "exe", "brief.exe")):
        print(f"❌ SPICE Toolkit not found at {cspice_path}")
        print("\nPlease install SPICE Toolkit:")
        print("  curl -L -o vendor/spice/cspice.zip https://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Windows_VisualC_64bit/packages/cspice.zip")
        print("  Expand-Archive vendor/spice/cspice.zip -DestinationPath vendor/spice")
        sys.exit(1)

    file_analyses = {}

    # Анализируем каждый файл
    for spk_file in sys.argv[1:]:
        if not os.path.exists(spk_file):
            print(f"⚠️  File not found: {spk_file}")
            continue

        try:
            bodies = analyze_spk_file(spk_file, cspice_path)
            file_analyses[spk_file] = bodies
        except Exception as e:
            print(f"❌ Error analyzing {spk_file}: {e}")
            continue

    # Генерируем общие рекомендации
    if len(file_analyses) > 1:
        print(f"\n{'='*80}")
        print("RECOMMENDED INTERVALS FOR UNIVERSAL CONVERTER")
        print(f"{'='*80}\n")

        recommendations = generate_recommendations(file_analyses)

        print("BODY_INTERVALS = {")
        for body_id in sorted(recommendations.keys()):
            interval = recommendations[body_id]
            name = BODY_NAMES.get(body_id, f"Body {body_id}")
            print(f"    {body_id:10d}: {interval:6.1f},  # {name}")
        print("}")

        print("\nThese values can be used in the universal converter configuration.")


if __name__ == "__main__":
    main()
