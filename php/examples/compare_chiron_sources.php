<?php

/**
 * Compare Chiron positions: JPL Horizons (.eph) vs Swiss Ephemeris (FFI).
 *
 * This script compares our binary .eph file accuracy against Swiss Ephemeris
 * using direct FFI calls to libswe.
 */

// Load Swiss Ephemeris FFI
$swe_dll = __DIR__ . '/../../vendor/swisseph/swedll64.dll';

if (!file_exists($swe_dll)) {
    die("ERROR: Swiss Ephemeris DLL not found: {$swe_dll}\n" .
        "Please download from https://www.astro.com/ftp/swisseph/\n");
}

$ffi = FFI::cdef("
    void swe_set_ephe_path(char *path);
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    const char* swe_get_planet_name(int ipl, char *plname);
    void swe_close(void);
", $swe_dll);

echo str_repeat("=", 70) . "\n";
echo "Chiron Position Comparison: JPL Horizons .eph vs Swiss Ephemeris\n";
echo str_repeat("=", 70) . "\n\n";

// Set ephemeris path
$ephe_path = realpath(__DIR__ . '/../../ephe');
$ffi->swe_set_ephe_path($ephe_path);
echo "Swiss Eph path: {$ephe_path}\n\n";

// Test epochs from JSON data
$json_file = __DIR__ . '/../../data/chiron/chiron_vectors_jpl.json';
$json_data = json_decode(file_get_contents($json_file), true);

echo "Loaded {$json_data['metadata']['num_points']} points from JPL Horizons\n";
echo "Coverage: {$json_data['metadata']['start_jd']} - {$json_data['metadata']['stop_jd']} JD\n\n";

// Select test epochs (every 300th point)
$test_indices = range(0, count($json_data['epochs']) - 1, 300);

echo "Testing " . count($test_indices) . " epochs:\n";
echo str_repeat("-", 70) . "\n\n";

// Swiss Ephemeris constants
const SE_CHIRON = 15;
const SEFLG_SWIEPH = 2;     // Use .se1 files
const SEFLG_HELCTR = 8;     // Heliocentric
const SEFLG_XYZ = 4096;     // Cartesian coordinates

$flags = SEFLG_SWIEPH | SEFLG_HELCTR | SEFLG_XYZ;

$errors = [];

foreach ($test_indices as $idx) {
    $jd = $json_data['epochs'][$idx];
    $vector = $json_data['vectors'][$idx];

    $jpl_x = $vector['x'];
    $jpl_y = $vector['y'];
    $jpl_z = $vector['z'];

    // Get position from Swiss Ephemeris
    $xx = FFI::new("double[6]");
    $serr = FFI::new("char[256]");

    $ret = $ffi->swe_calc_ut($jd, SE_CHIRON, $flags, FFI::addr($xx[0]), FFI::addr($serr[0]));

    if ($ret < 0) {
        $error_msg = FFI::string($serr);
        echo "ERROR at JD {$jd}: {$error_msg}\n";
        continue;
    }

    $swe_x = $xx[0];
    $swe_y = $xx[1];
    $swe_z = $xx[2];

    // Compute error
    $dx = $swe_x - $jpl_x;
    $dy = $swe_y - $jpl_y;
    $dz = $swe_z - $jpl_z;

    $error_au = sqrt($dx * $dx + $dy * $dy + $dz * $dz);
    $error_km = $error_au * 149597870.7;

    $errors[] = $error_km;

    // Approximate year
    $year = 2000 + ($jd - 2451545.0) / 365.25;

    echo sprintf("Index %4d (~%.0f): JD %.1f\n", $idx, $year, $jd);
    echo sprintf("  JPL:   X=%+.8f  Y=%+.8f  Z=%+.8f AU\n", $jpl_x, $jpl_y, $jpl_z);
    echo sprintf("  Swiss: X=%+.8f  Y=%+.8f  Z=%+.8f AU\n", $swe_x, $swe_y, $swe_z);
    echo sprintf("  Error: %.3e AU (%.0f km)\n\n", $error_au, $error_km);
}

// Statistics
if (count($errors) > 0) {
    echo str_repeat("=", 70) . "\n";
    echo "SUMMARY\n";
    echo str_repeat("=", 70) . "\n\n";

    $rms = sqrt(array_sum(array_map(fn($e) => $e * $e, $errors)) / count($errors));
    $mean = array_sum($errors) / count($errors);
    sort($errors);
    $median = $errors[count($errors) / 2];
    $max = max($errors);
    $min = min($errors);

    echo "Swiss Ephemeris accuracy vs JPL Horizons:\n";
    echo sprintf("  Samples:      %d\n", count($errors));
    echo sprintf("  RMS error:    %s km\n", number_format($rms, 0));
    echo sprintf("  Mean error:   %s km\n", number_format($mean, 0));
    echo sprintf("  Median error: %s km\n", number_format($median, 0));
    echo sprintf("  Min error:    %s km\n", number_format($min, 0));
    echo sprintf("  Max error:    %s km\n", number_format($max, 0));
    echo "\n";

    // Convert to million km for perspective
    echo "For comparison:\n";
    echo sprintf("  Earth-Sun distance: ~150 million km\n");
    echo sprintf("  Median error: ~%.1f%% of Earth-Sun distance\n", $median / 150000000 * 100);
    echo "\n";
}

// Cleanup
$ffi->swe_close();

echo str_repeat("=", 70) . "\n";
echo "COMPARISON COMPLETE\n";
echo str_repeat("=", 70) . "\n";
