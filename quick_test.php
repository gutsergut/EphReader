<?php
require 'vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\SqliteEphReader;

$binary = new EphReader('data/ephemerides/epm/2021/epm2021.eph');
$sqlite = new SqliteEphReader('data/ephemerides/epm/2021/epm2021.db');

$jd = 2451545.0; // J2000.0
$bodyId = 399;   // Earth

$binResult = $binary->compute($bodyId, $jd, false);
$sqlResult = $sqlite->compute($bodyId, $jd, false);

printf("Binary:  X=%.6f AU\n", $binResult['pos'][0]);
printf("SQLite:  X=%.6f AU\n", $sqlResult['pos'][0]);
printf("Match:   %s\n", abs($binResult['pos'][0] - $sqlResult['pos'][0]) < 1e-10 ? '✅ YES' : '❌ NO');
