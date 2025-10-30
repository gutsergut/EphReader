<?php
/**
 * Comprehensive Swiss Ephemeris Bodies Test
 * Проверяет все доступные тела: планеты, Хирон, Лунные узлы, Лилит
 */

$dllPath = __DIR__ . '/vendor/swisseph/swedll64.dll';
$ephePath = __DIR__ . '/ephe';

if (!file_exists($dllPath)) {
    die("❌ DLL not found: $dllPath\n");
}

if (!extension_loaded('ffi')) {
    die("❌ FFI extension not loaded\n");
}

try {
    $ffi = FFI::cdef("
        void swe_set_ephe_path(char *path);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        char *swe_get_planet_name(int ipl, char *name);
        void swe_close(void);
    ", $dllPath);

    $ffi->swe_set_ephe_path($ephePath);

    echo "=" . str_repeat("=", 79) . "\n";
    echo "SWISS EPHEMERIS: Complete Body Inventory Test\n";
    echo "=" . str_repeat("=", 79) . "\n\n";

    echo "Test Date: JD 2451545.0 (J2000.0 = 2000-01-01 12:00:00 TT)\n";
    echo "Ephemeris Path: $ephePath\n\n";

    // Define all bodies to test
    $bodies = [
        // Main planets
        ['id' => 0, 'name' => 'Sun', 'constant' => 'SE_SUN'],
        ['id' => 1, 'name' => 'Moon', 'constant' => 'SE_MOON'],
        ['id' => 2, 'name' => 'Mercury', 'constant' => 'SE_MERCURY'],
        ['id' => 3, 'name' => 'Venus', 'constant' => 'SE_VENUS'],
        ['id' => 4, 'name' => 'Mars', 'constant' => 'SE_MARS'],
        ['id' => 5, 'name' => 'Jupiter', 'constant' => 'SE_JUPITER'],
        ['id' => 6, 'name' => 'Saturn', 'constant' => 'SE_SATURN'],
        ['id' => 7, 'name' => 'Uranus', 'constant' => 'SE_URANUS'],
        ['id' => 8, 'name' => 'Neptune', 'constant' => 'SE_NEPTUNE'],
        ['id' => 9, 'name' => 'Pluto', 'constant' => 'SE_PLUTO'],

        // Special points
        ['id' => 10, 'name' => 'Mean Lunar Node', 'constant' => 'SE_MEAN_NODE'],
        ['id' => 11, 'name' => 'True Lunar Node', 'constant' => 'SE_TRUE_NODE'],
        ['id' => 12, 'name' => 'Mean Apogee (Lilith)', 'constant' => 'SE_MEAN_APOG'],
        ['id' => 13, 'name' => 'Osculating Apogee', 'constant' => 'SE_OSCU_APOG'],
        ['id' => 14, 'name' => 'Earth', 'constant' => 'SE_EARTH'],

        // Centaurs and TNOs
        ['id' => 15, 'name' => 'Chiron', 'constant' => 'SE_CHIRON'],
        ['id' => 16, 'name' => 'Pholus', 'constant' => 'SE_PHOLUS'],
        ['id' => 17, 'name' => 'Ceres', 'constant' => 'SE_CERES'],
        ['id' => 18, 'name' => 'Pallas', 'constant' => 'SE_PALLAS'],
        ['id' => 19, 'name' => 'Juno', 'constant' => 'SE_JUNO'],
        ['id' => 20, 'name' => 'Vesta', 'constant' => 'SE_VESTA'],
    ];

    $jd = 2451545.0;
    $iflag = 2 + 256 + 4096; // SEFLG_SWIEPH + SEFLG_SPEED + SEFLG_XYZ

    $available = [];
    $unavailable = [];

    echo "Testing bodies...\n\n";
    echo "┌─────┬────────────────────────┬──────────────┬────────────────────────────────┐\n";
    echo "│ ID  │ Name                   │ Status       │ Position (AU) @ J2000.0        │\n";
    echo "├─────┼────────────────────────┼──────────────┼────────────────────────────────┤\n";

    foreach ($bodies as $body) {
        $id = $body['id'];
        $name = $body['name'];

        $xx = FFI::new("double[6]");
        $serr = FFI::new("char[256]");

        $result = $ffi->swe_calc_ut($jd, $id, $iflag, $xx, $serr);

        if ($result >= 0) {
            // With SEFLG_XYZ, coordinates are already in AU
            $x = $xx[0];
            $y = $xx[1];
            $z = $xx[2];
            $dist = sqrt($x*$x + $y*$y + $z*$z);

            $pos_str = sprintf("[%7.4f, %7.4f, %7.4f]", $x, $y, $z);
            $status = "✅ Available";
            $available[] = ['id' => $id, 'name' => $name, 'dist' => $dist];

            printf("│ %-3d │ %-22s │ %-12s │ %s │\n",
                $id, $name, $status, $pos_str);
        } else {
            $error = FFI::string($serr);
            $status = "❌ Missing";
            $unavailable[] = ['id' => $id, 'name' => $name, 'error' => $error];

            printf("│ %-3d │ %-22s │ %-12s │ %-30s │\n",
                $id, $name, $status, substr($error, 0, 30));
        }
    }

    echo "└─────┴────────────────────────┴──────────────┴────────────────────────────────┘\n\n";

    // Summary
    echo "=" . str_repeat("=", 79) . "\n";
    echo "SUMMARY\n";
    echo "=" . str_repeat("=", 79) . "\n\n";

    echo "✅ Available bodies: " . count($available) . "\n";
    foreach ($available as $body) {
        echo sprintf("   - %s (ID %d): %.4f AU\n", $body['name'], $body['id'], $body['dist']);
    }

    if (!empty($unavailable)) {
        echo "\n❌ Unavailable bodies: " . count($unavailable) . "\n";
        foreach ($unavailable as $body) {
            echo sprintf("   - %s (ID %d): %s\n", $body['name'], $body['id'], $body['error']);
        }
    }

    // Test coordinate systems for one body (Sun)
    echo "\n" . str_repeat("=", 80) . "\n";
    echo "COORDINATE SYSTEMS TEST (Sun)\n";
    echo str_repeat("=", 80) . "\n\n";

    $systems = [
        ['name' => 'Geocentric Cartesian', 'flag' => 2 + 256 + 4096],
        ['name' => 'Geocentric Ecliptic', 'flag' => 2 + 256],
        ['name' => 'Geocentric Equatorial', 'flag' => 2 + 256 + 2048],
        ['name' => 'Heliocentric Cartesian', 'flag' => 8 + 256 + 4096],
        ['name' => 'Barycentric Cartesian', 'flag' => 16384 + 256 + 4096],
    ];

    foreach ($systems as $sys) {
        $xx = FFI::new("double[6]");
        $serr = FFI::new("char[256]");

        $result = $ffi->swe_calc_ut($jd, 0, $sys['flag'], $xx, $serr);

        if ($result >= 0) {
            echo sprintf("%-30s: [%10.6f, %10.6f, %10.6f]\n",
                $sys['name'], $xx[0], $xx[1], $xx[2]);
        }
    }

    $ffi->swe_close();

    echo "\n✅ Test complete!\n";

} catch (Throwable $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    echo "   File: " . $e->getFile() . ":" . $e->getLine() . "\n";
    exit(1);
}
