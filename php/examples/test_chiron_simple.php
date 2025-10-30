<?php

/**
 * Simple Chiron ephemeris test - standalone version without dependencies.
 */

echo "=" . str_repeat("=", 69) . "\n";
echo "Chiron Ephemeris Test (Standalone)\n";
echo "=" . str_repeat("=", 69) . "\n\n";

// Constants
const MAGIC = "EPH\0";
const HEADER_SIZE = 512;
const BODY_ENTRY_SIZE = 40;
const INTERVAL_ENTRY_SIZE = 16;
const BODY_CHIRON = 2060;

// Open file
$eph_file = __DIR__ . '/../../data/chiron/chiron_jpl.eph';

if (!file_exists($eph_file)) {
    die("ERROR: File not found: {$eph_file}\n");
}

echo "Opening: {$eph_file}\n";
echo "Size: " . number_format(filesize($eph_file)) . " bytes\n\n";

$fp = fopen($eph_file, 'rb');
if (!$fp) {
    die("ERROR: Cannot open file\n");
}

// Read header
$header_data = fread($fp, HEADER_SIZE);
$header = unpack(
    'a4magic/Vversion/Vnum_bodies/Vnum_intervals/dinterval_days/dstart_jd/dend_jd/Vcoeff_degree',
    $header_data
);

echo "Header:\n";
echo "  Magic: " . bin2hex($header['magic']) . "\n";
echo "  Version: {$header['version']}\n";
echo "  Bodies: {$header['num_bodies']}\n";
echo "  Intervals: {$header['num_intervals']}\n";
echo "  Coverage: {$header['start_jd']} - {$header['end_jd']} JD\n";
echo "  Chebyshev degree: {$header['coeff_degree']}\n\n";

// Read body table
$body_data = fread($fp, BODY_ENTRY_SIZE);
$body = unpack('ibody_id/a28name/Qdata_offset', $body_data);

echo "Body:\n";
echo "  ID: {$body['body_id']}\n";
echo "  Name: " . rtrim($body['name'], "\0") . "\n";
echo "  Data offset: {$body['data_offset']}\n\n";

// Read interval index
$intervals = [];
for ($i = 0; $i < $header['num_intervals']; $i++) {
    $interval_data = fread($fp, INTERVAL_ENTRY_SIZE);
    $interval = unpack('djd_start/djd_end', $interval_data);
    $intervals[] = $interval;
}

echo "First interval: {$intervals[0]['jd_start']} - {$intervals[0]['jd_end']}\n";
echo "Last interval: {$intervals[count($intervals)-1]['jd_start']} - {$intervals[count($intervals)-1]['jd_end']}\n\n";

// Test computation
function findInterval($jd, $intervals) {
    foreach ($intervals as $idx => $interval) {
        if ($jd >= $interval['jd_start'] && $jd <= $interval['jd_end']) {
            return $idx;
        }
    }
    return null;
}

function evaluateChebyshev($coeffs, $x) {
    $n = count($coeffs);
    if ($n === 0) return 0.0;
    if ($n === 1) return $coeffs[0];

    $b_k_plus_2 = 0.0;
    $b_k_plus_1 = 0.0;

    for ($k = $n - 1; $k >= 1; $k--) {
        $b_k = 2.0 * $x * $b_k_plus_1 - $b_k_plus_2 + $coeffs[$k];
        $b_k_plus_2 = $b_k_plus_1;
        $b_k_plus_1 = $b_k;
    }

    return $x * $b_k_plus_1 - $b_k_plus_2 + $coeffs[0];
}

$test_jd = 2451545.0;  // J2000.0
echo "Computing position for JD {$test_jd} (J2000.0):\n";
echo str_repeat("-", 70) . "\n";

$interval_idx = findInterval($test_jd, $intervals);
if ($interval_idx === null) {
    die("ERROR: No interval found for JD {$test_jd}\n");
}

echo "  Found in interval {$interval_idx}\n";

$interval = $intervals[$interval_idx];
$jd_start = $interval['jd_start'];
$jd_end = $interval['jd_end'];

// Normalize time
$t_norm = 2.0 * ($test_jd - $jd_start) / ($jd_end - $jd_start) - 1.0;
echo "  Normalized time: {$t_norm}\n\n";

// Read coefficients
$degree = $header['coeff_degree'];
$coeffs_per_interval = 3 * ($degree + 1);
$bytes_per_interval = $coeffs_per_interval * 8;

$offset = $body['data_offset'] + ($interval_idx * $bytes_per_interval);
fseek($fp, $offset);
$coeff_data = fread($fp, $bytes_per_interval);
$coeffs = unpack("d{$coeffs_per_interval}", $coeff_data);
$coeffs = array_values($coeffs);

$n_per_coord = $degree + 1;
$x_coeffs = array_slice($coeffs, 0, $n_per_coord);
$y_coeffs = array_slice($coeffs, $n_per_coord, $n_per_coord);
$z_coeffs = array_slice($coeffs, 2 * $n_per_coord, $n_per_coord);

$x = evaluateChebyshev($x_coeffs, $t_norm);
$y = evaluateChebyshev($y_coeffs, $t_norm);
$z = evaluateChebyshev($z_coeffs, $t_norm);

$distance = sqrt($x * $x + $y * $y + $z * $z);

echo "  Position:\n";
echo sprintf("    X = %+.8f AU\n", $x);
echo sprintf("    Y = %+.8f AU\n", $y);
echo sprintf("    Z = %+.8f AU\n", $z);
echo sprintf("    Distance from Sun = %.6f AU (%.2f million km)\n\n",
    $distance, $distance * 149.597871);

fclose($fp);

echo "=" . str_repeat("=", 69) . "\n";
echo "TEST SUCCESSFUL\n";
echo "=" . str_repeat("=", 69) . "\n";
