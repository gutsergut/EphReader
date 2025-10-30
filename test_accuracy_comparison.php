<?php
/**
 * Comprehensive Accuracy Comparison Test
 * Сравнивает точность определения положений планет между:
 * - JPL DE440 (эталон точности)
 * - EPM2021 (российская эфемерида)
 * - Swiss Ephemeris (основана на JPL DE431)
 *
 * Метрики:
 * - Абсолютная погрешность позиции (км)
 * - Относительная погрешность (% от расстояния)
 * - Погрешность скорости (км/день)
 */

require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;

const AU_TO_KM = 149597870.7;
const COLORS = [
    'reset' => "\033[0m",
    'bold' => "\033[1m",
    'green' => "\033[32m",
    'yellow' => "\033[33m",
    'red' => "\033[31m",
    'blue' => "\033[34m",
    'cyan' => "\033[36m",
];

function color($text, $color) {
    return COLORS[$color] . $text . COLORS['reset'];
}

function printHeader($text) {
    $line = str_repeat("=", 80);
    echo "\n" . color($line, 'cyan') . "\n";
    echo color($text, 'bold') . "\n";
    echo color($line, 'cyan') . "\n\n";
}

function printSection($text) {
    echo "\n" . color($text, 'blue') . "\n";
    echo color(str_repeat("-", 80), 'blue') . "\n\n";
}

/**
 * Вычисляет расстояние между двумя позициями (км)
 */
function distance($pos1, $pos2) {
    $dx = $pos1[0] - $pos2[0];
    $dy = $pos1[1] - $pos2[1];
    $dz = $pos1[2] - $pos2[2];
    return sqrt($dx * $dx + $dy * $dy + $dz * $dz);
}

/**
 * Вычисляет разницу скоростей (км/день)
 */
function velocityDiff($vel1, $vel2) {
    $dvx = $vel1[0] - $vel2[0];
    $dvy = $vel1[1] - $vel2[1];
    $dvz = $vel1[2] - $vel2[2];
    return sqrt($dvx * $dvx + $dvy * $dvy + $dvz * $dvz);
}

/**
 * Swiss Ephemeris FFI Reader
 */
class SwissEphFFIReader {
    private FFI $ffi;
    private string $ephe_path;

    public function __construct(string $dll_path, string $ephe_path) {
        $this->ephe_path = $ephe_path;

        $header = '
        typedef double centisec;
        typedef long int32;
        typedef unsigned long uint32;

        void swe_set_ephe_path(char *path);
        int32 swe_calc(double tjd, int ipl, int32 iflag, double *xx, char *serr);
        void swe_close(void);
        char *swe_version(char *s);
        ';

        $this->ffi = FFI::cdef($header, $dll_path);
        $this->ffi->swe_set_ephe_path($ephe_path);
    }

    /**
     * Вычислить позицию тела в барицентрической системе
     * @param int $body Swiss Ephemeris ID (0-20)
     * @param float $jd Julian Day
     * @return array ['pos' => [x,y,z], 'vel' => [vx,vy,vz]] в км
     */
    public function compute(int $body, float $jd): array {
        // SEFLG_SWIEPH(2) + SEFLG_SPEED(256) + SEFLG_XYZ(4096) + SEFLG_BARYCTR(16384) = 20738
        $flags = 2 | 256 | 4096 | 16384;

        $xx = FFI::new("double[6]");
        $serr = FFI::new("char[256]");

        $ret = $this->ffi->swe_calc($jd, $body, $flags, $xx, $serr);

        if ($ret < 0) {
            $err = FFI::string($serr);
            throw new RuntimeException("Swiss Eph error: $err");
        }

        // Уже в барицентрической системе благодаря SEFLG_BARYCTR
        return [
            'pos' => [$xx[0] * AU_TO_KM, $xx[1] * AU_TO_KM, $xx[2] * AU_TO_KM],
            'vel' => [$xx[3] * AU_TO_KM, $xx[4] * AU_TO_KM, $xx[5] * AU_TO_KM]
        ];
    }

    public function __destruct() {
        $this->ffi->swe_close();
    }
}

// ============================================================================
// Test Configuration
// ============================================================================

$test_epochs = [
    'J2000.0' => 2451545.0,           // 1 Jan 2000 12:00 TT
    'J1900.0' => 2415020.0,           // 31 Dec 1899 12:00 TT
    'J2100.0' => 2488070.0,           // 1 Jan 2100 12:00 TT
    'Current' => 2460247.5,           // ~Oct 2023
];

// Mapping: NAIF ID => [Swiss ID, Name, JPL Body ID, EPM Body ID]
$test_bodies = [
    1 => [2, 'Mercury', 1, 1],
    2 => [3, 'Venus', 2, 2],
    4 => [4, 'Mars', 4, 4],
    5 => [5, 'Jupiter', 5, 5],
    6 => [6, 'Saturn', 6, 6],
    7 => [7, 'Uranus', 7, 7],
    8 => [8, 'Neptune', 8, 8],
    9 => [9, 'Pluto', 9, 9],
    10 => [0, 'Sun', 11, 10],        // Note: different IDs
    301 => [1, 'Moon', 10, 301],     // Note: different IDs
];

printHeader("EPHEMERIS ACCURACY COMPARISON TEST");

echo "Test Date: " . date('Y-m-d H:i:s') . "\n";
echo "Reference: JPL DE440 (sub-meter precision)\n";
echo "Comparison: EPM2021 vs Swiss Ephemeris\n\n";

echo "Test Epochs:\n";
foreach ($test_epochs as $name => $jd) {
    echo "  - $name: JD $jd\n";
}

echo "\nTest Bodies: " . count($test_bodies) . " major bodies\n";

// ============================================================================
// Initialize Ephemerides
// ============================================================================

printSection("Initializing Ephemerides");

$ephemerides = [];

// JPL DE440
$jpl_path = 'data/ephemerides/jpl/de440.eph';
if (file_exists($jpl_path)) {
    try {
        $ephemerides['JPL_DE440'] = new EphReader($jpl_path);
        echo "✅ " . color("JPL DE440", 'green') . " loaded: $jpl_path\n";
        echo "   Precision: " . color("sub-meter to meter", 'cyan') . "\n";
    } catch (Exception $e) {
        echo "❌ JPL DE440 failed: " . $e->getMessage() . "\n";
    }
} else {
    echo "⚠️  JPL DE440 not found: $jpl_path\n";
}

// EPM2021
$epm_path = 'data/ephemerides/epm/2021/epm2021.eph';
if (file_exists($epm_path)) {
    try {
        $ephemerides['EPM2021'] = new EphReader($epm_path);
        echo "✅ " . color("EPM2021", 'green') . " loaded: $epm_path\n";
        echo "   Precision: " . color("~100 meters", 'cyan') . "\n";
    } catch (Exception $e) {
        echo "❌ EPM2021 failed: " . $e->getMessage() . "\n";
    }
} else {
    echo "⚠️  EPM2021 not found: $epm_path\n";
}

// Swiss Ephemeris
$swiss_dll = 'vendor/swisseph/swedll64.dll';
$swiss_ephe = 'ephe';
if (file_exists($swiss_dll) && is_dir($swiss_ephe)) {
    try {
        $ephemerides['Swiss_Eph'] = new SwissEphFFIReader($swiss_dll, $swiss_ephe);
        echo "✅ " . color("Swiss Ephemeris", 'green') . " loaded\n";
        echo "   Precision: " . color("~1 km (based on JPL DE431)", 'cyan') . "\n";
    } catch (Exception $e) {
        echo "❌ Swiss Ephemeris failed: " . $e->getMessage() . "\n";
    }
} else {
    echo "⚠️  Swiss Ephemeris not found\n";
}

if (count($ephemerides) < 2) {
    die("\n❌ Need at least 2 ephemerides for comparison!\n");
}

// ============================================================================
// Run Accuracy Tests
// ============================================================================

$results = [];

foreach ($test_epochs as $epoch_name => $jd) {
    printSection("Epoch: $epoch_name (JD $jd)");

    foreach ($test_bodies as $naif_id => [$swiss_id, $name, $jpl_body, $epm_body]) {
        echo str_pad($name, 12) . " ";

        $body_results = ['epoch' => $epoch_name, 'jd' => $jd, 'body' => $name];

        // Get reference (JPL DE440)
        try {
            if (isset($ephemerides['JPL_DE440'])) {
                $ref = $ephemerides['JPL_DE440']->compute($naif_id, $jd);
                // Convert AU to km
                $ref['pos'] = array_map(fn($v) => $v * AU_TO_KM, $ref['pos']);
                $ref['vel'] = array_map(fn($v) => $v * AU_TO_KM, $ref['vel']);
                $body_results['reference'] = $ref;
                echo color("✓", 'green') . " ";
            } else {
                echo color("?", 'yellow') . " ";
                $ref = null;
            }
        } catch (Exception $e) {
            echo color("✗", 'red') . " ";
            $ref = null;
        }

        // EPM2021
        try {
            if (isset($ephemerides['EPM2021'])) {
                $epm = $ephemerides['EPM2021']->compute($epm_body, $jd);
                // Convert AU to km
                $epm['pos'] = array_map(fn($v) => $v * AU_TO_KM, $epm['pos']);
                $epm['vel'] = array_map(fn($v) => $v * AU_TO_KM, $epm['vel']);
                if ($ref) {
                    $pos_err = distance($ref['pos'], $epm['pos']);
                    $vel_err = velocityDiff($ref['vel'], $epm['vel']);
                    $body_results['epm'] = [
                        'pos_error_km' => $pos_err,
                        'vel_error_km_day' => $vel_err
                    ];

                    $color_pos = $pos_err < 100 ? 'green' : ($pos_err < 1000 ? 'yellow' : 'red');
                    echo "EPM:" . color(sprintf("%6.1f", $pos_err), $color_pos) . "km ";
                } else {
                    echo color("EPM:N/A", 'yellow') . " ";
                }
            }
        } catch (Exception $e) {
            echo color("EPM:ERR", 'red') . " ";
        }

        // Swiss Eph
        try {
            if (isset($ephemerides['Swiss_Eph'])) {
                $swiss = $ephemerides['Swiss_Eph']->compute($swiss_id, $jd);
                if ($ref) {
                    $pos_err = distance($ref['pos'], $swiss['pos']);
                    $vel_err = velocityDiff($ref['vel'], $swiss['vel']);
                    $body_results['swiss'] = [
                        'pos_error_km' => $pos_err,
                        'vel_error_km_day' => $vel_err
                    ];

                    $color_pos = $pos_err < 1000 ? 'green' : ($pos_err < 10000 ? 'yellow' : 'red');
                    echo "Swiss:" . color(sprintf("%7.1f", $pos_err), $color_pos) . "km";
                } else {
                    echo color("Swiss:N/A", 'yellow');
                }
            }
        } catch (Exception $e) {
            echo color("Swiss:ERR", 'red');
        }

        echo "\n";
        $results[] = $body_results;
    }
}

// ============================================================================
// Statistical Summary
// ============================================================================

printSection("Statistical Summary");

// Calculate statistics
$stats = [
    'epm' => ['pos' => [], 'vel' => []],
    'swiss' => ['pos' => [], 'vel' => []]
];

foreach ($results as $r) {
    if (isset($r['epm'])) {
        $stats['epm']['pos'][] = $r['epm']['pos_error_km'];
        $stats['epm']['vel'][] = $r['epm']['vel_error_km_day'];
    }
    if (isset($r['swiss'])) {
        $stats['swiss']['pos'][] = $r['swiss']['pos_error_km'];
        $stats['swiss']['vel'][] = $r['swiss']['vel_error_km_day'];
    }
}

function calcStats($values) {
    if (empty($values)) return null;
    sort($values);
    $count = count($values);
    return [
        'min' => min($values),
        'max' => max($values),
        'mean' => array_sum($values) / $count,
        'median' => $count % 2 ? $values[floor($count/2)] : ($values[$count/2-1] + $values[$count/2]) / 2,
        'p95' => $values[min($count-1, floor($count * 0.95))]
    ];
}

echo "┌────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐\n";
echo "│ Ephemeris      │   Min    │   Mean   │  Median  │   P95    │   Max    │\n";
echo "├────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤\n";

foreach (['epm' => 'EPM2021', 'swiss' => 'Swiss Eph'] as $key => $label) {
    $pos_stats = calcStats($stats[$key]['pos']);
    if ($pos_stats) {
        printf("│ %-14s │ %6.1f km │ %6.1f km │ %6.1f km │ %6.1f km │ %6.1f km │\n",
            $label,
            $pos_stats['min'],
            $pos_stats['mean'],
            $pos_stats['median'],
            $pos_stats['p95'],
            $pos_stats['max']
        );
    }
}

echo "└────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘\n";

// ============================================================================
// Precision Classification
// ============================================================================

printSection("Precision Classification (vs JPL DE440)");

echo "┌────────────────┬─────────────────┬──────────────────────┐\n";
echo "│ Ephemeris      │ Typical Error   │ Classification       │\n";
echo "├────────────────┼─────────────────┼──────────────────────┤\n";
echo "│ JPL DE440      │ < 1 m           │ " . color("★★★★★ Reference", 'green') . "    │\n";

$epm_stats = calcStats($stats['epm']['pos'] ?? []);
if ($epm_stats) {
    $epm_class = $epm_stats['mean'] < 100 ? "★★★★☆ Excellent" : ($epm_stats['mean'] < 1000 ? "★★★☆☆ Good" : "★★☆☆☆ Fair");
    $color = $epm_stats['mean'] < 100 ? 'green' : 'yellow';
    printf("│ EPM2021        │ %6.1f m        │ " . color("%-20s", $color) . " │\n",
        $epm_stats['mean'] * 1000, $epm_class);
}

$swiss_stats = calcStats($stats['swiss']['pos'] ?? []);
if ($swiss_stats) {
    $swiss_class = $swiss_stats['mean'] < 1000 ? "★★★★☆ Excellent" : ($swiss_stats['mean'] < 10000 ? "★★★☆☆ Good" : "★★☆☆☆ Fair");
    $color = $swiss_stats['mean'] < 1000 ? 'green' : 'yellow';
    printf("│ Swiss Eph      │ %6.1f m        │ " . color("%-20s", $color) . " │\n",
        $swiss_stats['mean'] * 1000, $swiss_class);
}

echo "└────────────────┴─────────────────┴──────────────────────┘\n";

// ============================================================================
// Recommendations
// ============================================================================

printSection("Recommendations");

echo "🎯 " . color("For Maximum Accuracy", 'bold') . " (< 1 meter):\n";
echo "   Use JPL DE440 for planetary positions\n\n";

echo "⚡ " . color("For Good Balance", 'bold') . " (< 100 meters):\n";
echo "   Use EPM2021 - enhanced lunar data, good overall precision\n\n";

echo "🔄 " . color("For Maximum Flexibility", 'bold') . " (< 1 km):\n";
echo "   Use Swiss Ephemeris - all coordinate systems, asteroids, nodes\n\n";

echo "📌 " . color("Unique Features", 'bold') . ":\n";
echo "   - Chiron, Pholus: " . color("Only in Swiss Ephemeris", 'cyan') . "\n";
echo "   - Lunar Nodes: " . color("Only in Swiss Ephemeris", 'cyan') . "\n";
echo "   - Black Moon Lilith: " . color("Only in Swiss Ephemeris", 'cyan') . "\n";
echo "   - Asteroids (Ceres, Pallas, etc): " . color("Only in Swiss Ephemeris", 'cyan') . "\n\n";

printHeader("TEST COMPLETE");

echo "Results saved to memory. Use this data to update documentation.\n\n";
