<?php
require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

echo "=== Debug Binary .eph Structure ===\n\n";

// Header
$header = $eph->getMetadata();
echo "Header:\n";
print_r($header);

// Bodies
echo "\n=== Bodies Table ===\n";
$bodies_refl = new ReflectionProperty($eph, 'bodies');
$bodies_refl->setAccessible(true);
$bodies = $bodies_refl->getValue($eph);

foreach ($bodies as $id => $info) {
    printf("Body %3d (%s): offset=%d (0x%X)\n", $id, $info['name'], $info['offset'], $info['offset']);
}

// Check Earth specifically
echo "\n=== Earth (ID 399) at J2000.0 ===\n";
$earth_info = $bodies[399] ?? null;
if ($earth_info) {
    echo "Name: {$earth_info['name']}\n";
    echo "Offset: {$earth_info['offset']} bytes\n";

    // Calculate expected offset
    $num_bodies = $header['numBodies'];
    $num_intervals = $header['numIntervals'];
    $coeffs_per_comp = $header['coeffDegree'] + 1;
    $bytes_per_interval = $coeffs_per_comp * 3 * 8; // 3 components (X,Y,Z), 8 bytes per double

    $header_size = 512;
    $body_table_size = $num_bodies * 36; // 36 bytes per body entry
    $interval_index_size = $num_intervals * 16; // 16 bytes per interval
    $data_section_start = $header_size + $body_table_size + $interval_index_size;

    echo "\nCalculated structure:\n";
    echo "  Header: {$header_size} bytes\n";
    echo "  Body table: {$body_table_size} bytes ({$num_bodies} bodies × 36)\n";
    echo "  Interval index: {$interval_index_size} bytes ({$num_intervals} intervals × 16)\n";
    echo "  Data section starts at: {$data_section_start} bytes\n";
    echo "  Bytes per interval: {$bytes_per_interval} ({$coeffs_per_comp} coeffs × 3 × 8)\n";
}

// Read first coefficient for Earth at interval 2423 (J2000.0)
$result = $eph->compute(399, 2451545.0);
echo "\nComputed result:\n";
printf("Position: X=%.8f, Y=%.8f, Z=%.8f\n", ...$result['pos']);
printf("Velocity: VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result['vel']);
