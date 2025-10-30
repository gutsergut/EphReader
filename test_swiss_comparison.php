<?php
/**
 * Комплексное сравнение Swiss Ephemeris с JPL/EPM
 * Бенчмарки скорости и точности
 */

declare(strict_types=1);

// Тестовые эпохи (JD)
const TEST_EPOCHS = [
    2451545.0,   // J2000.0 (2000-01-01 12:00 TT)
    2460000.0,   // 2023-02-25
    2470000.0,   // 2050-06-15
    2400000.0,   // 1858-11-16 (историческая эпоха)
];

// Тела (Swiss ID -> Name)
const TEST_BODIES = [
    0 => 'Sun',
    1 => 'Moon',
    2 => 'Mercury',
    3 => 'Venus',
    4 => 'Mars',
    5 => 'Jupiter',
    6 => 'Saturn',
    7 => 'Uranus',
    8 => 'Neptune',
    9 => 'Pluto',
];

// Маппинг Swiss ID -> NAIF ID для сравнения
const SWISS_TO_NAIF = [
    0 => 10,   // Sun
    1 => 301,  // Moon
    2 => 1,    // Mercury
    3 => 2,    // Venus
    4 => 4,    // Mars
    5 => 5,    // Jupiter
    6 => 6,    // Saturn
    7 => 7,    // Uranus
    8 => 8,    // Neptune
    9 => 9,    // Pluto
];

class SwissEphemerisComparison
{
    private FFI $ffi;
    private array $results = [
        'performance' => [],
        'accuracy' => [],
    ];

    public function __construct()
    {
        // Загрузка Swiss Ephemeris через FFI
        $libPath = __DIR__ . '/../vendor/swisseph/libswe.dll';
        if (!file_exists($libPath)) {
            throw new RuntimeException("Swiss Ephemeris library not found: $libPath");
        }

        $header = <<<HEADER
        void swe_set_ephe_path(const char *path);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        void swe_close(void);
        HEADER;

        $this->ffi = FFI::cdef($header, $libPath);

        // Устанавливаем путь к эфемеридам
        $ephePath = realpath(__DIR__ . '/../ephe');
        $this->ffi->swe_set_ephe_path($ephePath);

        echo "✅ Swiss Ephemeris loaded from: $libPath\n";
        echo "✅ Ephemeris path: $ephePath\n";
    }

    public function __destruct()
    {
        $this->ffi->swe_close();
    }

    /**
     * Вычисление позиции тела
     */
    public function computePosition(int $body, float $jd, int $flags = 0): ?array
    {
        $xx = FFI::new('double[6]');
        $serr = FFI::new('char[256]');

        // SEFLG_SWIEPH (2) + SEFLG_BARYCTR (16384) + SEFLG_XYZ (4096)
        $iflag = 2 | 16384 | 4096 | $flags;

        $ret = $this->ffi->swe_calc_ut($jd - 2451545.0, $body, $iflag, FFI::addr($xx), FFI::addr($serr));

        if ($ret < 0) {
            return null;
        }

        return [
            'x' => $xx[0],
            'y' => $xx[1],
            'z' => $xx[2],
            'vx' => $xx[3],
            'vy' => $xx[4],
            'vz' => $xx[5],
        ];
    }

    /**
     * Бенчмарк скорости доступа
     */
    public function benchmarkAccessSpeed(int $iterations = 100): array
    {
        echo "\n🔧 Бенчмарк Swiss Ephemeris (FFI)...\n";

        $times = [];
        $successful = 0;

        for ($i = 0; $i < $iterations; $i++) {
            $epoch = TEST_EPOCHS[$i % count(TEST_EPOCHS)];
            $body = array_keys(TEST_BODIES)[$i % count(TEST_BODIES)];

            $start = microtime(true);
            $result = $this->computePosition($body, $epoch);
            $elapsed = (microtime(true) - $start) * 1000; // в миллисекунды

            if ($result !== null) {
                $times[] = $elapsed;
                $successful++;
            }
        }

        if (empty($times)) {
            return ['error' => 'Нет успешных вычислений'];
        }

        sort($times);
        $count = count($times);

        return [
            'mean_ms' => array_sum($times) / $count,
            'median_ms' => $times[intdiv($count, 2)],
            'min_ms' => min($times),
            'max_ms' => max($times),
            'stdev_ms' => $this->stdev($times),
            'success_rate' => ($successful / $iterations) * 100,
            'total_iterations' => $iterations,
        ];
    }

    /**
     * Сравнение с эталоном (данные из Python/calceph)
     */
    public function compareWithReference(array $referenceData): array
    {
        echo "\n📊 Сравнение Swiss Ephemeris с JPL DE440...\n";

        $errors = [];
        $bodyErrors = [];

        foreach (TEST_EPOCHS as $epoch) {
            foreach (TEST_BODIES as $swissId => $bodyName) {
                $naifId = SWISS_TO_NAIF[$swissId];

                // Вычисляем Swiss позицию
                $swissPos = $this->computePosition($swissId, $epoch);

                if ($swissPos === null) {
                    continue;
                }

                // Ищем референс позицию (должна быть загружена из Python скрипта)
                $refKey = "{$naifId}_{$epoch}";
                if (!isset($referenceData[$refKey])) {
                    continue;
                }

                $refPos = $referenceData[$refKey];

                // Вычисляем ошибку (Euclidean distance in AU)
                $dx = $swissPos['x'] - $refPos['x'];
                $dy = $swissPos['y'] - $refPos['y'];
                $dz = $swissPos['z'] - $refPos['z'];
                $errorAu = sqrt($dx*$dx + $dy*$dy + $dz*$dz);
                $errorKm = $errorAu * 149597870.7;

                $errors[] = $errorKm;
                $bodyErrors[$bodyName][] = $errorKm;
            }
        }

        if (empty($errors)) {
            return ['error' => 'Нет успешных сравнений'];
        }

        sort($errors);
        $count = count($errors);

        $result = [
            'median_km' => $errors[intdiv($count, 2)],
            'mean_km' => array_sum($errors) / $count,
            'min_km' => min($errors),
            'max_km' => max($errors),
            'stdev_km' => $this->stdev($errors),
            'body_errors' => [],
        ];

        // Статистика по телам
        foreach ($bodyErrors as $bodyName => $bodyErrs) {
            if (empty($bodyErrs)) continue;

            sort($bodyErrs);
            $bodyCount = count($bodyErrs);

            $result['body_errors'][$bodyName] = [
                'median_km' => $bodyErrs[intdiv($bodyCount, 2)],
                'max_km' => max($bodyErrs),
            ];
        }

        return $result;
    }

    /**
     * Стандартное отклонение
     */
    private function stdev(array $values): float
    {
        $count = count($values);
        if ($count < 2) {
            return 0.0;
        }

        $mean = array_sum($values) / $count;
        $variance = 0.0;

        foreach ($values as $value) {
            $variance += pow($value - $mean, 2);
        }

        return sqrt($variance / ($count - 1));
    }

    /**
     * Запуск полного сравнения
     */
    public function runFullComparison(): void
    {
        echo str_repeat('=', 80) . "\n";
        echo "🚀 SWISS EPHEMERIS COMPARISON\n";
        echo str_repeat('=', 80) . "\n";

        // 1. Бенчмарк скорости
        echo "\n" . str_repeat('=', 80) . "\n";
        echo "⚡ БЕНЧМАРК СКОРОСТИ\n";
        echo str_repeat('=', 80) . "\n";

        $this->results['performance'] = $this->benchmarkAccessSpeed(100);

        // 2. Загрузка референсных данных (если есть)
        $refFile = __DIR__ . '/../COMPREHENSIVE_COMPARISON_RESULTS.json';
        if (file_exists($refFile)) {
            echo "\n📂 Загрузка референсных данных из Python...\n";
            // TODO: парсинг JSON и сравнение
            echo "⚠️  Сравнение точности требует предварительного запуска Python скрипта\n";
        }

        // 3. Печать результатов
        $this->printResults();

        // 4. Сохранение
        $this->saveResults();
    }

    /**
     * Печать результатов
     */
    private function printResults(): void
    {
        echo "\n" . str_repeat('=', 80) . "\n";
        echo "📊 РЕЗУЛЬТАТЫ\n";
        echo str_repeat('=', 80) . "\n";

        if (isset($this->results['performance']) && !isset($this->results['performance']['error'])) {
            $perf = $this->results['performance'];

            echo "\n⚡ СКОРОСТЬ ДОСТУПА (Swiss Ephemeris FFI)\n";
            echo str_repeat('-', 80) . "\n";
            printf("Mean:          %.3f ms\n", $perf['mean_ms']);
            printf("Median:        %.3f ms\n", $perf['median_ms']);
            printf("Min:           %.3f ms\n", $perf['min_ms']);
            printf("Max:           %.3f ms\n", $perf['max_ms']);
            printf("Stdev:         %.3f ms\n", $perf['stdev_ms']);
            printf("Success rate:  %.1f%%\n", $perf['success_rate']);
        }

        if (isset($this->results['accuracy']) && !isset($this->results['accuracy']['error'])) {
            $acc = $this->results['accuracy'];

            echo "\n🎯 ТОЧНОСТЬ (vs JPL DE440)\n";
            echo str_repeat('-', 80) . "\n";
            printf("Median error:  %.2f km\n", $acc['median_km']);
            printf("Mean error:    %.2f km\n", $acc['mean_km']);
            printf("Min error:     %.2f km\n", $acc['min_km']);
            printf("Max error:     %.2f km\n", $acc['max_km']);

            if (isset($acc['body_errors'])) {
                echo "\nПо телам:\n";
                foreach ($acc['body_errors'] as $body => $errors) {
                    printf("  %-10s: %.2f km (median), %.2f km (max)\n",
                        $body, $errors['median_km'], $errors['max_km']);
                }
            }
        }
    }

    /**
     * Сохранение результатов
     */
    private function saveResults(): void
    {
        $outputFile = __DIR__ . '/../SWISS_EPHEMERIS_COMPARISON.json';
        file_put_contents(
            $outputFile,
            json_encode($this->results, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
        );
        echo "\n💾 Результаты сохранены: $outputFile\n";
    }
}

// Запуск
try {
    $comparison = new SwissEphemerisComparison();
    $comparison->runFullComparison();
} catch (Throwable $e) {
    echo "❌ Ошибка: {$e->getMessage()}\n";
    echo $e->getTraceAsString() . "\n";
    exit(1);
}
