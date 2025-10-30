<?php

/**
 * Chiron ephemeris test - demonstrates reading Chiron positions from binary .eph file.
 */

require_once __DIR__ . '/../src/EphReader.php';
require_once __DIR__ . '/../src/ChironEphReader.php';

use Swisseph\Ephemeris\ChironEphReader;

echo "=" . str_repeat("=", 69) . "\n";
echo "Chiron Ephemeris Test\n";
echo "=" . str_repeat("=", 69) . "\n\n";

// Open Chiron ephemeris file
$eph_file = __DIR__ . '/../../data/chiron/chiron_jpl.eph';

if (!file_exists($eph_file)) {
    die("ERROR: Chiron ephemeris file not found: {$eph_file}\n");
}

echo "Opening: {$eph_file}\n\n";

try {
    $reader = new ChironEphReader($eph_file);

    // Test epochs
    $test_epochs = [
        ['name' => 'J2000.0', 'jd' => 2451545.0],
        ['name' => '2010-01-01', 'jd' => 2455197.5],
        ['name' => '2020-01-01', 'jd' => 2458849.5],
        ['name' => '1990-01-01', 'jd' => 2447892.5],
    ];

    echo "Computing Chiron positions:\n";
    echo str_repeat("-", 70) . "\n\n";

    foreach ($test_epochs as $epoch) {
        $jd = $epoch['jd'];
        $name = $epoch['name'];

        try {
            $result = $reader->compute(ChironEphReader::BODY_CHIRON, $jd);

            $x = $result['pos'][0];
            $y = $result['pos'][1];
            $z = $result['pos'][2];

            $vx = $result['vel'][0];
            $vy = $result['vel'][1];
            $vz = $result['vel'][2];

            // Compute distance from Sun
            $distance = sqrt($x * $x + $y * $y + $z * $z);

            // Compute speed
            $speed = sqrt($vx * $vx + $vy * $vy + $vz * $vz);

            echo "Epoch: {$name} (JD {$jd})\n";
            echo "  Position (AU):\n";
            echo sprintf("    X = %+.8f\n", $x);
            echo sprintf("    Y = %+.8f\n", $y);
            echo sprintf("    Z = %+.8f\n", $z);
            echo sprintf("    Distance from Sun = %.6f AU (%.2f million km)\n",
                $distance, $distance * 149.597871);
            echo "  Velocity (AU/day):\n";
            echo sprintf("    VX = %+.10f\n", $vx);
            echo sprintf("    VY = %+.10f\n", $vy);
            echo sprintf("    VZ = %+.10f\n", $vz);
            echo sprintf("    Speed = %.10f AU/day (%.2f km/s)\n",
                $speed, $speed * 149597870.7 / 86400);
            echo "\n";

        } catch (\Exception $e) {
            echo "ERROR at epoch {$name}: {$e->getMessage()}\n\n";
        }
    }

    echo str_repeat("=", 70) . "\n";
    echo "TEST COMPLETE\n";
    echo str_repeat("=", 70) . "\n";

} catch (\Exception $e) {
    die("ERROR: {$e->getMessage()}\n");
}
