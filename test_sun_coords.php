<?php
require_once 'php/src/EphReader.php';
require_once 'php/src/SqliteEphReader.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\SqliteEphReader;

$jd = 2451545.0; // J2000.0

echo "=== Testing Sun (ID 10) at J2000.0 ===\n\n";

// Binary .eph
$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');
$sun_bin = $eph->compute(10, $jd);
echo "Binary .eph:\n";
printf("  Position: X=%.8f, Y=%.8f, Z=%.8f AU\n", ...$sun_bin['pos']);

// SQLite .db
$db = new SqliteEphReader('data/ephemerides/epm/2021/epm2021.db');
$sun_db = $db->compute(10, $jd);
echo "\nSQLite .db:\n";
printf("  Position: X=%.8f, Y=%.8f, Z=%.8f AU\n", ...$sun_db['pos']);

echo "\nExpected (from test_sun.py): X=-0.007 AU (close to SSB)\n";

if (abs($sun_db['pos'][0]) < 0.01) {
    echo "✅ SQLite Sun position looks correct (close to zero)\n";
} else {
    echo "❌ SQLite Sun position seems wrong\n";
}

if (abs($sun_bin['pos'][0]) < 0.01) {
    echo "✅ Binary Sun position looks correct (close to zero)\n";
} else {
    echo "❌ Binary Sun position seems wrong\n";
}
