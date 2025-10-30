<?php
require 'vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\HybridEphReader;

$jd = 2451545.0;
$bodyId = 399;

// Binary
$binary = new EphReader('data/ephemerides/epm/2021/epm2021.eph');
$binPos = $binary->compute($bodyId, $jd);

// Hybrid
$hybrid = new HybridEphReader('data/ephemerides/epm/2021/epm2021.hidx');
$hybPos = $hybrid->compute($bodyId, $jd);

echo "Comparison at JD $jd (Earth):\n";
echo "==============================\n\n";

printf("Binary:  X=%.15f  Y=%.15f  Z=%.15f\n",
    $binPos['pos'][0], $binPos['pos'][1], $binPos['pos'][2]);
printf("Hybrid:  X=%.15f  Y=%.15f  Z=%.15f\n",
    $hybPos['pos'][0], $hybPos['pos'][1], $hybPos['pos'][2]);

$dx = abs($binPos['pos'][0] - $hybPos['pos'][0]);
$dy = abs($binPos['pos'][1] - $hybPos['pos'][1]);
$dz = abs($binPos['pos'][2] - $hybPos['pos'][2]);

printf("\nDifferences:\n");
printf("  ΔX = %.3e AU (%.1f km)\n", $dx, $dx * 149597870.7);
printf("  ΔY = %.3e AU (%.1f km)\n", $dy, $dy * 149597870.7);
printf("  ΔZ = %.3e AU (%.1f km)\n", $dz, $dz * 149597870.7);
printf("  Total = %.3e AU (%.1f km)\n",
    sqrt($dx*$dx + $dy*$dy + $dz*$dz),
    sqrt($dx*$dx + $dy*$dy + $dz*$dz) * 149597870.7);

// Debug: get same interval from both
echo "\n\nDebug: Interval Data\n";
echo "====================\n";

// Get Binary interval index
$r = new ReflectionClass($binary);
$findMethod = $r->getMethod('findIntervalIdx');
$findMethod->setAccessible(true);
$intervalIdx = $findMethod->invoke($binary, $jd);

echo "Binary interval index: $intervalIdx\n";

// Get metadata
$meta = $binary->getMetadata();
echo "Interval days: {$meta['intervalDays']}\n";
echo "Start JD: {$meta['startJD']}\n";

$intervalStart = $meta['startJD'] + $intervalIdx * $meta['intervalDays'];
$intervalEnd = $intervalStart + $meta['intervalDays'];

printf("Binary interval: JD %.1f to %.1f\n", $intervalStart, $intervalEnd);

// Get normalized time
$t_norm = 2.0 * ($jd - $intervalStart) / ($intervalEnd - $intervalStart) - 1.0;
printf("Normalized time t: %.15f\n", $t_norm);
