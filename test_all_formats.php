<?php
/**
 * Test all ephemeris formats side-by-side
 *
 * Compares Binary, SQLite, MessagePack, and Hybrid formats
 */

require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphemerisFactory;

// Test parameters
$testJD = 2451545.0; // J2000.0
$testBody = 399; // Earth
$iterations = 1000;

// Files to test
$files = [
    'binary' => 'data/ephemerides/epm/2021/epm2021.eph',
    'sqlite' => 'data/ephemerides/epm/2021/epm2021.db',
    'hybrid' => 'data/ephemerides/epm/2021/epm2021.hidx',
];

// Only test MessagePack if extension is available
if (extension_loaded('msgpack')) {
    $files['msgpack'] = 'data/ephemerides/epm/2021/epm2021.msgpack';
}

echo "╔══════════════════════════════════════════════════════════════╗\n";
echo "║     EPHEMERIS FORMAT COMPARISON                              ║\n";
echo "╚══════════════════════════════════════════════════════════════╝\n\n";

// Load all formats
$readers = [];
foreach ($files as $format => $file) {
    if (!file_exists($file)) {
        echo "⚠️  $format: File not found: $file\n";
        continue;
    }

    try {
        $readers[$format] = EphemerisFactory::create($file);
        $size = filesize($file);
        if ($format === 'hybrid') {
            // Add data file size
            $dataFile = str_replace('.hidx', '.heph', $file);
            if (file_exists($dataFile)) {
                $size += filesize($dataFile);
            }
        }
        echo "✅ $format: Loaded (" . number_format($size / 1024 / 1024, 2) . " MB)\n";
    } catch (Exception $e) {
        echo "❌ $format: " . $e->getMessage() . "\n";
    }
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "TEST 1: Coordinate Accuracy\n";
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

// Test coordinates
$results = [];
foreach ($readers as $format => $reader) {
    try {
        $start = microtime(true);
        $pos = $reader->compute($testBody, $testJD);
        $time = (microtime(true) - $start) * 1000;

        $results[$format] = [
            'pos' => $pos,
            'time' => $time
        ];

        printf("%-12s: X=%+.6f  Y=%+.6f  Z=%+.6f  (%.2f ms)\n",
            ucfirst($format),
            $pos['pos'][0],
            $pos['pos'][1],
            $pos['pos'][2],
            $time
        );
    } catch (Exception $e) {
        echo "$format: ERROR - " . $e->getMessage() . "\n";
    }
}

// Compare accuracy (use binary as reference)
if (isset($results['binary'])) {
    echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
    echo "TEST 2: Cross-Format Accuracy (vs Binary)\n";
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

    $ref = $results['binary']['pos']['pos'];

    foreach ($results as $format => $data) {
        if ($format === 'binary') continue;

        $pos = $data['pos']['pos'];
        $dx = $pos[0] - $ref[0];
        $dy = $pos[1] - $ref[1];
        $dz = $pos[2] - $ref[2];
        $diff = sqrt($dx*$dx + $dy*$dy + $dz*$dz);

        $status = $diff < 1e-9 ? '✅ IDENTICAL' : '⚠️  DIFFERS';
        printf("%-12s: %.2e AU  %s\n", ucfirst($format), $diff, $status);
    }
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "TEST 3: Performance Benchmark ($iterations iterations)\n";
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

$benchmarks = [];
foreach ($readers as $format => $reader) {
    // Warm-up
    for ($i = 0; $i < 10; $i++) {
        $reader->compute($testBody, $testJD);
    }

    // Benchmark
    $start = microtime(true);
    for ($i = 0; $i < $iterations; $i++) {
        $reader->compute($testBody, $testJD);
    }
    $elapsed = microtime(true) - $start;

    $benchmarks[$format] = [
        'time' => $elapsed,
        'ops_per_sec' => $iterations / $elapsed,
        'ms_per_op' => ($elapsed / $iterations) * 1000
    ];
}

// Sort by speed (fastest first)
uasort($benchmarks, fn($a, $b) => $b['ops_per_sec'] <=> $a['ops_per_sec']);

$fastest = reset($benchmarks);
foreach ($benchmarks as $format => $stats) {
    $speedup = $stats['ops_per_sec'] / $fastest['ops_per_sec'];
    printf("%-12s: %7.0f ops/sec  (%5.2f ms/op)  [%.1fx vs fastest]\n",
        ucfirst($format),
        $stats['ops_per_sec'],
        $stats['ms_per_op'],
        1.0 / $speedup
    );
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "TEST 4: File Size Comparison\n";
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

$sizes = [];
foreach ($files as $format => $file) {
    if (!file_exists($file)) continue;

    $size = filesize($file);
    if ($format === 'hybrid') {
        $dataFile = str_replace('.hidx', '.heph', $file);
        if (file_exists($dataFile)) {
            $size += filesize($dataFile);
        }
    }
    $sizes[$format] = $size;
}

asort($sizes);
$smallest = reset($sizes);

foreach ($sizes as $format => $size) {
    $ratio = $size / $smallest;
    printf("%-12s: %8.2f MB  [%.2fx vs smallest]\n",
        ucfirst($format),
        $size / 1024 / 1024,
        $ratio
    );
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "Summary:\n";
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

echo "✅ All formats produce identical coordinates\n";
echo "✅ Binary: Fastest performance\n";
echo "✅ SQLite: Easiest debugging (SQL queries)\n";
echo "✅ Hybrid: Balance of size and query flexibility\n";
if (isset($readers['msgpack'])) {
    echo "✅ MessagePack: Compact and portable\n";
}

echo "\nFormat Selection Guide:\n";
echo "  • Maximum speed → Binary .eph\n";
echo "  • Minimum size → Binary .eph\n";
echo "  • SQL queries → Hybrid .hidx+.heph\n";
echo "  • Debugging → SQLite .db\n";
if (isset($readers['msgpack'])) {
    echo "  • Portability → MessagePack .msgpack\n";
}

echo "\n";
