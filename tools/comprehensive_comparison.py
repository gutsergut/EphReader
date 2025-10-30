#!/usr/bin/env python3
"""
Комплексное сравнение всех эфемерид: точность и скорость
Сравнивает JPL DE440, DE431, EPM2021, Swiss Ephemeris
"""

import sys
import time
import statistics
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Добавляем путь к calceph
sys.path.insert(0, str(Path(__file__).parent.parent / 'vendor' / 'calceph-4.0.1' / 'install' / 'lib' / 'python'))

try:
    import calceph
    HAS_CALCEPH = True
except ImportError:
    HAS_CALCEPH = False
    print("⚠️  calceph не установлен, часть тестов будет пропущена")

# Тестовые эпохи (JD)
TEST_EPOCHS = [
    2451545.0,   # J2000.0 (2000-01-01 12:00 TT)
    2460000.0,   # 2023-02-25
    2470000.0,   # 2050-06-15
    2400000.0,   # 1858-11-16 (историческая эпоха)
]

# Тела для тестирования (NAIF ID)
TEST_BODIES = {
    1: "Mercury",
    2: "Venus",
    3: "EMB",
    4: "Mars",
    5: "Jupiter",
    6: "Saturn",
    7: "Uranus",
    8: "Neptune",
    9: "Pluto",
    10: "Sun",
    301: "Moon",
    399: "Earth",
}

class EphemerisComparison:
    """Комплексное сравнение эфемерид"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.results = {
            'accuracy': {},
            'performance': {},
            'intervals': {},
        }

    def load_ephemeris(self, name: str, path: str) -> calceph.Ephem:
        """Загрузка эфемериды через calceph"""
        full_path = self.base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"{name}: {full_path} не найден")

        eph = calceph.Ephem()
        eph.open(str(full_path))
        return eph

    def compute_position(self, eph: calceph.Ephem, body: int, epoch: float) -> Tuple[float, float, float]:
        """Вычисление позиции тела"""
        try:
            # Barrycentric position (center=0)
            result = eph.compute(epoch, body, 0, calceph.Constants.USE_NAIFID)
            if result is None:
                return None
            return (result[0], result[1], result[2])
        except Exception as e:
            return None

    def distance_3d(self, pos1, pos2) -> float:
        """Евклидово расстояние в 3D (AU)"""
        if pos1 is None or pos2 is None:
            return None
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        return (dx*dx + dy*dy + dz*dz) ** 0.5

    def benchmark_access_speed(self, name: str, eph: calceph.Ephem, iterations: int = 100) -> Dict:
        """Бенчмарк скорости доступа"""
        print(f"\n🔧 Бенчмарк {name}...")

        times = []
        successful = 0

        for i in range(iterations):
            # Случайная эпоха и тело
            epoch = TEST_EPOCHS[i % len(TEST_EPOCHS)]
            body = list(TEST_BODIES.keys())[i % len(TEST_BODIES)]

            start = time.perf_counter()
            result = self.compute_position(eph, body, epoch)
            elapsed = time.perf_counter() - start

            if result is not None:
                times.append(elapsed * 1000)  # в миллисекунды
                successful += 1

        if not times:
            return {
                'error': 'Нет успешных вычислений',
                'success_rate': 0.0
            }

        return {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'stdev_ms': statistics.stdev(times) if len(times) > 1 else 0,
            'success_rate': (successful / iterations) * 100,
            'total_iterations': iterations,
        }

    def compare_accuracy(self, reference_name: str, reference_eph: calceph.Ephem,
                        test_name: str, test_eph: calceph.Ephem) -> Dict:
        """Сравнение точности с эталоном"""
        print(f"\n📊 Сравнение {test_name} vs {reference_name}...")

        errors = []
        body_errors = {body: [] for body in TEST_BODIES}

        for epoch in TEST_EPOCHS:
            for body_id, body_name in TEST_BODIES.items():
                ref_pos = self.compute_position(reference_eph, body_id, epoch)
                test_pos = self.compute_position(test_eph, body_id, epoch)

                if ref_pos and test_pos:
                    error_au = self.distance_3d(ref_pos, test_pos)
                    error_km = error_au * 149597870.7  # AU to km
                    errors.append(error_km)
                    body_errors[body_id].append(error_km)

        if not errors:
            return {'error': 'Нет успешных сравнений'}

        # Агрегированная статистика
        result = {
            'median_km': statistics.median(errors),
            'mean_km': statistics.mean(errors),
            'min_km': min(errors),
            'max_km': max(errors),
            'stdev_km': statistics.stdev(errors) if len(errors) > 1 else 0,
            'body_errors': {}
        }

        # По каждому телу
        for body_id, body_name in TEST_BODIES.items():
            if body_errors[body_id]:
                result['body_errors'][body_name] = {
                    'median_km': statistics.median(body_errors[body_id]),
                    'max_km': max(body_errors[body_id]),
                }

        return result

    def extract_intervals(self, name: str, path: str) -> Dict:
        """Извлечение нативных интервалов через calceph_inspector"""
        print(f"\n🔍 Извлечение интервалов {name}...")

        inspector_path = self.base_dir / 'vendor' / 'calceph-4.0.1' / 'install' / 'bin' / 'calceph_inspector.exe'
        if not inspector_path.exists():
            return {'error': 'calceph_inspector не найден'}

        import subprocess
        full_path = self.base_dir / path

        try:
            result = subprocess.run(
                [str(inspector_path), str(full_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            intervals = {}
            for line in result.stdout.splitlines():
                # Парсим: "1           0           -3100014.50     1721425.50       1         2           Time span per record:    8 (day)"
                if 'Time span per record' in line:
                    parts = line.split()
                    body_id = int(parts[0])
                    interval_idx = parts.index('record:') + 1
                    interval_days = float(parts[interval_idx])

                    if body_id in TEST_BODIES:
                        intervals[TEST_BODIES[body_id]] = interval_days

            return intervals

        except Exception as e:
            return {'error': str(e)}

    def run_full_comparison(self):
        """Полное сравнение всех эфемерид"""

        print("=" * 80)
        print("🚀 КОМПЛЕКСНОЕ СРАВНЕНИЕ ЭФЕМЕРИД")
        print("=" * 80)

        if not HAS_CALCEPH:
            print("\n❌ calceph не установлен!")
            print("Установите: cd vendor/calceph-4.0.1/pythonapi && python setup.py install --user")
            return

        ephemerides = {
            'DE440': 'data/ephemerides/jpl/de440/linux_p1550p2650.440',
            'DE431_Part1': 'data/ephemerides/jpl/de431/de431_part-1.bsp',
            'EPM2021': 'data/ephemerides/epm/2021/spice/epm2021.bsp',
        }

        # Загрузка эфемерид
        print("\n📂 Загрузка эфемерид...")
        loaded = {}

        for name, path in ephemerides.items():
            try:
                loaded[name] = self.load_ephemeris(name, path)
                print(f"  ✅ {name}: {path}")
            except FileNotFoundError as e:
                print(f"  ⚠️  {name}: не найден ({path})")
            except Exception as e:
                print(f"  ❌ {name}: ошибка загрузки - {e}")

        if len(loaded) < 2:
            print("\n❌ Недостаточно эфемерид для сравнения!")
            return

        # 1. ИЗВЛЕЧЕНИЕ ИНТЕРВАЛОВ
        print("\n" + "=" * 80)
        print("📏 НАТИВНЫЕ ИНТЕРВАЛЫ")
        print("=" * 80)

        for name, path in ephemerides.items():
            if name in loaded:
                intervals = self.extract_intervals(name, path)
                self.results['intervals'][name] = intervals

        # 2. БЕНЧМАРКИ СКОРОСТИ
        print("\n" + "=" * 80)
        print("⚡ БЕНЧМАРКИ СКОРОСТИ ДОСТУПА")
        print("=" * 80)

        for name, eph in loaded.items():
            perf = self.benchmark_access_speed(name, eph, iterations=100)
            self.results['performance'][name] = perf

        # 3. СРАВНЕНИЕ ТОЧНОСТИ (DE440 как эталон)
        print("\n" + "=" * 80)
        print("🎯 СРАВНЕНИЕ ТОЧНОСТИ (эталон: JPL DE440)")
        print("=" * 80)

        if 'DE440' in loaded:
            reference_eph = loaded['DE440']
            reference_name = 'DE440'

            for name, eph in loaded.items():
                if name != reference_name:
                    accuracy = self.compare_accuracy(reference_name, reference_eph, name, eph)
                    self.results['accuracy'][f'{name}_vs_{reference_name}'] = accuracy

        # 4. ФИНАЛЬНЫЙ ОТЧЁТ
        self.print_final_report()
        self.save_results()

    def print_final_report(self):
        """Печать финального отчёта"""

        print("\n" + "=" * 80)
        print("📊 ФИНАЛЬНЫЙ ОТЧЁТ")
        print("=" * 80)

        # Таблица интервалов
        if self.results['intervals']:
            print("\n1️⃣  НАТИВНЫЕ ИНТЕРВАЛЫ (дни)")
            print("-" * 80)

            # Получаем все тела
            all_bodies = set()
            for intervals in self.results['intervals'].values():
                if isinstance(intervals, dict) and 'error' not in intervals:
                    all_bodies.update(intervals.keys())

            # Печать заголовка
            print(f"{'Body':<12}", end="")
            for name in self.results['intervals'].keys():
                print(f"{name:<15}", end="")
            print()
            print("-" * 80)

            # Печать данных
            for body in sorted(all_bodies):
                print(f"{body:<12}", end="")
                for name, intervals in self.results['intervals'].items():
                    if isinstance(intervals, dict) and 'error' not in intervals:
                        value = intervals.get(body, '-')
                        if isinstance(value, float):
                            print(f"{value:<15.1f}", end="")
                        else:
                            print(f"{value:<15}", end="")
                    else:
                        print(f"{'ERROR':<15}", end="")
                print()

        # Таблица скорости
        if self.results['performance']:
            print("\n2️⃣  СКОРОСТЬ ДОСТУПА")
            print("-" * 80)
            print(f"{'Ephemeris':<15} {'Mean (ms)':<12} {'Median (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Success %':<10}")
            print("-" * 80)

            for name, perf in self.results['performance'].items():
                if 'error' not in perf:
                    print(f"{name:<15} "
                          f"{perf['mean_ms']:<12.3f} "
                          f"{perf['median_ms']:<12.3f} "
                          f"{perf['min_ms']:<12.3f} "
                          f"{perf['max_ms']:<12.3f} "
                          f"{perf['success_rate']:<10.1f}")
                else:
                    print(f"{name:<15} ERROR: {perf['error']}")

        # Таблица точности
        if self.results['accuracy']:
            print("\n3️⃣  ТОЧНОСТЬ (vs DE440)")
            print("-" * 80)
            print(f"{'Ephemeris':<15} {'Median (km)':<15} {'Mean (km)':<15} {'Min (km)':<15} {'Max (km)':<15}")
            print("-" * 80)

            for name, acc in self.results['accuracy'].items():
                if 'error' not in acc:
                    eph_name = name.replace('_vs_DE440', '')
                    print(f"{eph_name:<15} "
                          f"{acc['median_km']:<15.2f} "
                          f"{acc['mean_km']:<15.2f} "
                          f"{acc['min_km']:<15.2f} "
                          f"{acc['max_km']:<15.2f}")
                else:
                    print(f"{name:<15} ERROR: {acc['error']}")

            # Детализация по телам
            print("\n4️⃣  ТОЧНОСТЬ ПО ТЕЛАМ (Median, km)")
            print("-" * 80)

            # Получаем все эфемериды
            eph_names = [name.replace('_vs_DE440', '') for name in self.results['accuracy'].keys()
                        if 'error' not in self.results['accuracy'][name]]

            if eph_names:
                print(f"{'Body':<12}", end="")
                for name in eph_names:
                    print(f"{name:<15}", end="")
                print()
                print("-" * 80)

                # Получаем все тела
                all_bodies = set()
                for acc in self.results['accuracy'].values():
                    if isinstance(acc, dict) and 'body_errors' in acc:
                        all_bodies.update(acc['body_errors'].keys())

                for body in sorted(all_bodies):
                    print(f"{body:<12}", end="")
                    for name in eph_names:
                        full_name = f"{name}_vs_DE440"
                        acc = self.results['accuracy'].get(full_name, {})
                        if 'body_errors' in acc and body in acc['body_errors']:
                            median = acc['body_errors'][body]['median_km']
                            print(f"{median:<15.2f}", end="")
                        else:
                            print(f"{'-':<15}", end="")
                    print()

    def save_results(self):
        """Сохранение результатов в JSON"""
        output_file = self.base_dir / 'COMPREHENSIVE_COMPARISON_RESULTS.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Результаты сохранены: {output_file}")


def main():
    comparison = EphemerisComparison()
    comparison.run_full_comparison()


if __name__ == '__main__':
    main()
