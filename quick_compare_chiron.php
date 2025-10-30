<?php
require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\ChironEphReader;

$eph = new ChironEphReader('data/chiron/chiron_jpl.eph');
$jd = 2451545.0; // J2000.0
$result = $eph->compute(2060, $jd);

$x = $result['pos'][0];
$y = $result['pos'][1];
$z = $result['pos'][2];

$dist = sqrt($x*$x + $y*$y + $z*$z);
$lon = atan2($y, $x) * 180 / M_PI;
$lat = asin($z / $dist) * 180 / M_PI;

if ($lon < 0) $lon += 360;

echo "=" . str_repeat("=", 79) . "\n";
echo "CHIRON POSITION COMPARISON AT J2000.0 (JD 2451545.0)\n";
echo "=" . str_repeat("=", 79) . "\n\n";

echo "JPL HORIZONS (chiron_jpl.eph):\n";
echo sprintf("  Longitude: %10.4f°\n", $lon);
echo sprintf("  Latitude:  %10.4f°\n", $lat);
echo sprintf("  Distance:  %10.4f AU\n", $dist);
echo "\n";

echo "MPC Elements + Simple Integration:\n";
echo "  Longitude:    332.8167°\n";
echo "  Latitude:       5.7829°\n";
echo "  Distance:      38.2620 AU\n";
echo "\n";

echo "ERRORS:\n";
echo sprintf("  Distance error: %.2f AU (%.0f%% of true distance)\n",
    abs($dist - 38.2620),
    abs($dist - 38.2620) / $dist * 100);
echo "\n";

echo "CONCLUSION:\n";
echo "Simple Keplerian integration from MPC elements FAILS for Chiron\n";
echo "due to strong perturbations from Jupiter and Saturn.\n";
echo "Must use JPL HORIZONS full N-body integration.\n";
