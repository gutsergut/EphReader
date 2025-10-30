<?php
/**
 * Comprehensive ephemeris accuracy comparison.
 *
 * Compares geocentric ecliptic longitude accuracy across:
 * - JPL DE440 (NASA, reference/gold standard) - via Swiss Ephemeris
 * - EPM2021 (IAA RAS, Russian high-precision)
 * - Swiss Ephemeris (based on JPL DE440/DE431)
 *
 * NOTE: Swiss Ephemeris USES JPL DE440 data internally, making this
 * effectively a direct comparison: EPM2021 vs JPL DE440.
 *
 * Uses ANGULAR SEPARATION (arcseconds) as primary metric.
 *
 * Author: AI Assistant
 * Date: 2025-10-30
 */

// Load Swiss Ephemeris via FFI
$swissephDll = __DIR__ . '/../../vendor/swisseph/swedll64.dll';
if (!file_exists($swissephDll)) {
    die("ERROR: Swiss Ephemeris DLL not found: $swissephDll\n");
}

$ffi = FFI::cdef("
    void swe_set_ephe_path(char *path);
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    int swe_calc(double tjd_et, int ipl, int iflag, double *xx, char *serr);
    double swe_deltat(double tjd_ut);
    void swe_close(void);
", $swissephDll);

// Set ephemeris path
$ephePath = __DIR__ . '/../../ephe';
$ffi->swe_set_ephe_path($ephePath);

// Swiss Ephemeris constants
const SE_SUN = 0;
const SE_MOON = 1;
const SE_MERCURY = 2;
const SE_VENUS = 3;
const SE_MARS = 4;
const SE_JUPITER = 5;
const SE_SATURN = 6;
const SE_URANUS = 7;
const SE_NEPTUNE = 8;
const SE_PLUTO = 9;

const SEFLG_SWIEPH = 2;      // Use Swiss Ephemeris files
const SEFLG_SPEED = 256;     // Calculate velocity

// Body mapping
$bodies = [
    'Sun' => SE_SUN,
    'Moon' => SE_MOON,
    'Mercury' => SE_MERCURY,
    'Venus' => SE_VENUS,
    'Mars' => SE_MARS,
    'Jupiter' => SE_JUPITER,
    'Saturn' => SE_SATURN,
    'Uranus' => SE_URANUS,
    'Neptune' => SE_NEPTUNE,
    'Pluto' => SE_PLUTO,
];

// Test epochs
$testEpochs = [
    ['J1900.0', 2415020.0],
    ['J1950.0', 2433282.5],
    ['J2000.0', 2451545.0],
    ['2010-01-01', 2455197.5],
    ['2020-01-01', 2458849.5],
    ['2030-01-01', 2462502.5],
    ['2050-01-01', 2469807.5],
];

// Load autoloader
require_once __DIR__ . '/../../vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\TimeScaleConverter;

$de440File = __DIR__ . '/../../data/ephemerides/jpl/de440/de440.eph';
$epm2021File = __DIR__ . '/../../data/ephemerides/epm/2021/epm2021.eph';

$hasDE440 = false;
$hasEPM2021 = false;
$hasSwissEph = true;  // FFI loaded above

echo "Loading ephemerides...\n";

if (file_exists($de440File)) {
    try {
        $de440 = new EphReader($de440File);
        $hasDE440 = true;
        $size = round(filesize($de440File) / 1024 / 1024, 1);
        echo "✓ Loaded JPL DE440 (DIRECT): {$size} MB\n";
    } catch (Exception $e) {
        echo "⚠ Failed to load DE440: " . $e->getMessage() . "\n";
    }
} else {
    echo "⚠ JPL DE440 not found: $de440File\n";
    echo "  Run: python tools/spice2eph.py data/ephemerides/jpl/de440/de440.bsp data/ephemerides/jpl/de440/de440.eph\n";
}

if (file_exists($epm2021File)) {
    try {
        $epm2021 = new EphReader($epm2021File);
        $hasEPM2021 = true;
        echo "✓ Loaded EPM2021: $epm2021File\n";
    } catch (Exception $e) {
        echo "⚠ Failed to load EPM2021: " . $e->getMessage() . "\n";
    }
}

echo "\n";

/**
 * Compute geocentric ecliptic coordinates from Swiss Ephemeris.
 *
 * NOTE: JPL ephemerides use TDB (Barycentric Dynamical Time).
 * Swiss Eph swe_calc() expects ET (Ephemeris Time ≈ TDB for our purposes).
 * We use swe_calc() directly with JD assuming it's already in TDB/ET.
 */
function computeSwissEph($ffi, int $bodyId, float $jd): ?array
{
    $xx = FFI::new("double[6]");
    $serr = FFI::new("char[256]");

    // Calculate geocentric ecliptic coordinates
    // Use swe_calc() with TDB/ET time (NOT swe_calc_ut() which expects UT)
    // Default flags return ecliptic lon/lat/dist
    $ret = $ffi->swe_calc($jd, $bodyId, SEFLG_SWIEPH | SEFLG_SPEED,
                          FFI::addr($xx[0]), FFI::addr($serr[0]));

    if ($ret < 0) {
        $error = FFI::string($serr);
        echo "    Swiss Eph error: $error\n";
        return null;
    }

    return [
        'lon' => $xx[0],  // Ecliptic longitude (degrees)
        'lat' => $xx[1],  // Ecliptic latitude (degrees)
        'dist' => $xx[2], // Distance (AU)
        'dlon' => $xx[3], // Longitude velocity (deg/day)
    ];
}

/**
 * Compute geocentric ecliptic coordinates from CALCEPH ephemeris.
 */
function computeFromEph(EphReader $eph, int $naifId, float $jd): ?array
{
    try {
        // Special handling for Sun and Moon
        if ($naifId === 10) {
            // Sun: invert Earth position to get geocentric Sun
            $posEarth = $eph->compute(399, $jd);
            if (!$posEarth) return null;

            $dx = -$posEarth['pos'][0];
            $dy = -$posEarth['pos'][1];
            $dz = -$posEarth['pos'][2];
        } elseif ($naifId === 301) {
            // Moon: geocentric position is Moon - Earth
            $posMoon = $eph->compute(301, $jd);
            $posEarth = $eph->compute(399, $jd);

            if (!$posMoon || !$posEarth) return null;

            $dx = $posMoon['pos'][0] - $posEarth['pos'][0];
            $dy = $posMoon['pos'][1] - $posEarth['pos'][1];
            $dz = $posMoon['pos'][2] - $posEarth['pos'][2];
        } else {
            // Planets: geocentric = heliocentric_planet - heliocentric_earth
            $posBody = $eph->compute($naifId, $jd);
            $posEarth = $eph->compute(399, $jd);

            if (!$posBody || !$posEarth) return null;

            $dx = $posBody['pos'][0] - $posEarth['pos'][0];
            $dy = $posBody['pos'][1] - $posEarth['pos'][1];
            $dz = $posBody['pos'][2] - $posEarth['pos'][2];
        }

        // Convert Cartesian equatorial (ICRF) to ecliptic coordinates
        // Apply obliquity of ecliptic (J2000): ε = 23.43929111°
        $epsilon = deg2rad(23.43929111);

        // Rotation matrix from equatorial to ecliptic:
        // x_ecl = x_eq
        // y_ecl = y_eq * cos(ε) + z_eq * sin(ε)
        // z_ecl = -y_eq * sin(ε) + z_eq * cos(ε)
        $x_ecl = $dx;
        $y_ecl = $dy * cos($epsilon) + $dz * sin($epsilon);
        $z_ecl = -$dy * sin($epsilon) + $dz * cos($epsilon);

        // Convert to spherical ecliptic lon/lat
        $lon = rad2deg(atan2($y_ecl, $x_ecl));
        if ($lon < 0) $lon += 360.0;

        $r = sqrt($x_ecl*$x_ecl + $y_ecl*$y_ecl + $z_ecl*$z_ecl);
        $lat = rad2deg(asin($z_ecl / $r));        return [
            'lon' => $lon,
            'lat' => $lat,
            'dist' => $r,
        ];

    } catch (Exception $e) {
        return null;
    }
}/**
 * Calculate angular separation using haversine formula.
 */
function angularSeparation(float $lon1, float $lat1, float $lon2, float $lat2): float
{
    $lon1Rad = deg2rad($lon1);
    $lat1Rad = deg2rad($lat1);
    $lon2Rad = deg2rad($lon2);
    $lat2Rad = deg2rad($lat2);

    $dlat = $lat2Rad - $lat1Rad;
    $dlon = $lon2Rad - $lon1Rad;

    $a = sin($dlat/2) ** 2 + cos($lat1Rad) * cos($lat2Rad) * sin($dlon/2) ** 2;
    $c = 2 * asin(sqrt($a));

    // Convert to arcseconds
    return rad2deg($c) * 3600.0;
}

/**
 * Format angular separation with status.
 */
function formatSeparation(float $arcsec): string
{
    if ($arcsec < 1.0) {
        $status = "✅";
    } elseif ($arcsec < 60.0) {
        $status = "⚠️";
    } else {
        $status = "❌";
    }

    return sprintf("%8.3f\" %s", $arcsec, $status);
}

// NAIF ID mapping
$naifIds = [
    'Sun' => 10,
    'Moon' => 301,
    'Mercury' => 1,
    'Venus' => 2,
    'Mars' => 4,
    'Jupiter' => 5,
    'Saturn' => 6,
    'Uranus' => 7,
    'Neptune' => 8,
    'Pluto' => 9,
];

// Results storage
$resultsSwissVsDE440 = [];
$resultsEPMVsDE440 = [];

echo str_repeat("=", 80) . "\n";
echo "Comprehensive Ephemeris Accuracy Comparison\n";
echo str_repeat("=", 80) . "\n\n";
echo "Metric: Geocentric ecliptic angular separation (arcseconds)\n";
echo "Reference: JPL DE440 (DIRECT from .eph file)\n\n";

foreach ($testEpochs as [$epochName, $jd]) {
    echo "Epoch: $epochName (JD $jd)\n";
    echo str_repeat("-", 80) . "\n";

    foreach ($bodies as $bodyName => $seId) {
        $naifId = $naifIds[$bodyName];

        // Compute DE440 position (REFERENCE)
        $de440Pos = null;
        if ($hasDE440) {
            $de440Pos = computeFromEph($de440, $naifId, $jd);
        }

        if (!$de440Pos) {
            echo sprintf("  %-10s: DE440 unavailable\n", $bodyName);
            continue;
        }

        // Compare EPM2021 vs DE440
        $epmSep = null;
        if ($hasEPM2021) {
            $epmPos = computeFromEph($epm2021, $naifId, $jd);
            if ($epmPos) {
                $epmSep = angularSeparation(
                    $de440Pos['lon'], $de440Pos['lat'],
                    $epmPos['lon'], $epmPos['lat']
                );

                if (!isset($resultsEPMVsDE440[$bodyName])) {
                    $resultsEPMVsDE440[$bodyName] = [];
                }
                $resultsEPMVsDE440[$bodyName][] = $epmSep;
            }
        }

        // Compare Swiss Eph vs DE440
        $swissSep = null;
        if ($hasSwissEph) {
            $swissPos = computeSwissEph($ffi, $seId, $jd);
            if ($swissPos) {
                $swissSep = angularSeparation(
                    $de440Pos['lon'], $de440Pos['lat'],
                    $swissPos['lon'], $swissPos['lat']
                );

                if (!isset($resultsSwissVsDE440[$bodyName])) {
                    $resultsSwissVsDE440[$bodyName] = [];
                }
                $resultsSwissVsDE440[$bodyName][] = $swissSep;
            }
        }

        // Display results
        $line = sprintf("  %-10s: DE440=%7.3f°", $bodyName, $de440Pos['lon']);

        if ($epmSep !== null) {
            $line .= sprintf(" | EPM Δ=%s", formatSeparation($epmSep));
        }

        if ($swissSep !== null) {
            $line .= sprintf(" | Swiss Δ=%s", formatSeparation($swissSep));
        }

        echo "$line\n";
    }

    echo "\n";
}

// Summary statistics
function printSummaryTable(array $results, string $title): void
{
    echo str_repeat("=", 80) . "\n";
    echo "$title\n";
    echo str_repeat("=", 80) . "\n\n";

    if (empty($results)) {
        echo "No data available\n\n";
        return;
    }

    printf("%-12s %8s %10s %10s %10s %s\n",
           'Body', 'Samples', 'Mean', 'Median', 'Max', 'Status');
    echo str_repeat("-", 80) . "\n";

    foreach (['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto'] as $bodyName) {
        if (!isset($results[$bodyName]) || empty($results[$bodyName])) {
            continue;
        }

        $errors = $results[$bodyName];
        $mean = array_sum($errors) / count($errors);

        sort($errors);
        $median = $errors[intval(count($errors) / 2)];
        $max = max($errors);

        // Status
        if ($median < 1.0) {
            $status = "✅ Excellent";
        } elseif ($median < 10.0) {
            $status = "✅ Good";
        } elseif ($median < 60.0) {
            $status = "⚠️ Acceptable";
        } else {
            $status = "❌ Poor";
        }

        printf("%-12s %8d %9.2f\" %9.2f\" %9.2f\" %s\n",
               $bodyName, count($errors), $mean, $median, $max, $status);
    }

    echo "\n";
}

// Print comparison summaries
printSummaryTable($resultsEPMVsDE440, "SUMMARY 1: EPM2021 vs JPL DE440 (DIRECT)");
printSummaryTable($resultsSwissVsDE440, "SUMMARY 2: Swiss Ephemeris vs JPL DE440 (Validation)");

echo str_repeat("=", 80) . "\n";
echo "NOTES\n";
echo str_repeat("=", 80) . "\n";
echo "• JPL DE440 used as reference (NASA gold standard)\n";
echo "• Angular separation measures actual sky position difference\n";
echo "• Arcseconds: < 1\" = Excellent, < 60\" = Good, > 60\" = Poor\n";
echo "• For comparison: Moon diameter ≈ 1800\", Jupiter ≈ 40\"\n";
echo "• Swiss Eph should match DE440 within < 0.1\" (uses same data)\n";
echo "\n";

// Cleanup
$ffi->swe_close();

echo "COMPARISON COMPLETE\n";
