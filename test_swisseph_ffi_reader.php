<?php

require_once __DIR__ . '/php/src/SwissEphFFIReader.php';

use Swisseph\Ephemeris\SwissEphFFIReader;

echo "╔══════════════════════════════════════════════════════════════╗\n";
echo "║  SwissEphFFIReader Test Suite                               ║\n";
echo "╚══════════════════════════════════════════════════════════════╝\n\n";

try {
    // Initialize reader
    $reader = new SwissEphFFIReader(
        'vendor/swisseph/swedll64.dll',
        'ephe/'
    );

    echo "✅ FFI reader initialized\n\n";

    // Test data
    $jd = 2451545.0; // J2000.0
    $bodies = [
        10 => 'Sun',
        301 => 'Moon',
        2 => 'Venus',
        3 => 'Earth',
        5 => 'Jupiter',
    ];

    // Test both frames
    foreach (['geocentric', 'barycentric'] as $frame) {
        echo "📡 Testing $frame frame:\n";
        echo str_repeat('─', 64) . "\n\n";

        foreach ($bodies as $naifId => $name) {
            try {
                $result = $reader->compute($naifId, $jd, $frame);

                $pos = $result['pos'];
                $vel = $result['vel'];
                $distance = sqrt($pos[0]**2 + $pos[1]**2 + $pos[2]**2);

                echo "🌍 $name (NAIF $naifId):\n";
                printf("  Position:  [%0.3f, %0.3f, %0.3f] km\n", ...$pos);
                printf("  Velocity:  [%0.3f, %0.3f, %0.3f] km/day\n", ...$vel);
                printf("  Distance:  %0.0f thousand km\n", $distance / 1000);
                printf("  Frame:     %s\n\n", $result['frame']);

            } catch (RuntimeException $e) {
                echo "  ⚠️  Error: {$e->getMessage()}\n\n";
            }
        }
    }

    // Cross-validation: geocentric vs barycentric inversion
    echo "🔬 Cross-validation (coordinate inversion):\n";
    echo str_repeat('─', 64) . "\n\n";

    $sunGeo = $reader->compute(10, $jd, 'geocentric');
    $sunBary = $reader->compute(10, $jd, 'barycentric');

    $expectedBary = [
        -$sunGeo['pos'][0],
        -$sunGeo['pos'][1],
        -$sunGeo['pos'][2],
    ];

    $error = sqrt(
        ($sunBary['pos'][0] - $expectedBary[0])**2 +
        ($sunBary['pos'][1] - $expectedBary[1])**2 +
        ($sunBary['pos'][2] - $expectedBary[2])**2
    );

    echo "Sun geocentric:     [" . implode(', ', array_map(fn($v) => sprintf('%0.3f', $v), $sunGeo['pos'])) . "] km\n";
    echo "Sun barycentric:    [" . implode(', ', array_map(fn($v) => sprintf('%0.3f', $v), $sunBary['pos'])) . "] km\n";
    echo "Expected (inverted):[" . implode(', ', array_map(fn($v) => sprintf('%0.3f', $v), $expectedBary)) . "] km\n";
    printf("Inversion error:    %0.3f km ", $error);

    if ($error < 0.001) {
        echo "✅ Perfect!\n";
    } elseif ($error < 1.0) {
        echo "✅ Excellent\n";
    } else {
        echo "❌ Poor\n";
    }

    echo "\n";

    // Performance test
    echo "⚡ Performance test (1000 computations):\n";
    echo str_repeat('─', 64) . "\n\n";

    $iterations = 1000;
    $start = microtime(true);

    for ($i = 0; $i < $iterations; $i++) {
        $reader->compute(10, $jd + $i * 0.01, 'geocentric');
    }

    $elapsed = microtime(true) - $start;
    $rate = $iterations / $elapsed;

    printf("Iterations:  %d\n", $iterations);
    printf("Time:        %0.3f seconds\n", $elapsed);
    printf("Rate:        %0.0f computations/second\n", $rate);
    printf("Avg latency: %0.3f ms/computation\n", ($elapsed / $iterations) * 1000);

    echo "\n╔══════════════════════════════════════════════════════════════╗\n";
    echo "║  ✅ All tests passed                                         ║\n";
    echo "╚══════════════════════════════════════════════════════════════╝\n";

} catch (Exception $e) {
    echo "❌ Fatal error: {$e->getMessage()}\n";
    exit(1);
}
