<?php
/**
 * Test SQLite ephemeris reader
 */

require_once 'php/src/SqliteEphReader.php';

use Swisseph\Ephemeris\SqliteEphReader;

$dbFile = 'data/ephemerides/epm/2021/epm2021.db';

if (!file_exists($dbFile)) {
    die("SQLite database not found: {$dbFile}\n" .
        "Please run: python tools/spice2sqlite.py data/ephemerides/epm/2021/spice/epm2021.bsp {$dbFile}\n");
}

try {
    $eph = new SqliteEphReader($dbFile);

    // Display metadata
    echo "=== Ephemeris Metadata ===\n";
    $meta = $eph->getMetadata();
    print_r($meta);

    echo "\n=== Available Bodies ===\n";
    foreach ($eph->getBodies() as $id => $name) {
        echo sprintf("ID %3d: %s\n", $id, $name);
    }

    // Compute Earth position at J2000.0
    echo "\n=== Earth Position at J2000.0 ===\n";
    $jd = 2451545.0;
    $result = $eph->compute(399, $jd);

    echo "JD: {$jd}\n";
    echo sprintf("Position (AU): X=%.8f, Y=%.8f, Z=%.8f\n", ...$result['pos']);
    echo sprintf("Velocity (AU/day): VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result['vel']);

    // Benchmark: single lookups
    echo "\n=== Benchmark: 1,000 random Earth positions ===\n";
    $startTime = microtime(true);
    $iterations = 1000;

    $jdMin = $meta['startJD'];
    $jdMax = $meta['endJD'];

    for ($i = 0; $i < $iterations; $i++) {
        $jd_random = $jdMin + mt_rand() / mt_getrandmax() * ($jdMax - $jdMin);
        $eph->compute(399, $jd_random, false);
    }

    $elapsed = microtime(true) - $startTime;
    $avgTime = ($elapsed / $iterations) * 1000;

    echo sprintf("Total time: %.3f seconds\n", $elapsed);
    echo sprintf("Average: %.4f ms per computation\n", $avgTime);
    echo sprintf("Throughput: %.0f computations/second\n", $iterations / $elapsed);

    // Database statistics
    echo "\n=== Database Statistics ===\n";
    $stats = $eph->getStats();
    echo "Total intervals: {$stats['totalIntervals']}\n";
    echo "Database size: " . round($stats['databaseSize'] / 1024 / 1024, 2) . " MB\n";
    echo "\nIntervals per body:\n";
    foreach ($stats['intervalsPerBody'] as $name => $count) {
        echo "  {$name}: {$count}\n";
    }

    echo "\n✅ Success!\n";

} catch (\Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
    exit(1);
}
