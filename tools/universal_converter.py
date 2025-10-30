#!/usr/bin/env python3
"""
Универсальный конвертер эфемерид.
Поддерживает конвертацию JPL DE и EPM эфемерид в различные форматы.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Импортируем существующий конвертер
from spice2eph import SPICEConverter


class UniversalConverter:
    def __init__(self, config_path: str = "tools/universal_converter_config.json"):
        """Инициализация конвертера с конфигурацией."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.sources = self.config['sources']
        self.body_intervals = self.config['body_intervals']
        self.profiles = self.config['conversion_profiles']

    def get_source_info(self, source_name: str) -> Optional[Dict]:
        """Получить информацию об источнике эфемерид."""
        return self.sources.get(source_name)

    def get_body_interval(self, body_id: int) -> float:
        """Получить рекомендуемый интервал для тела."""
        body_str = str(body_id)
        if body_str in self.body_intervals:
            return self.body_intervals[body_str]['interval_days']
        # Fallback: 32 дня для неизвестных тел
        return 32.0

    def get_profile(self, profile_name: str) -> Optional[Dict]:
        """Получить профиль конвертации."""
        return self.profiles.get(profile_name)

    def convert(self,
                source_name: str,
                output_path: str,
                bodies: Optional[List[int]] = None,
                intervals: Optional[List[float]] = None,
                profile_name: Optional[str] = None,
                output_format: str = "eph_binary") -> bool:
        """
        Выполнить конвертацию.

        Args:
            source_name: Имя источника из конфига
            output_path: Путь к выходному файлу
            bodies: Список ID тел (если None, берётся из профиля)
            intervals: Список интервалов для каждого тела (если None, используются нативные)
            profile_name: Имя профиля конвертации
            output_format: Формат выходного файла

        Returns:
            True если успешно
        """
        # Получаем информацию об источнике
        source_info = self.get_source_info(source_name)
        if not source_info:
            print(f"❌ Unknown source: {source_name}")
            print(f"Available sources: {', '.join(self.sources.keys())}")
            return False

        input_path = source_info['path']
        if not Path(input_path).exists():
            print(f"❌ Source file not found: {input_path}")
            return False

        # Применяем профиль если указан
        if profile_name:
            profile = self.get_profile(profile_name)
            if not profile:
                print(f"❌ Unknown profile: {profile_name}")
                print(f"Available profiles: {', '.join(self.profiles.keys())}")
                return False

            if bodies is None:
                bodies = profile['bodies']

            if 'use_native_intervals' in profile and profile['use_native_intervals']:
                if intervals is None:
                    intervals = [self.get_body_interval(b) for b in bodies]
            elif 'interval_days' in profile:
                if intervals is None:
                    intervals = [profile['interval_days']] * len(bodies)

        # Fallback если тела не указаны
        if bodies is None:
            print("⚠️  No bodies specified, using standard profile")
            bodies = self.profiles['standard']['bodies']

        # Fallback для интервалов
        if intervals is None:
            intervals = [self.get_body_interval(b) for b in bodies]
        elif len(intervals) == 1:
            # Один интервал для всех тел
            intervals = intervals * len(bodies)
        elif len(intervals) != len(bodies):
            print(f"❌ Number of intervals ({len(intervals)}) doesn't match number of bodies ({len(bodies)})")
            return False

        # Информация о конвертации
        print(f"\n{'='*80}")
        print(f"UNIVERSAL EPHEMERIS CONVERTER")
        print(f"{'='*80}\n")
        print(f"Source: {source_name}")
        print(f"  Path: {input_path}")
        print(f"  Available bodies: {source_info['available_bodies']}")
        print(f"  Coverage: {source_info['coverage']['years']} years\n")

        print(f"Conversion:")
        print(f"  Bodies: {len(bodies)}")
        print(f"  Output format: {output_format}")
        print(f"  Output path: {output_path}\n")

        print(f"Bodies and intervals:")
        for body_id, interval in zip(bodies, intervals):
            body_str = str(body_id)
            body_name = self.body_intervals.get(body_str, {}).get('name', f'Body {body_id}')
            native_interval = self.body_intervals.get(body_str, {}).get('interval_days', 'unknown')

            status = "✅" if interval == native_interval else "⚠️"
            print(f"  {status} {body_id:10d} ({body_name:20s}): {interval:6.1f} days (native: {native_interval})")

        print()

        # Выполняем конвертацию (пока только eph_binary через существующий конвертер)
        if output_format == "eph_binary":
            print("Starting conversion...")

            try:
                converter = SPICEConverter(
                    input_path,
                    output_path,
                    body_ids=bodies
                )

                # Используем первый интервал если все одинаковые, иначе средний
                if len(set(intervals)) == 1:
                    interval = intervals[0]
                else:
                    interval = sum(intervals) / len(intervals)
                    print(f"⚠️  Using average interval: {interval:.1f} days")
                    print("    (TODO: Implement per-body intervals in converter)")

                converter.convert(interval_days=interval)

                print(f"\n✅ Conversion complete: {output_path}")

                # Статистика
                output_size = Path(output_path).stat().st_size
                input_size = Path(input_path).stat().st_size
                compression = (1 - output_size / input_size) * 100

                print(f"\nStatistics:")
                print(f"  Input size:  {input_size / 1024 / 1024:.2f} MB")
                print(f"  Output size: {output_size / 1024 / 1024:.2f} MB")
                print(f"  Compression: {compression:.1f}%")

                return True

            except Exception as e:
                print(f"\n❌ Conversion failed: {e}")
                import traceback
                traceback.print_exc()
                return False

        else:
            print(f"❌ Output format '{output_format}' not implemented yet")
            print("    Currently supported: eph_binary")
            return False

    def merge_sources(self,
                      source_names: List[str],
                      output_path: str,
                      bodies: Optional[List[int]] = None,
                      profile_name: Optional[str] = None) -> bool:
        """
        Объединить несколько источников в один файл.
        Полезно для DE431 Part 1 + Part 2.
        """
        print(f"\n{'='*80}")
        print(f"MERGING EPHEMERIDES")
        print(f"{'='*80}\n")
        print(f"Sources: {', '.join(source_names)}")
        print(f"Output: {output_path}\n")

        print("❌ Merge functionality not implemented yet")
        print("   Workaround: Convert each part separately, then merge manually")

        return False

    def list_sources(self):
        """Показать доступные источники."""
        print(f"\n{'='*80}")
        print(f"AVAILABLE SOURCES")
        print(f"{'='*80}\n")

        for name, info in self.sources.items():
            print(f"{name}:")
            print(f"  Path: {info['path']}")
            print(f"  Bodies: {len(info['available_bodies'])} ({', '.join(map(str, info['available_bodies'][:8]))}...)")
            print(f"  Coverage: {info['coverage']['years']} years ({info['coverage']['start_jd']:.0f} to {info['coverage']['end_jd']:.0f} JD)")
            exists = "✅" if Path(info['path']).exists() else "❌"
            print(f"  File exists: {exists}")
            print()

    def list_profiles(self):
        """Показать доступные профили."""
        print(f"\n{'='*80}")
        print(f"AVAILABLE PROFILES")
        print(f"{'='*80}\n")

        for name, profile in self.profiles.items():
            print(f"{name}:")
            print(f"  Description: {profile['description']}")
            print(f"  Bodies: {len(profile['bodies'])} ({', '.join(map(str, profile['bodies'][:8]))}...)")
            if 'use_native_intervals' in profile:
                print(f"  Intervals: native (optimized per body)")
            elif 'interval_days' in profile:
                print(f"  Intervals: {profile['interval_days']} days (uniform)")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Universal Ephemeris Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Список источников и профилей
  python universal_converter.py --list-sources
  python universal_converter.py --list-profiles

  # Конвертация со стандартным профилем
  python universal_converter.py --source de440 --profile standard --output de440.eph

  # Конвертация EPM2021 с полным набором тел
  python universal_converter.py --source epm2021 --profile full_epm --output epm2021_full.eph

  # Кастомный набор тел
  python universal_converter.py --source epm2021 --bodies 10,301,2090377,2136199 --output custom.eph

  # Кастомный набор с индивидуальными интервалами
  python universal_converter.py --source epm2021 --bodies 10,301,2090377 --intervals 32,8,128 --output custom.eph
"""
    )

    parser.add_argument('--config', default='tools/universal_converter_config.json',
                        help='Path to configuration file')

    parser.add_argument('--list-sources', action='store_true',
                        help='List available ephemeris sources')

    parser.add_argument('--list-profiles', action='store_true',
                        help='List available conversion profiles')

    parser.add_argument('--source', type=str,
                        help='Source ephemeris name (from config)')

    parser.add_argument('--sources', type=str,
                        help='Multiple sources to merge (comma-separated)')

    parser.add_argument('--profile', type=str,
                        help='Conversion profile name (from config)')

    parser.add_argument('--bodies', type=str,
                        help='Body IDs to include (comma-separated)')

    parser.add_argument('--intervals', type=str,
                        help='Interval in days for each body (comma-separated) or single value for all')

    parser.add_argument('--output', type=str,
                        help='Output file path')

    parser.add_argument('--format', default='eph_binary',
                        choices=['eph_binary', 'sqlite', 'hdf5', 'json'],
                        help='Output format (default: eph_binary)')

    args = parser.parse_args()

    # Создаём конвертер
    try:
        converter = UniversalConverter(args.config)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in configuration file: {e}")
        sys.exit(1)

    # Обработка команд
    if args.list_sources:
        converter.list_sources()
        sys.exit(0)

    if args.list_profiles:
        converter.list_profiles()
        sys.exit(0)

    # Конвертация
    if not args.output:
        print("❌ Output path is required (use --output)")
        parser.print_help()
        sys.exit(1)

    # Парсинг bodies
    bodies = None
    if args.bodies:
        try:
            bodies = [int(b.strip()) for b in args.bodies.split(',')]
        except ValueError:
            print(f"❌ Invalid body IDs: {args.bodies}")
            sys.exit(1)

    # Парсинг intervals
    intervals = None
    if args.intervals:
        try:
            intervals = [float(i.strip()) for i in args.intervals.split(',')]
        except ValueError:
            print(f"❌ Invalid intervals: {args.intervals}")
            sys.exit(1)

    # Merge или обычная конвертация
    if args.sources:
        source_names = [s.strip() for s in args.sources.split(',')]
        success = converter.merge_sources(source_names, args.output, bodies, args.profile)
    elif args.source:
        success = converter.convert(
            args.source,
            args.output,
            bodies=bodies,
            intervals=intervals,
            profile_name=args.profile,
            output_format=args.format
        )
    else:
        print("❌ Either --source or --sources is required")
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
