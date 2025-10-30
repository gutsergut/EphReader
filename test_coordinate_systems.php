<?php
/**
 * Comprehensive Swiss Ephemeris Test
 * Сравнение геоцентрических и барицентрических координат
 */

require_once 'php/src/EphemerisInterface.php';
require_once 'php/src/AbstractEphemeris.php';
require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

function formatVector(array $vec, int $decimals = 3): string {
    return '[' . implode(', ', array_map(fn($v) => number_format($v, $decimals), $vec)) . ']';
}

function vectorMagnitude(array $vec): float {
    return sqrt(array_sum(array_map(fn($v) => $v ** 2, $vec)));
}

function vectorDifference(array $a, array $b): array {
    return [
        $a[0] - $b[0],
        $a[1] - $b[1],
        $a[2] - $b[2],
    ];
}

echo "╔══════════════════════════════════════════════════════════════╗\n";
echo "║  Swiss Ephemeris: Geocentric vs Barycentric Comparison      ║\n";
echo "╚══════════════════════════════════════════════════════════════╝\n\n";

$jd = 2451545.0; // J2000.0
$AU_TO_KM = 149597870.7;

// === FFI Direct Access ===
echo "📡 DIRECT FFI ACCESS (Swiss Ephemeris DLL)\n";
echo str_repeat('─', 64) . "\n";

$dllPath = __DIR__ . '/vendor/swisseph/swedll64.dll';
$ephePath = __DIR__ . '/ephe';

if (!file_exists($dllPath) || !extension_loaded('ffi')) {
    echo "⚠️  FFI not available, skipping direct tests\n\n";
} else {
    $ffi = FFI::cdef("
        void swe_set_ephe_path(char *path);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        void swe_close(void);
    ", $dllPath);

    $ffi->swe_set_ephe_path($ephePath);

    // Test bodies: Sun, Moon, Venus
    $bodies = [
        ['id' => 10, 'ipl' => 0, 'name' => 'Sun'],
        ['id' => 301, 'ipl' => 1, 'name' => 'Moon'],
        ['id' => 2, 'ipl' => 3, 'name' => 'Venus'],
    ];

    foreach ($bodies as $body) {
        echo "\n🌍 {$body['name']} (NAIF {$body['id']}):\n";

        // Geocentric
        $xx_geo = FFI::new("double[6]");
        $serr = FFI::new("char[256]");
        $iflag_geo = 2 + 256; // SEFLG_SWIEPH + SEFLG_SPEED
        $ffi->swe_calc_ut($jd, $body['ipl'], $iflag_geo, $xx_geo, $serr);

        $lon_rad = $xx_geo[0] * M_PI / 180.0;
        $lat_rad = $xx_geo[1] * M_PI / 180.0;
        $dist_km = $xx_geo[2] * $AU_TO_KM;

        $pos_geo = [
            $dist_km * cos($lat_rad) * cos($lon_rad),
            $dist_km * cos($lat_rad) * sin($lon_rad),
            $dist_km * sin($lat_rad),
        ];

        echo "  Geocentric:   " . formatVector($pos_geo) . " km\n";
        echo "                Distance: " . number_format(vectorMagnitude($pos_geo) / 1000, 0) . " thousand km\n";

        // Barycentric (inverted for Sun, unchanged for planets/Moon)
        $pos_bary = array_map(fn($v) => -$v, $pos_geo);
        echo "  Barycentric:  " . formatVector($pos_bary) . " km\n";
        echo "                Distance: " . number_format(vectorMagnitude($pos_bary) / 1000, 0) . " thousand km\n";
    }

    $ffi->swe_close();
}

// === .eph File Tests ===
echo "\n\n📂 .EPH FILE TESTS\n";
echo str_repeat('─', 64) . "\n";

$geoFile = 'data/ephemerides/swisseph/swisseph_geocentric.eph';
$baryFile = 'data/ephemerides/swisseph/swisseph_barycentric.eph';

$testBodies = [10, 301]; // Sun, Moon

if (file_exists($geoFile)) {
    echo "\n✅ Geocentric .eph file found: " . basename($geoFile) . "\n";
    echo "   Size: " . round(filesize($geoFile) / 1024, 2) . " KB\n";

    $reader_geo = new EphReader($geoFile);

    foreach ($testBodies as $bodyId) {
        $bodyName = $bodyId === 10 ? 'Sun' : 'Moon';
        $result = $reader_geo->compute($bodyId, $jd);

        echo "\n   {$bodyName} (ID {$bodyId}):\n";
        echo "     Position: " . formatVector($result['pos']) . " km\n";
        echo "     Velocity: " . formatVector($result['vel'], 6) . " km/day\n";
        echo "     Distance: " . number_format(vectorMagnitude($result['pos']) / 1000, 0) . " thousand km\n";
    }
} else {
    echo "\n⚠️  Geocentric .eph file not found: $geoFile\n";
    echo "   Create with: python tools/swisseph_ffi2eph.py --frame geocentric\n";
}

if (file_exists($baryFile)) {
    echo "\n✅ Barycentric .eph file found: " . basename($baryFile) . "\n";
    echo "   Size: " . round(filesize($baryFile) / 1024, 2) . " KB\n";

    $reader_bary = new EphReader($baryFile);

    foreach ($testBodies as $bodyId) {
        $bodyName = $bodyId === 10 ? 'Sun' : 'Moon';
        $result = $reader_bary->compute($bodyId, $jd);

        echo "\n   {$bodyName} (ID {$bodyId}):\n";
        echo "     Position: " . formatVector($result['pos']) . " km\n";
        echo "     Velocity: " . formatVector($result['vel'], 6) . " km/day\n";
        echo "     Distance: " . number_format(vectorMagnitude($result['pos']) / 1000, 0) . " thousand km\n";
    }
} else {
    echo "\n⚠️  Barycentric .eph file not found: $baryFile\n";
    echo "   Create with: python tools/swisseph_ffi2eph.py --frame barycentric\n";
}

// === Cross-validation ===
if (file_exists($geoFile) && file_exists($baryFile) && isset($ffi)) {
    echo "\n\n🔬 CROSS-VALIDATION\n";
    echo str_repeat('─', 64) . "\n";

    $reader_geo = new EphReader($geoFile);
    $reader_bary = new EphReader($baryFile);

    foreach ($testBodies as $bodyId) {
        $bodyName = $bodyId === 10 ? 'Sun' : 'Moon';

        $geo_eph = $reader_geo->compute($bodyId, $jd);
        $bary_eph = $reader_bary->compute($bodyId, $jd);

        // Expected: bary = -geo (for simple inversion)
        $expected_bary = array_map(fn($v) => -$v, $geo_eph['pos']);
        $diff = vectorDifference($expected_bary, $bary_eph['pos']);
        $error_km = vectorMagnitude($diff);

        echo "\n{$bodyName} coordinate inversion check:\n";
        echo "  Geocentric .eph:  " . formatVector($geo_eph['pos']) . " km\n";
        echo "  Barycentric .eph: " . formatVector($bary_eph['pos']) . " km\n";
        echo "  Expected (inv):   " . formatVector($expected_bary) . " km\n";
        echo "  Error:            " . number_format($error_km, 3) . " km";

        if ($error_km < 1000) {
            echo " ✅ Excellent\n";
        } elseif ($error_km < 10000) {
            echo " ⚠️  Acceptable\n";
        } else {
            echo " ❌ Poor\n";
        }
    }
}

echo "\n\n╔══════════════════════════════════════════════════════════════╗\n";
echo "║  Test Complete                                               ║\n";
echo "╚══════════════════════════════════════════════════════════════╝\n";
