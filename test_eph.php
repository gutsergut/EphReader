<?php
require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

echo "=== Metadata ===\n";
print_r($eph->getMetadata());

echo "\n=== Earth at J2000.0 (JD 2451545.0) ===\n";
$result = $eph->compute(399, 2451545.0);
printf("Position (AU): X=%.8f, Y=%.8f, Z=%.8f\n", ...$result['pos']);
printf("Velocity (AU/day): VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result['vel']);

echo "\nSuccess!\n";
