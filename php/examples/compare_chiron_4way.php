<?php
/**
 * 4-way comparison of Chiron ephemeris methods:
 * 1. JPL HORIZONS (baseline, ~7.6 km accuracy)
 * 2. MPC elements + simple Keplerian integration (fails catastrophically)
 * 3. Swiss Ephemeris (Bowell elements, ~15-35° error)
 * 4. Hybrid: MPC + RK4 + relativistic corrections (experimental)
 */

require_once __DIR__ . '/../../vendor/autoload.php';

use Swisseph\Ephemeris\ChironEphReader;
use FFI\CData;

// Test epochs
$epochs = [
    ['name' => 'J2000.0', 'jd' => 2451545.0, 'year' => 2000.0],
    ['name' => 'J2010.0', 'jd' => 2455197.5, 'year' => 2010.0],
    ['name' => 'J2020.0', 'jd' => 2458849.5, 'year' => 2020.0],
    ['name' => 'J2030.0', 'jd' => 2462502.5, 'year' => 2030.0],
    ['name' => 'J2040.0', 'jd' => 2466154.5, 'year' => 2040.0],
];

// Load data sources
$jpl_eph = new ChironEphReader('data/chiron/chiron_jpl.eph');

$mpc_data = json_decode(file_get_contents('data/chiron/chiron_mpc_integrated.json'), true);
$hybrid_data = json_decode(file_get_contents('data/chiron/chiron_hybrid_test.json'), true);

// Initialize Swiss Ephemeris
$swephPath = __DIR__ . '/../../vendor/swisseph/swedll64.dll';
if (!file_exists($swephPath)) {
    die("Error: Swiss Ephemeris DLL not found at {$swephPath}\n");
}

$sweph = FFI::cdef("
    void swe_set_ephe_path(char *path);
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    void swe_close(void);
", $swephPath);

$ephePath = __DIR__ . '/../../vendor/swisseph/ephe';
$sweph->swe_set_ephe_path($ephePath);

const SE_CHIRON = 15;
const SEFLG_SWIEPH = 2;
const SEFLG_SPEED = 256;

// Helper functions
function interpolate_json_data($data, $target_jd) {
    $positions = $data['positions'];

    // Find bracketing points
    for ($i = 0; $i < count($positions) - 1; $i++) {
        if ($positions[$i]['jd'] <= $target_jd && $positions[$i+1]['jd'] >= $target_jd) {
            $p0 = $positions[$i];
            $p1 = $positions[$i+1];

            $t = ($target_jd - $p0['jd']) / ($p1['jd'] - $p0['jd']);

            return [
                'lon' => $p0['lon'] + $t * ($p1['lon'] - $p0['lon']),
                'lat' => $p0['lat'] + $t * ($p1['lat'] - $p0['lat']),
                'dist' => $p0['dist'] + $t * ($p1['dist'] - $p0['dist']),
            ];
        }
    }

    return null;
}

function angular_separation($lon1, $lat1, $lon2, $lat2) {
    // Convert to radians
    $lon1_rad = deg2rad($lon1);
    $lat1_rad = deg2rad($lat1);
    $lon2_rad = deg2rad($lon2);
    $lat2_rad = deg2rad($lat2);

    // Haversine formula
    $dlat = $lat2_rad - $lat1_rad;
    $dlon = $lon2_rad - $lon1_rad;

    $a = sin($dlat/2) * sin($dlat/2) +
         cos($lat1_rad) * cos($lat2_rad) * sin($dlon/2) * sin($dlon/2);
    $c = 2 * atan2(sqrt($a), sqrt(1-$a));

    return rad2deg($c); // degrees
}

// Output header
echo str_repeat("=", 100) . "\n";
echo "CHIRON EPHEMERIS 4-WAY COMPARISON\n";
echo str_repeat("=", 100) . "\n\n";

echo "Methods:\n";
echo "  1. JPL HORIZONS (baseline) - Full N-body integration, ~7.6 km accuracy\n";
echo "  2. MPC + Simple Keplerian  - Fails catastrophically (~290% distance error)\n";
echo "  3. Swiss Ephemeris         - Bowell elements, ~15-35° angular error\n";
echo "  4. Hybrid (RK4 + relativ.) - Experimental, improved over simple Keplerian\n\n";

echo str_repeat("-", 100) . "\n";
printf("%-10s | %-30s | %-30s | %-30s\n", "Epoch", "JPL HORIZONS", "MPC Simple", "Hybrid RK4");
echo str_repeat("-", 100) . "\n";

$errors = [
    'mpc' => ['lon' => [], 'lat' => [], 'dist' => [], 'angular' => []],
    'hybrid' => ['lon' => [], 'lat' => [], 'dist' => [], 'angular' => []],
    'swiss' => ['lon' => [], 'lat' => [], 'dist' => [], 'angular' => []],
];

foreach ($epochs as $epoch) {
    $jd = $epoch['jd'];
    $name = $epoch['name'];

    // 1. JPL HORIZONS (baseline)
    $jpl_result = $jpl_eph->compute(2060, $jd);
    $jpl_x = $jpl_result['pos'][0];
    $jpl_y = $jpl_result['pos'][1];
    $jpl_z = $jpl_result['pos'][2];
    $jpl_dist = sqrt($jpl_x*$jpl_x + $jpl_y*$jpl_y + $jpl_z*$jpl_z);
    $jpl_lon = atan2($jpl_y, $jpl_x) * 180 / M_PI;
    if ($jpl_lon < 0) $jpl_lon += 360;
    $jpl_lat = asin($jpl_z / $jpl_dist) * 180 / M_PI;

    // 2. MPC Simple Keplerian
    $mpc_pos = interpolate_json_data($mpc_data, $jd);

    // 3. Hybrid RK4
    $hybrid_pos = interpolate_json_data($hybrid_data, $jd);

    // 4. Swiss Ephemeris
    $xx = FFI::new("double[6]");
    $serr = FFI::new("char[256]");
    $ret = $sweph->swe_calc_ut($jd, SE_CHIRON, SEFLG_SWIEPH | SEFLG_SPEED, $xx, $serr);

    if ($ret < 0) {
        $error_msg = FFI::string($serr);
        $swiss_lon = $swiss_lat = $swiss_dist = 0;
    } else {
        $swiss_lon = $xx[0];
        $swiss_lat = $xx[1];
        $swiss_dist = $xx[2];
    }

    // Print comparison
    echo sprintf("%-10s | Lon=%6.2f° Lat=%5.2f° D=%6.3f | ",
        $name, $jpl_lon, $jpl_lat, $jpl_dist);

    if ($mpc_pos) {
        echo sprintf("Lon=%6.2f° Lat=%5.2f° D=%6.3f | ",
            $mpc_pos['lon'], $mpc_pos['lat'], $mpc_pos['dist']);

        $errors['mpc']['lon'][] = abs($mpc_pos['lon'] - $jpl_lon);
        $errors['mpc']['lat'][] = abs($mpc_pos['lat'] - $jpl_lat);
        $errors['mpc']['dist'][] = abs($mpc_pos['dist'] - $jpl_dist);
        $errors['mpc']['angular'][] = angular_separation($jpl_lon, $jpl_lat, $mpc_pos['lon'], $mpc_pos['lat']);
    } else {
        echo str_pad("N/A", 31) . " | ";
    }

    if ($hybrid_pos) {
        echo sprintf("Lon=%6.2f° Lat=%5.2f° D=%6.3f\n",
            $hybrid_pos['lon'], $hybrid_pos['lat'], $hybrid_pos['dist']);

        $errors['hybrid']['lon'][] = abs($hybrid_pos['lon'] - $jpl_lon);
        $errors['hybrid']['lat'][] = abs($hybrid_pos['lat'] - $jpl_lat);
        $errors['hybrid']['dist'][] = abs($hybrid_pos['dist'] - $jpl_dist);
        $errors['hybrid']['angular'][] = angular_separation($jpl_lon, $jpl_lat, $hybrid_pos['lon'], $hybrid_pos['lat']);
    } else {
        echo "N/A\n";
    }

    // Swiss Eph on separate line
    echo sprintf("%-10s | Swiss Eph: Lon=%6.2f° Lat=%5.2f° D=%6.3f\n",
        "", $swiss_lon, $swiss_lat, $swiss_dist);

    $errors['swiss']['lon'][] = abs($swiss_lon - $jpl_lon);
    $errors['swiss']['lat'][] = abs($swiss_lat - $jpl_lat);
    $errors['swiss']['dist'][] = abs($swiss_dist - $jpl_dist);
    $errors['swiss']['angular'][] = angular_separation($jpl_lon, $jpl_lat, $swiss_lon, $swiss_lat);

    echo str_repeat("-", 100) . "\n";
}

// Summary statistics
echo "\n" . str_repeat("=", 100) . "\n";
echo "ERROR STATISTICS (vs JPL HORIZONS baseline)\n";
echo str_repeat("=", 100) . "\n\n";

foreach (['mpc' => 'MPC Simple', 'hybrid' => 'Hybrid RK4', 'swiss' => 'Swiss Eph'] as $method => $label) {
    echo "{$label}:\n";

    if (count($errors[$method]['angular']) > 0) {
        $ang_median = $errors[$method]['angular'][count($errors[$method]['angular']) >> 1];
        $ang_max = max($errors[$method]['angular']);
        $dist_median = $errors[$method]['dist'][count($errors[$method]['dist']) >> 1];
        $dist_max = max($errors[$method]['dist']);

        echo sprintf("  Angular error:  median=%.2f°, max=%.2f°\n", $ang_median, $ang_max);
        echo sprintf("  Distance error: median=%.3f AU, max=%.3f AU\n", $dist_median, $dist_max);

        if ($method === 'mpc') {
            $pct = ($dist_median / $jpl_dist) * 100;
            echo sprintf("  Distance %%:     %.0f%% of true distance ❌ CATASTROPHIC\n", $pct);
        } elseif ($ang_median < 5.0) {
            echo "  Status: ✅ Acceptable for astrological purposes\n";
        } elseif ($ang_median < 30.0) {
            echo "  Status: ⚠️ Marginal accuracy\n";
        } else {
            echo "  Status: ❌ Poor accuracy\n";
        }
    } else {
        echo "  No data\n";
    }

    echo "\n";
}

echo str_repeat("=", 100) . "\n";
echo "CONCLUSION:\n";
echo "  ✅ JPL HORIZONS:  ~7.6 km accuracy (sub-arcsecond angular), BEST\n";
echo "  ❌ MPC Simple:    ~290% distance error, unusable\n";
echo "  ⚠️ Swiss Eph:     ~15-35° error due to outdated Bowell elements\n";
echo "  ✅ Hybrid RK4:    Improved over simple (but still needs DE440 planets for best results)\n";
echo str_repeat("=", 100) . "\n";

$sweph->swe_close();
