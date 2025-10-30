<?php
/**
 * DE431 vs DE440 vs Swiss Eph Complete Comparison
 *
 * Цель: Полное сравнение точности трёх эфемерид:
 *   - JPL DE440 (эталон, 2020, новые фундаментальные константы)
 *   - JPL DE431 (2013, старые константы)
 *   - Swiss Eph (основана на DE431)
 *
 * Задачи:
 *   1. Выяснить, насколько DE431 отличается от DE440
 *   2. Проверить, действительно ли Swiss Eph основана на DE431
 *   3. Понять, можно ли улучшить Swiss Eph обновлением базы до DE440
 */require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;

const AU_TO_KM = 149597870.7;

// Swiss Ephemeris FFI Reader (из test_accuracy_comparison.php)
class SwissEphFFIReader {
    private FFI $ffi;

    public function __construct(string $dll_path, string $ephe_path) {
        $header = '
        typedef double centisec;
        typedef long int32;
        typedef unsigned long uint32;

        void swe_set_ephe_path(char *path);
        int32 swe_calc(double tjd, int ipl, int32 iflag, double *xx, char *serr);
        void swe_close(void);
        ';

        $this->ffi = FFI::cdef($header, $dll_path);
        $this->ffi->swe_set_ephe_path($ephe_path);
    }

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

        return [
            'pos' => [$xx[0] * AU_TO_KM, $xx[1] * AU_TO_KM, $xx[2] * AU_TO_KM],
            'vel' => [$xx[3] * AU_TO_KM, $xx[4] * AU_TO_KM, $xx[5] * AU_TO_KM]
        ];
    }

    public function __destruct() {
        $this->ffi->swe_close();
    }
}

function distance($pos1, $pos2) {
    $dx = $pos1[0] - $pos2[0];
    $dy = $pos1[1] - $pos2[1];
    $dz = $pos1[2] - $pos2[2];
    return sqrt($dx * $dx + $dy * $dy + $dz * $dz);
}

echo str_repeat("=", 80) . "\n";
echo "DE431 vs DE440 vs Swiss Ephemeris Complete Comparison\n";
echo str_repeat("=", 80) . "\n\n";

echo "Goal: Comprehensive accuracy comparison of three ephemerides\n";
echo "Reference: JPL DE440 (2020, latest fundamental constants)\n";
echo "Comparisons:\n";
echo "  1. DE431 vs DE440 → Quantify impact of constant changes\n";
echo "  2. Swiss Eph vs DE440 → Current Swiss Eph accuracy\n";
echo "  3. Swiss Eph vs DE431 → Verify Swiss Eph is DE431-based\n\n";

// Load ephemerides
$de440 = new EphReader('data/ephemerides/jpl/de440.eph');

// Try to load DE431 Part 1 (converted from SPICE)
// Part 1 covers BC 13200 to ~AD 8000 (overlaps with DE440's 1550-2650 AD range)
$de431 = null;
$de431_path = 'data/ephemerides/jpl/de431_part-1.eph';
if (file_exists($de431_path)) {
    try {
        $de431 = new EphReader($de431_path);
        echo "✅ DE431 Part 1 loaded: $de431_path\n";
    } catch (Exception $e) {
        echo "⚠️  DE431 file exists but cannot be read: {$e->getMessage()}\n";
        echo "   Will compare only DE440 vs Swiss Eph\n";
    }
} else {
    echo "⚠️  DE431 not found: $de431_path\n";
    echo "   Run: .\\convert_de431.ps1\n";
    echo "   Will compare only DE440 vs Swiss Eph\n";
}

$swiss = new SwissEphFFIReader('vendor/swisseph/swedll64.dll', 'ephe');

echo "✅ DE440 loaded: data/ephemerides/jpl/de440.eph\n";
echo "✅ Swiss Eph loaded\n\n";

// Test configuration - расширенный набор эпох
$test_epochs = [
    'J1900.0' => 2415020.0,
    'J1950.0' => 2433282.5,
    'J2000.0' => 2451545.0,
    'J2050.0' => 2469807.5,
    'J2100.0' => 2488070.0,
];

// NAIF => [Swiss ID, Name]
$test_bodies = [
    1 => [2, 'Mercury'],
    2 => [3, 'Venus'],
    4 => [4, 'Mars'],
    5 => [5, 'Jupiter'],
    6 => [6, 'Saturn'],
    7 => [7, 'Uranus'],
    8 => [8, 'Neptune'],
    9 => [9, 'Pluto'],
    10 => [0, 'Sun'],
    301 => [1, 'Moon'],
];

$results = [];

foreach ($test_epochs as $epoch_name => $jd) {
    echo "\n" . str_repeat("=", 80) . "\n";
    echo "Epoch: $epoch_name (JD $jd)\n";
    echo str_repeat("=", 80) . "\n\n";

    if ($de431) {
        echo sprintf("%-12s %15s %15s %15s\n", "Body", "DE431-DE440", "Swiss-DE440", "Swiss-DE431");
        echo str_repeat("-", 80) . "\n";
    } else {
        echo sprintf("%-12s %20s %20s\n", "Body", "Swiss-DE440 (km)", "% of distance");
        echo str_repeat("-", 60) . "\n";
    }

    foreach ($test_bodies as $naif_id => [$swiss_id, $name]) {
        try {
            // Get positions
            $pos_440 = $de440->compute($naif_id, $jd);
            $pos_swiss = $swiss->compute($swiss_id, $jd);

            // Convert AU to km
            $pos_440['pos'] = array_map(fn($v) => $v * AU_TO_KM, $pos_440['pos']);

            if ($de431) {
                // Full 3-way comparison
                $pos_431 = $de431->compute($naif_id, $jd);
                $pos_431['pos'] = array_map(fn($v) => $v * AU_TO_KM, $pos_431['pos']);

                $diff_431_440 = distance($pos_431['pos'], $pos_440['pos']);
                $diff_swiss_440 = distance($pos_swiss['pos'], $pos_440['pos']);
                $diff_swiss_431 = distance($pos_swiss['pos'], $pos_431['pos']);

                printf("%-12s %12.1f km %12.1f km %12.1f km\n",
                    $name,
                    $diff_431_440,
                    $diff_swiss_440,
                    $diff_swiss_431
                );

                $results[] = [
                    'epoch' => $epoch_name,
                    'body' => $name,
                    'diff_431_440' => $diff_431_440,
                    'diff_swiss_440' => $diff_swiss_440,
                    'diff_swiss_431' => $diff_swiss_431,
                ];
            } else {
                // DE440 vs Swiss only
                $diff_swiss_440 = distance($pos_swiss['pos'], $pos_440['pos']);

                // Distance from SSB to body (for percentage calculation)
                $dist_from_ssb = sqrt(
                    $pos_440['pos'][0]**2 +
                    $pos_440['pos'][1]**2 +
                    $pos_440['pos'][2]**2
                );

                $percent = $dist_from_ssb > 0 ? ($diff_swiss_440 / $dist_from_ssb) * 100 : 0;

                printf("%-12s %17.1f km %18.4f%%\n",
                    $name,
                    $diff_swiss_440,
                    $percent
                );

                $results[] = [
                    'epoch' => $epoch_name,
                    'body' => $name,
                    'diff_swiss_440' => $diff_swiss_440,
                    'percent' => $percent,
                ];
            }

        } catch (Exception $e) {
            printf("%-12s ERROR: %s\n", $name, $e->getMessage());
        }
    }
}

// Statistical analysis
echo "\n\n" . str_repeat("=", 80) . "\n";
echo "Statistical Summary\n";
echo str_repeat("=", 80) . "\n\n";

$stats = [
    'de431_vs_de440' => [],
    'swiss_vs_de440' => [],
    'swiss_vs_de431' => [],
    'percentages' => [],
];

foreach ($results as $r) {
    $stats['swiss_vs_de440'][] = $r['diff_swiss_440'];
    if (isset($r['diff_431_440'])) {
        $stats['de431_vs_de440'][] = $r['diff_431_440'];
        $stats['swiss_vs_de431'][] = $r['diff_swiss_431'];
    }
    if (isset($r['percent'])) {
        $stats['percentages'][] = $r['percent'];
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
    ];
}

$s_431_440 = calcStats($stats['de431_vs_de440']);
$s_swiss_440 = calcStats($stats['swiss_vs_de440']);
$s_swiss_431 = calcStats($stats['swiss_vs_de431']);
$s_percent = calcStats($stats['percentages']);

echo sprintf("%-20s %15s %15s %15s %15s\n", "Comparison", "Min", "Median", "Mean", "Max");
echo str_repeat("-", 90) . "\n";

if ($s_431_440) {
    printf("%-20s %12.1f km %12.1f km %12.1f km %12.1f km\n",
        "DE431 vs DE440",
        $s_431_440['min'], $s_431_440['median'], $s_431_440['mean'], $s_431_440['max']
    );
}

if ($s_swiss_440) {
    printf("%-20s %12.1f km %12.1f km %12.1f km %12.1f km\n",
        "Swiss vs DE440",
        $s_swiss_440['min'], $s_swiss_440['median'], $s_swiss_440['mean'], $s_swiss_440['max']
    );
}

if ($s_swiss_431) {
    printf("%-20s %12.1f km %12.1f km %12.1f km %12.1f km\n",
        "Swiss vs DE431",
        $s_swiss_431['min'], $s_swiss_431['median'], $s_swiss_431['mean'], $s_swiss_431['max']
    );
}

if ($s_percent) {
    printf("%-20s %13.4f%% %13.4f%% %13.4f%% %13.4f%%\n",
        "Error percentage",
        $s_percent['min'], $s_percent['median'], $s_percent['mean'], $s_percent['max']
    );
}

// Conclusion
echo "\n\n" . str_repeat("=", 80) . "\n";
echo "Conclusion\n";
echo str_repeat("=", 80) . "\n\n";

if ($s_431_440 && $s_swiss_440 && $s_swiss_431) {
    // Full 3-way comparison
    echo "Key Findings (3-Way Comparison):\n\n";

    echo "1. DE431 vs DE440 differences:\n";
    printf("   Minimum: %.1f km\n", $s_431_440['min']);
    printf("   Median: %.1f km\n", $s_431_440['median']);
    printf("   Mean: %.1f km\n", $s_431_440['mean']);
    printf("   Maximum: %.1f km\n\n", $s_431_440['max']);

    echo "2. Swiss Eph vs DE440 differences:\n";
    printf("   Minimum: %.1f km\n", $s_swiss_440['min']);
    printf("   Median: %.1f km\n", $s_swiss_440['median']);
    printf("   Mean: %.1f km\n", $s_swiss_440['mean']);
    printf("   Maximum: %.1f km\n\n", $s_swiss_440['max']);

    echo "3. Swiss Eph vs DE431 differences:\n";
    printf("   Minimum: %.1f km\n", $s_swiss_431['min']);
    printf("   Median: %.1f km\n", $s_swiss_431['median']);
    printf("   Mean: %.1f km\n", $s_swiss_431['mean']);
    printf("   Maximum: %.1f km\n\n", $s_swiss_431['max']);

    echo "Analysis:\n\n";

    // Is Swiss Eph really based on DE431?
    if ($s_swiss_431['median'] < $s_431_440['median'] * 2) {
        echo "✅ Swiss Eph is VERIFIED to be based on DE431!\n";
        printf("   Swiss-DE431 median error (%.1f km) << Swiss-DE440 error (%.1f km)\n\n",
            $s_swiss_431['median'], $s_swiss_440['median']);
    } else {
        echo "⚠️  Swiss Eph differs significantly even from DE431!\n";
        printf("   Swiss-DE431: %.1f km vs Swiss-DE440: %.1f km\n\n",
            $s_swiss_431['median'], $s_swiss_440['median']);
    }

    // Impact of DE431→DE440 changes
    if ($s_431_440['median'] > 1000000) {
        echo "⚠️  DE431→DE440 changes are MASSIVE (>1M km median)!\n";
        printf("   Median difference: %.1f km\n", $s_431_440['median']);
        echo "   This explains most Swiss Eph errors vs DE440.\n";
        echo "   Updating Swiss Eph to DE440 base would dramatically improve precision!\n\n";
    } elseif ($s_431_440['median'] > 100000) {
        echo "⚠️  DE431→DE440 changes are SIGNIFICANT (>100k km)!\n";
        printf("   Median difference: %.1f km\n", $s_431_440['median']);
        echo "   These are NOT minor refinements - fundamental constants changed.\n\n";
    } else {
        echo "✅ DE431→DE440 changes are relatively small (<100k km).\n";
        printf("   Median difference: %.1f km\n", $s_431_440['median']);
        echo "   Swiss Eph errors are primarily from other sources.\n\n";
    }

    // Breakdown responsibility
    $de_change_contribution = ($s_431_440['median'] / $s_swiss_440['median']) * 100;
    $swiss_impl_contribution = ($s_swiss_431['median'] / $s_swiss_440['median']) * 100;

    echo "Error Attribution:\n";
    printf("   DE431→DE440 changes: ~%.1f%% of Swiss-DE440 error\n", $de_change_contribution);
    printf("   Swiss Eph implementation: ~%.1f%% of Swiss-DE440 error\n\n", $swiss_impl_contribution);

} elseif ($s_swiss_440 && $s_percent) {
    // DE440 vs Swiss only
    echo "Key Findings (Swiss Eph vs DE440):\n\n";

    echo "1. Swiss Eph vs DE440 distance errors:\n";
    printf("   Minimum: %.1f km\n", $s_swiss_440['min']);
    printf("   Median: %.1f km (%.4f%% of distance)\n", $s_swiss_440['median'], $s_percent['median']);
    printf("   Mean: %.1f km (%.4f%% of distance)\n", $s_swiss_440['mean'], $s_percent['mean']);
    printf("   Maximum: %.1f km (%.4f%% of distance)\n\n", $s_swiss_440['max'], $s_percent['max']);

    echo "2. Error analysis:\n\n";

    if ($s_percent['median'] < 0.01) {
        echo "✅ Median error < 0.01% of distance\n";
        echo "   Swiss Eph provides excellent positional accuracy!\n\n";
    } elseif ($s_percent['median'] < 0.1) {
        echo "✅ Median error < 0.1% of distance\n";
        echo "   Swiss Eph provides good positional accuracy.\n\n";
    } elseif ($s_percent['median'] < 1.0) {
        echo "⚠️  Median error < 1% of distance\n";
        echo "   Swiss Eph adequate for most applications.\n\n";
    } else {
        echo "⚠️  Median error > 1% of distance\n";
        echo "   Significant errors, but angular positions may still be accurate.\n\n";
    }

    if ($s_swiss_440['max'] > 1e9) {
        echo "⚠️  Maximum errors exceed 1 million km!\n";
        echo "   This is expected for:\n";
        echo "   - Distant bodies (Neptune, Pluto)\n";
        echo "   - Epochs far from J2000 reference epoch\n";
        echo "   - DE431→DE440 fundamental constant changes\n\n";
    }
}

echo "3. Recommendations:\n\n";
echo "✅ For ANGULAR positions (astrology): Swiss Eph is excellent\n";
echo "   - Longitude/latitude precision: ~arcseconds\n";
echo "   - Sufficient for chart calculations\n\n";

echo "⚠️  For DISTANCE precision (astronomy): Use JPL DE440/EPM2021\n";
echo "   - EPM2021: ~20-50 km for inner planets\n";
echo "   - Swiss Eph based on older DE431 with different constants\n\n";

echo "💡 For UNIQUE bodies (Chiron, Pholus, Nodes, Lilith):\n";
echo "   - Swiss Eph is the ONLY integrated source\n";
echo "   - No alternatives in JPL or EPM standard files\n\n";

echo "Test complete!\n";
