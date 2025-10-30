<?php
require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;

$files = [
    'de200.eph' => 'data/ephemerides/jpl/de200.eph',
    'de406e.eph' => 'data/ephemerides/jpl/de406e.eph',
    'de431.eph' => 'data/ephemerides/jpl/de431.eph',
    'de441.eph' => 'data/ephemerides/jpl/de441.eph'
];

foreach ($files as $name => $path) {
    echo "\n========== $name ==========\n";

    if (!file_exists($path)) {
        echo "❌ File not found\n";
        continue;
    }

    try {
        $eph = new EphReader($path);
        $meta = $eph->getMetadata();

        echo "✅ Valid Binary .eph format\n";
        echo "Time range: JD {$meta['start_jd']} - {$meta['end_jd']}\n";
        echo "Interval: {$meta['interval_days']} days\n";
        echo "Bodies: " . count($eph->getBodies()) . "\n";
        echo "Bodies: " . implode(', ', array_column($eph->getBodies(), 'name')) . "\n";

        // Test computation
        $result = $eph->compute(399, 2451545.0); // Earth at J2000.0
        echo "Earth@J2000: X={$result['pos'][0]} AU\n";

    } catch (Exception $e) {
        echo "❌ Error: " . $e->getMessage() . "\n";
    }
}
