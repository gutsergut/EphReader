<?php
require 'vendor/autoload.php';
use Swisseph\Ephemeris\EphReader;

$jpl = new EphReader('data/ephemerides/jpl/de440.eph');
$epm = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

$jd = 2451545.0;
$body = 5; // Jupiter

$jpl_pos = $jpl->compute($body, $jd);
$epm_pos = $epm->compute($body, $jd);

echo "JPL DE440 Jupiter position (barycentric):\n";
printf("  X: %12.6f AU = %15.0f km\n", $jpl_pos['pos'][0], $jpl_pos['pos'][0] * 149597870.7);
printf("  Y: %12.6f AU = %15.0f km\n", $jpl_pos['pos'][1], $jpl_pos['pos'][1] * 149597870.7);
printf("  Z: %12.6f AU = %15.0f km\n", $jpl_pos['pos'][2], $jpl_pos['pos'][2] * 149597870.7);
$jpl_dist = sqrt($jpl_pos['pos'][0]**2 + $jpl_pos['pos'][1]**2 + $jpl_pos['pos'][2]**2);
printf("  Distance: %12.6f AU = %15.0f km\n\n", $jpl_dist, $jpl_dist * 149597870.7);

echo "EPM2021 Jupiter position (barycentric):\n";
printf("  X: %12.6f AU = %15.0f km\n", $epm_pos['pos'][0], $epm_pos['pos'][0] * 149597870.7);
printf("  Y: %12.6f AU = %15.0f km\n", $epm_pos['pos'][1], $epm_pos['pos'][1] * 149597870.7);
printf("  Z: %12.6f AU = %15.0f km\n", $epm_pos['pos'][2], $epm_pos['pos'][2] * 149597870.7);
$epm_dist = sqrt($epm_pos['pos'][0]**2 + $epm_pos['pos'][1]**2 + $epm_pos['pos'][2]**2);
printf("  Distance: %12.6f AU = %15.0f km\n\n", $epm_dist, $epm_dist * 149597870.7);

$dx = $jpl_pos['pos'][0] - $epm_pos['pos'][0];
$dy = $jpl_pos['pos'][1] - $epm_pos['pos'][1];
$dz = $jpl_pos['pos'][2] - $epm_pos['pos'][2];
$diff = sqrt($dx*$dx + $dy*$dy + $dz*$dz);

echo "Difference JPL-EPM: " . number_format($diff * 149597870.7, 1) . " km\n";
echo "Difference in meters: " . number_format($diff * 149597870700, 1) . " m\n";

