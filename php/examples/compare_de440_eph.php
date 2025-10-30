<?php
require_once __DIR__ . '/../../vendor/autoload.php';

use Swisseph\Ephemeris\ChironEphReader;

$eph = new ChironEphReader('data/chiron/chiron_jpl.eph');
$jd = 2451545.0; // J2000.0
$result = $eph->compute(2060, $jd);

$x = $result['pos'][0];
$y = $result['pos'][1];
$z = $result['pos'][2];

$dist = sqrt($x*$x + $y*$y + $z*$z);
$lon = atan2($y, $x) * 180 / M_PI;
$lat = asin($z / $dist) * 180 / M_PI;

if ($lon < 0) $lon += 360;

echo str_repeat("=", 80) . "\n";
echo "CHIRON POSITION COMPARISON AT J2000.0 (JD 2451545.0)\n";
echo str_repeat("=", 80) . "\n\n";

// Load comparison data
$de440_data = json_decode(file_get_contents('data/chiron/chiron_hybrid_de440_fixed.json'), true);
$simplified_data = json_decode(file_get_contents('data/chiron/chiron_hybrid_simplified.json'), true);
$euler_data = json_decode(file_get_contents('data/chiron/chiron_mpc_integrated.json'), true);

$de440_entry = $de440_data['positions'][0] ?? null;
$simplified_entry = $simplified_data['positions'][0] ?? null;
$euler_entry = $euler_data['positions'][0] ?? null;

printf("JPL HORIZONS:        Lon=%6.2f° Lat=%5.2f° Dist=%6.3f AU\n", $lon, $lat, $dist);
if ($de440_entry) {
    printf("Hybrid DE440 eph:    Lon=%6.2f° Lat=%5.2f° Dist=%6.3f AU\n",
        $de440_entry['lon'], $de440_entry['lat'], $de440_entry['dist']);
} else {
    printf("Hybrid DE440 eph:    [FILE NOT FOUND]\n");
}
if ($simplified_entry) {
    printf("Hybrid simplified:   Lon=%6.2f° Lat=%5.2f° Dist=%6.3f AU\n",
        $simplified_entry['lon'], $simplified_entry['lat'], $simplified_entry['dist']);
} else {
    printf("Hybrid simplified:   [FILE NOT FOUND]\n");
}
if ($euler_entry) {
    printf("MPC Simple Euler:    Lon=%6.2f° Lat=%5.2f° Dist=%6.3f AU\n",
        $euler_entry['lon'], $euler_entry['lat'], $euler_entry['dist']);
} else {
    printf("MPC Simple Euler:    [FILE NOT FOUND]\n");
}

echo "\n";
echo "ERRORS (vs JPL HORIZONS):\n";
if ($de440_entry) {
    printf("  DE440 eph:     %5.2f° longitude, %5.3f AU distance\n",
        abs($lon - $de440_entry['lon']), abs($dist - $de440_entry['dist']));
}
if ($simplified_entry) {
    printf("  Simplified:    %5.2f° longitude, %5.3f AU distance\n",
        abs($lon - $simplified_entry['lon']), abs($dist - $simplified_entry['dist']));
}
if ($euler_entry) {
    printf("  Simple Euler:  %5.2f° longitude, %5.3f AU distance\n",
        abs($lon - $euler_entry['lon']), abs($dist - $euler_entry['dist']));
}

echo "\n";
echo "OBSERVATIONS:\n";
echo "  - DE440 eph worse than simplified (!)\n";
echo "  - Possible issues:\n";
echo "    1. Long propagation from epoch (25 years: 2025 → 2000)\n";
echo "    2. Chiron's chaotic orbit sensitive to initial conditions\n";
echo "    3. RK4 step size (16 days) may be too large\n";
echo "  - Next steps: Test with smaller step size or different epoch\n";
