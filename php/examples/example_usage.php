<?php
/**
 * Example: Using EphReader to compute planetary positions
 */

require_once __DIR__ . '/../src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

// Path to .eph file (created by spice2eph.py)
$ephFile = __DIR__ . '/../../data/ephemerides/epm/2021/epm2021.eph';

if (!file_exists($ephFile)) {
    die("Ephemeris file not found: {$ephFile}\n" .
        "Please run: python tools/spice2eph.py data/ephemerides/epm/2021/spice/epm2021.bsp {$ephFile}\n");
}

try {
    $eph = new EphReader($ephFile);

    // Display metadata
    echo "=== Ephemeris Metadata ===\n";
    $meta = $eph->getMetadata();
    print_r($meta);

    echo "\n=== Available Bodies ===\n";
    foreach ($eph->getBodies() as $id => $info) {
        echo sprintf("ID %3d: %s\n", $id, $info['name']);
    }

    // Compute Earth position at J2000.0
    echo "\n=== Earth Position at J2000.0 ===\n";
    $jd = 2451545.0; // J2000.0
    $result = $eph->compute(399, $jd); // 399 = Earth NAIF ID

    echo "JD: {$jd}\n";
    echo sprintf("Position (AU): X=%.8f, Y=%.8f, Z=%.8f\n", ...$result['pos']);
    echo sprintf("Velocity (AU/day): VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result['vel']);

    // Benchmark: 10,000 position computations
    echo "\n=== Benchmark: 10,000 Earth positions ===\n";
    $startTime = microtime(true);
    $iterations = 10000;

    for ($i = 0; $i < $iterations; $i++) {
        $jd_random = $meta['startJD'] + mt_rand() / mt_getrandmax() *
                     ($meta['endJD'] - $meta['startJD']);
        $eph->compute(399, $jd_random, false); // Position only, no velocity
    }

    $elapsed = microtime(true) - $startTime;
    $avgTime = ($elapsed / $iterations) * 1000; // ms

    echo sprintf("Total time: %.3f seconds\n", $elapsed);
    echo sprintf("Average: %.4f ms per computation\n", $avgTime);
    echo sprintf("Throughput: %.0f computations/second\n", $iterations / $elapsed);

} catch (\Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
    exit(1);
}
