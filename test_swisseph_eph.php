<?php
/**
 * Тест Swiss Ephemeris .eph через Universal Adapter
 */

require_once 'php/src/EphemerisInterface.php';
require_once 'php/src/AbstractEphemeris.php';
require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

$ephFile = 'data/ephemerides/swisseph/swisseph_sun_moon_fixed.eph';

if (!file_exists($ephFile)) {
    echo "❌ File not found: $ephFile\n";
    exit(1);
}

try {
    echo "🔍 Testing Swiss Ephemeris .eph file\n";
    echo "   File: $ephFile\n";
    echo "   Size: " . round(filesize($ephFile) / 1024, 2) . " KB\n\n";

    $reader = new EphReader($ephFile);    echo "📊 File info:\n";
    echo "   Format: Binary .eph\n";
    echo "   Reader: " . get_class($reader) . "\n\n";

    // Тест: вычислить положение Солнца и Луны на J2000.0
    $jd = 2451545.0;

    echo "🌞 Testing Sun position (body 10) at JD $jd (J2000.0):\n";
    $sunResult = $reader->compute(10, $jd);
    echo "   Position: [" . implode(', ', array_map(fn($v) => number_format($v, 3), $sunResult['pos'])) . "] km\n";
    echo "   Velocity: [" . implode(', ', array_map(fn($v) => number_format($v, 6), $sunResult['vel'])) . "] km/day\n";
    echo "   Distance: " . number_format(sqrt(array_sum(array_map(fn($v) => $v**2, $sunResult['pos']))) / 149597870.7, 9) . " AU\n\n";

    echo "🌙 Testing Moon position (body 301) at JD $jd:\n";
    $moonResult = $reader->compute(301, $jd);
    echo "   Position: [" . implode(', ', array_map(fn($v) => number_format($v, 3), $moonResult['pos'])) . "] km\n";
    echo "   Velocity: [" . implode(', ', array_map(fn($v) => number_format($v, 6), $moonResult['vel'])) . "] km/day\n";
    echo "   Distance: " . number_format(sqrt(array_sum(array_map(fn($v) => $v**2, $moonResult['pos']))) / 1000, 3) . " thousand km\n\n";

    // Сравним с прямым FFI вызовом
    echo "🔬 Comparison with direct Swiss Ephemeris FFI:\n";

    $dllPath = __DIR__ . '/vendor/swisseph/swedll64.dll';
    $ephePath = __DIR__ . '/ephe';

    if (file_exists($dllPath) && extension_loaded('ffi')) {
        $ffi = FFI::cdef("
            void swe_set_ephe_path(char *path);
            int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
            void swe_close(void);
        ", $dllPath);

        $ffi->swe_set_ephe_path($ephePath);

        // Sun (ipl=0)
        $xx = FFI::new("double[6]");
        $serr = FFI::new("char[256]");
        $ffi->swe_calc_ut($jd, 0, 2 + 256, $xx, $serr);

        $AU_TO_KM = 149597870.7;
        $lon_rad = $xx[0] * M_PI / 180.0;
        $lat_rad = $xx[1] * M_PI / 180.0;
        $dist_km = $xx[2] * $AU_TO_KM;

        $ffi_sun_pos = [
            $dist_km * cos($lat_rad) * cos($lon_rad),
            $dist_km * cos($lat_rad) * sin($lon_rad),
            $dist_km * sin($lat_rad),
        ];

        echo "   FFI Sun position:  [" . implode(', ', array_map(fn($v) => number_format($v, 3), $ffi_sun_pos)) . "] km\n";
        echo "   .eph Sun position: [" . implode(', ', array_map(fn($v) => number_format($v, 3), $sunResult['pos'])) . "] km\n";

        $diff = sqrt(array_sum(array_map(fn($a, $b) => ($a - $b)**2, $ffi_sun_pos, $sunResult['pos'])));
        echo "   Difference: " . number_format($diff, 3) . " km\n";

        if ($diff < 1000) {
            echo "   ✅ Excellent agreement (<1000 km)\n";
        } elseif ($diff < 10000) {
            echo "   ⚠️  Good agreement (<10,000 km)\n";
        } else {
            echo "   ❌ Poor agreement (>{$diff} km)\n";
        }

        $ffi->swe_close();
    } else {
        echo "   (FFI comparison skipped - DLL or FFI not available)\n";
    }

    echo "\n✅ Swiss Ephemeris .eph test complete!\n";

} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    echo "   File: " . $e->getFile() . ":" . $e->getLine() . "\n";
    exit(1);
}
