<?php
require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphemerisFactory;

echo "\n========================================\n";
echo "JPL DE440 Format Comparison Test\n";
echo "========================================\n\n";

$base_path = 'data/ephemerides/jpl/';
$formats = [
    'Binary'      => $base_path . 'de440.eph',
    'SQLite'      => $base_path . 'de440.db',
    'Hybrid'      => $base_path . 'de440.hidx',
    'MessagePack' => $base_path . 'de440.msgpack'
];

// Test parameters
$test_jd = 2451545.0; // J2000.0
$test_body = 399; // Earth

$results = [];
$reference = null;

echo "TEST 1: Metadata Verification\n";
echo str_repeat("-", 80) . "\n";

foreach ($formats as $name => $path) {
    if (!file_exists($path)) {
        echo "⚠️  $name: File not found ($path)\n";
        continue;
    }

    try {
        $eph = EphemerisFactory::create($path);
        $meta = $eph->getMetadata();
        $bodies = $eph->getBodies();

        $size_mb = round(filesize($path) / 1024 / 1024, 2);

        echo "✅ $name ($size_mb MB)\n";
        echo "   Range: JD {$meta['start_jd']} - {$meta['end_jd']}\n";
        echo "   Interval: {$meta['interval_days']} days\n";
        echo "   Bodies: " . count($bodies) . " (" . implode(', ', array_column($bodies, 'name')) . ")\n";
        echo "   Degree: {$meta['degree']}\n\n";

        $results[$name] = $eph;

    } catch (Exception $e) {
        echo "❌ $name: " . $e->getMessage() . "\n\n";
    }
}

if (empty($results)) {
    echo "❌ No valid formats found!\n";
    exit(1);
}

echo "\nTEST 2: Cross-Format Accuracy (Earth @ J2000.0)\n";
echo str_repeat("-", 80) . "\n";

foreach ($results as $name => $eph) {
    try {
        $result = $eph->compute($test_body, $test_jd);

        if ($reference === null) {
            $reference = $result;
            echo "📍 $name (reference)\n";
        } else {
            $dx = $result['pos'][0] - $reference['pos'][0];
            $dy = $result['pos'][1] - $reference['pos'][1];
            $dz = $result['pos'][2] - $reference['pos'][2];
            $diff = sqrt($dx*$dx + $dy*$dy + $dz*$dz);

            $status = $diff < 1e-10 ? '✅' : '⚠️';
            echo "$status $name: " . sprintf("%.2e AU", $diff);
            echo $diff < 1e-10 ? " IDENTICAL\n" : " DIFFERS\n";
        }

        echo "   Position: [";
        echo sprintf("%.9f, %.9f, %.9f", ...$result['pos']);
        echo "] AU\n";

    } catch (Exception $e) {
        echo "❌ $name: " . $e->getMessage() . "\n";
    }
}

echo "\nTEST 3: Performance Benchmark (1000 iterations)\n";
echo str_repeat("-", 80) . "\n";

$iterations = 1000;
$perf_results = [];

foreach ($results as $name => $eph) {
    $start = microtime(true);

    for ($i = 0; $i < $iterations; $i++) {
        $eph->compute($test_body, $test_jd + $i * 0.01);
    }

    $elapsed = microtime(true) - $start;
    $ops_per_sec = round($iterations / $elapsed);
    $ms_per_op = round($elapsed * 1000 / $iterations, 2);

    $perf_results[$name] = $ops_per_sec;

    echo sprintf("%-12s: %5d ops/sec (%4.2f ms/op)", $name, $ops_per_sec, $ms_per_op);

    if (count($perf_results) > 1) {
        $fastest = max($perf_results);
        $slowdown = round($fastest / $ops_per_sec, 1);
        echo sprintf(" [%.1fx%s]", $slowdown, $slowdown > 1 ? " slower" : "");
    }

    echo "\n";
}

echo "\n========================================\n";
echo "All Tests Complete\n";
echo "========================================\n\n";
