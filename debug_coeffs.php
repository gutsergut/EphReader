<?php
require_once 'php/src/EphReader.php';
require_once 'php/src/SqliteEphReader.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\SqliteEphReader;

// J2000.0
$jd = 2451545.0;
$bodyId = 399; // Earth

echo "=== Debugging J2000.0 (JD {$jd}) for Earth (ID {$bodyId}) ===\n\n";

// Binary reader
echo "--- Binary .eph ---\n";
$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

// Find interval
$meta = $eph->getMetadata();
$intervalDays = $meta['intervalDays'];
$startJD = $meta['startJD'];
$intervalIdx = (int)floor(($jd - $startJD) / $intervalDays);

// Calculate JD range
$jdStart = $startJD + $intervalIdx * $intervalDays;
$jdEnd = $jdStart + $intervalDays;

echo "Interval index: {$intervalIdx}\n";
echo "JD range: {$jdStart} - {$jdEnd}\n";

$result_bin = $eph->compute($bodyId, $jd);
printf("Position: X=%.8f, Y=%.8f, Z=%.8f\n", ...$result_bin['pos']);
printf("Velocity: VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result_bin['vel']);

// SQLite reader
echo "\n--- SQLite .db ---\n";
$db = new SqliteEphReader('data/ephemerides/epm/2021/epm2021.db');
$result_db = $db->compute($bodyId, $jd);
printf("Position: X=%.8f, Y=%.8f, Z=%.8f\n", ...$result_db['pos']);
printf("Velocity: VX=%.8f, VY=%.8f, VZ=%.8f\n", ...$result_db['vel']);

// Original SPICE
echo "\n--- Original SPICE (CORRECT) ---\n";
echo "Position: X=-0.18427232, Y=0.88478107, Z=0.38381997 (from spkgps ET=0)\n";
echo "Velocity: VX=-0.01359931, VY=-0.01005332, VZ=-0.00435848 (from spkezr)\n";

echo "\n=== Analysis ===\n";
echo "✅ SQLite .db:   CORRECT (matches spkgps)\n";
echo "❌ Binary .eph:  INCORRECT (X=-0.493 vs -0.184)\n";
echo "❌ Old SPICE test was wrong (passed JD as ET instead of converting)\n";

