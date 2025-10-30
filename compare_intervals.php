<?php
require 'vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;

$old = new EphReader('data/ephemerides/epm/2021/epm2021.eph');      // i32
$new = new EphReader('data/ephemerides/epm/2021/epm2021_i16.eph');   // i16

$jd = 2451545.0;
$body = 399;

$p1 = $old->compute($body, $jd);
$p2 = $new->compute($body, $jd);

echo "Comparison: interval=32 vs interval=16 at J2000.0 (Earth)\n";
echo "===========================================================\n\n";

printf("Old (i32): X=%+.9f  Y=%+.9f  Z=%+.9f AU\n", $p1['pos'][0], $p1['pos'][1], $p1['pos'][2]);
printf("New (i16): X=%+.9f  Y=%+.9f  Z=%+.9f AU\n", $p2['pos'][0], $p2['pos'][1], $p2['pos'][2]);

$dx = abs($p1['pos'][0] - $p2['pos'][0]);
$dy = abs($p1['pos'][1] - $p2['pos'][1]);
$dz = abs($p1['pos'][2] - $p2['pos'][2]);
$diff = sqrt($dx*$dx + $dy*$dy + $dz*$dz);

echo "\nDifference:\n";
printf("  ΔX = %.3e AU (%.1f km)\n", $dx, $dx * 149597870.7);
printf("  ΔY = %.3e AU (%.1f km)\n", $dy, $dy * 149597870.7);
printf("  ΔZ = %.3e AU (%.1f km)\n", $dz, $dz * 149597870.7);
printf("  Total = %.3e AU (%.1f km)\n", $diff, $diff * 149597870.7);

if ($diff < 1e-7) {
    echo "\n✅ Precision improved! Difference < 15 km\n";
} else {
    echo "\n⚠️  Large difference detected\n";
}

// Check metadata
echo "\nMetadata comparison:\n";
$meta1 = $old->getMetadata();
$meta2 = $new->getMetadata();

printf("  Old: interval=%d days, %d intervals, size=%.2f MB\n",
    $meta1['intervalDays'], $meta1['numIntervals'], filesize('data/ephemerides/epm/2021/epm2021.eph')/1024/1024);
printf("  New: interval=%d days, %d intervals, size=%.2f MB\n",
    $meta2['intervalDays'], $meta2['numIntervals'], filesize('data/ephemerides/epm/2021/epm2021_i16.eph')/1024/1024);
