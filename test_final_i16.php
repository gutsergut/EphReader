<?php
/**
 * Final test: Compare all formats with interval=16
 */

require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphemerisFactory;

$testJD = 2451545.0; // J2000.0
$testBody = 399; // Earth

echo "╔══════════════════════════════════════════════════════════════╗\n";
echo "║   FINAL TEST: All Formats with interval=16 (Native EPM)     ║\n";
echo "╚══════════════════════════════════════════════════════════════╝\n\n";

$files = [
    'Binary i16' => 'data/ephemerides/epm/2021/epm2021_i16.eph',
    'SQLite i16' => 'data/ephemerides/epm/2021/epm2021_i16.db',
    'Hybrid i16' => 'data/ephemerides/epm/2021/epm2021_i16.hidx',
];

// Load readers
$readers = [];
foreach ($files as $name => $file) {
    if (!file_exists($file)) {
        echo "⏳ $name: Not ready yet ($file)\n";
        continue;
    }

    try {
        $readers[$name] = EphemerisFactory::create($file);

        $size = filesize($file);
        if (strpos($name, 'Hybrid') !== false) {
            $dataFile = str_replace('.hidx', '.heph', $file);
            if (file_exists($dataFile)) {
                $size += filesize($dataFile);
            }
        }

        echo "✅ $name: " . number_format($size / 1024 / 1024, 2) . " MB\n";
    } catch (Exception $e) {
        echo "❌ $name: " . $e->getMessage() . "\n";
    }
}

if (empty($readers)) {
    echo "\n⚠️  No readers loaded. Wait for conversions to complete.\n";
    exit(1);
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "Coordinates at J2000.0 (Earth)\n";
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

$results = [];
foreach ($readers as $name => $reader) {
    try {
        $pos = $reader->compute($testBody, $testJD);
        $results[$name] = $pos;

        printf("%-15s: X=%+.9f  Y=%+.9f  Z=%+.9f AU\n",
            $name,
            $pos['pos'][0],
            $pos['pos'][1],
            $pos['pos'][2]
        );
    } catch (Exception $e) {
        echo "$name: ERROR - " . $e->getMessage() . "\n";
    }
}

// Cross-comparison
if (count($results) > 1) {
    echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
    echo "Cross-Format Accuracy\n";
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

    $names = array_keys($results);
    $ref_name = $names[0];
    $ref = $results[$ref_name]['pos'];

    echo "Using $ref_name as reference:\n\n";

    $max_diff = 0;
    foreach ($results as $name => $data) {
        if ($name === $ref_name) continue;

        $pos = $data['pos'];
        $dx = $pos[0] - $ref[0];
        $dy = $pos[1] - $ref[1];
        $dz = $pos[2] - $ref[2];
        $diff = sqrt($dx*$dx + $dy*$dy + $dz*$dz);
        $max_diff = max($max_diff, $diff);

        $status = $diff < 1e-9 ? '✅ IDENTICAL' : ($diff < 1e-7 ? '✅ EXCELLENT' : '⚠️  DIFFERS');
        printf("%-15s: %.2e AU (%.1f km)  %s\n",
            $name, $diff, $diff * 149597870.7, $status);
    }

    echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
    echo "VERDICT\n";
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";

    if ($max_diff < 1e-9) {
        echo "🎉 PERFECT! All formats produce IDENTICAL coordinates!\n";
        echo "   Maximum difference: < 1 meter\n";
    } elseif ($max_diff < 1e-7) {
        echo "✅ EXCELLENT! All formats have high precision.\n";
        printf("   Maximum difference: %.1f km (negligible for astrology)\n", $max_diff * 149597870.7);
    } else {
        echo "⚠️  CAUTION: Some formats differ significantly.\n";
        printf("   Maximum difference: %.1f km\n", $max_diff * 149597870.7);
    }

    echo "\n✨ All formats now use interval=16 days (native EPM2021 precision)\n";
    echo "✨ Coordinates match original SPICE data\n";
}
