<?php
/**
 * Debug Binary .eph coordinate mismatch
 *
 * Compare coefficients from Binary vs SQLite at same interval
 * to identify where the data diverges
 */

require_once __DIR__ . '/vendor/autoload.php';

use Swisseph\Ephemeris\EphReader;
use Swisseph\Ephemeris\SqliteEphReader;

$binaryPath = 'data/ephemerides/epm/2021/epm2021.eph';
$sqlitePath = 'data/ephemerides/epm/2021/epm2021.db';

try {
    // Open both readers
    echo "Opening ephemeris files...\n";
    $binary = new EphReader($binaryPath);
    $sqlite = new SqliteEphReader($sqlitePath);

    // Test at J2000.0
    $jd = 2451545.0;
    $bodyId = 399; // Earth

    echo "\n=== Testing Earth (399) at JD {$jd} (J2000.0) ===\n\n";

    // Get metadata
    $binMeta = $binary->getMetadata();
    $sqlMeta = $sqlite->getStats();

    echo "Binary metadata:\n";
    print_r($binMeta);

    echo "\nSQLite metadata:\n";
    print_r($sqlMeta);

    // Compute positions
    echo "\n=== Position Comparison ===\n";
    $binResult = $binary->compute($bodyId, $jd, false);
    $sqlResult = $sqlite->compute($bodyId, $jd, false);

    printf("Binary X: %.6f AU\n", $binResult['pos'][0]);
    printf("SQLite X: %.6f AU\n", $sqlResult['pos'][0]);
    printf("Diff:     %.6f AU (%.1f%%)\n",
           $binResult['pos'][0] - $sqlResult['pos'][0],
           abs($binResult['pos'][0] - $sqlResult['pos'][0]) / abs($sqlResult['pos'][0]) * 100);

    // Now extract and compare the raw coefficients
    echo "\n=== Raw Coefficient Extraction ===\n";

    // For Binary: manually extract coefficients
    echo "\nExtracting Binary coefficients...\n";
    $binCoeffs = extractBinaryCoeffs($binaryPath, $bodyId, $jd, $binMeta);

    echo "\nExtracting SQLite coefficients...\n";
    $sqlCoeffs = extractSqliteCoeffs($sqlitePath, $bodyId, $jd);

    // Compare coefficients
    echo "\n=== Coefficient Comparison (X component) ===\n";
    $numCoeffs = min(count($binCoeffs['x']), count($sqlCoeffs['x']));

    printf("%-5s  %-15s  %-15s  %-15s\n", "Idx", "Binary", "SQLite", "Difference");
    echo str_repeat("-", 60) . "\n";

    for ($i = 0; $i < $numCoeffs; $i++) {
        $diff = $binCoeffs['x'][$i] - $sqlCoeffs['x'][$i];
        printf("%-5d  %15.8e  %15.8e  %15.8e\n",
               $i, $binCoeffs['x'][$i], $sqlCoeffs['x'][$i], $diff);
    }

    // Check if coefficients are identical
    $maxDiff = 0.0;
    for ($i = 0; $i < $numCoeffs; $i++) {
        $maxDiff = max($maxDiff, abs($binCoeffs['x'][$i] - $sqlCoeffs['x'][$i]));
    }

    echo "\n=== Analysis ===\n";
    printf("Max coefficient difference: %.2e\n", $maxDiff);

    if ($maxDiff < 1e-10) {
        echo "✅ Coefficients are IDENTICAL - bug is in PHP evaluation!\n";
    } else {
        echo "❌ Coefficients are DIFFERENT - bug is in Python conversion!\n";
    }

    // Test Chebyshev evaluation with same coefficients
    echo "\n=== Testing Chebyshev Evaluation ===\n";

    // Get normalized time for J2000.0
    $interval = findBinaryInterval($binaryPath, $jd, $binMeta);
    $t_norm = 2.0 * ($jd - $interval['start']) / ($interval['end'] - $interval['start']) - 1.0;

    printf("Interval: JD %.2f - %.2f\n", $interval['start'], $interval['end']);
    printf("Normalized time: %.6f\n", $t_norm);

    // Evaluate using both sets of coefficients
    $evalBinary = evaluateChebyshev($binCoeffs['x'], $t_norm);
    $evalSqlite = evaluateChebyshev($sqlCoeffs['x'], $t_norm);

    printf("Eval with Binary coeffs: %.6f AU\n", $evalBinary);
    printf("Eval with SQLite coeffs: %.6f AU\n", $evalSqlite);
    printf("Expected Binary result:  %.6f AU\n", $binResult['pos'][0]);
    printf("Expected SQLite result:  %.6f AU\n", $sqlResult['pos'][0]);

} catch (Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
    echo $e->getTraceAsString() . "\n";
}

/**
 * Extract coefficients from Binary .eph file
 */
function extractBinaryCoeffs(string $filepath, int $bodyId, float $jd, array $meta): array
{
    $fp = fopen($filepath, 'rb');

    // Find interval
    $intervalIdx = findIntervalIdx($fp, $jd, $meta);

    // Read body table to get offset
    $headerSize = 512;
    $bodyEntrySize = 36;

    fseek($fp, $headerSize);
    $bodies = [];

    for ($i = 0; $i < $meta['numBodies']; $i++) {
        $data = fread($fp, $bodyEntrySize);
        $entry = unpack('lbodyId/a24name/QdataOffset', $data);
        $bodies[$entry['bodyId']] = $entry['dataOffset'];
    }

    if (!isset($bodies[$bodyId])) {
        throw new Exception("Body {$bodyId} not found in binary file");
    }

    // Calculate offset for this body/interval
    $numCoeffs = $meta['coeffDegree'] + 1;
    $coeffsPerInterval = $numCoeffs * 3; // x, y, z
    $bytesPerInterval = $coeffsPerInterval * 8;

    $offset = $bodies[$bodyId] + $intervalIdx * $bytesPerInterval;
    fseek($fp, $offset);


    // Read coefficients
    $data = fread($fp, $coeffsPerInterval * 8);
    $coeffs = unpack("d{$coeffsPerInterval}", $data);

    // unpack() returns 1-indexed array, convert to 0-indexed
    $coeffs = array_values($coeffs);

    fclose($fp);

    return [
        'x' => array_slice($coeffs, 0, $numCoeffs),
        'y' => array_slice($coeffs, $numCoeffs, $numCoeffs),
        'z' => array_slice($coeffs, 2 * $numCoeffs, $numCoeffs)
    ];
}/**
 * Extract coefficients from SQLite .db file
 */
function extractSqliteCoeffs(string $filepath, int $bodyId, float $jd): array
{
    $db = new PDO("sqlite:{$filepath}");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->prepare('
        SELECT coeffs_x, coeffs_y, coeffs_z
        FROM intervals
        WHERE body_id = ? AND jd_start <= ? AND jd_end >= ?
        LIMIT 1
    ');

    $stmt->execute([$bodyId, $jd, $jd]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$row) {
        throw new Exception("No interval found for JD {$jd}");
    }

    // Decompress and unpack
    $coeffs_x = unpack('d*', gzuncompress($row['coeffs_x']));
    $coeffs_y = unpack('d*', gzuncompress($row['coeffs_y']));
    $coeffs_z = unpack('d*', gzuncompress($row['coeffs_z']));

    return [
        'x' => array_values($coeffs_x),
        'y' => array_values($coeffs_y),
        'z' => array_values($coeffs_z)
    ];
}

/**
 * Find interval index for JD
 */
function findIntervalIdx($fp, float $jd, array $meta): int
{
    $headerSize = 512;
    $bodyTableSize = $meta['numBodies'] * 36;
    $intervalIndexOffset = $headerSize + $bodyTableSize;

    fseek($fp, $intervalIndexOffset);

    for ($i = 0; $i < $meta['numIntervals']; $i++) {
        $data = fread($fp, 16);
        $interval = unpack('djdStart/djdEnd', $data);

        if ($jd >= $interval['jdStart'] && $jd <= $interval['jdEnd']) {
            return $i;
        }
    }

    throw new Exception("JD {$jd} not found in intervals");
}

/**
 * Find interval bounds
 */
function findBinaryInterval(string $filepath, float $jd, array $meta): array
{
    $fp = fopen($filepath, 'rb');

    $headerSize = 512;
    $bodyTableSize = $meta['numBodies'] * 36;
    $intervalIndexOffset = $headerSize + $bodyTableSize;

    fseek($fp, $intervalIndexOffset);

    for ($i = 0; $i < $meta['numIntervals']; $i++) {
        $data = fread($fp, 16);
        $interval = unpack('djdStart/djdEnd', $data);

        if ($jd >= $interval['jdStart'] && $jd <= $interval['jdEnd']) {
            fclose($fp);
            return ['start' => $interval['jdStart'], 'end' => $interval['jdEnd']];
        }
    }

    fclose($fp);
    throw new Exception("JD {$jd} not found");
}

/**
 * Evaluate Chebyshev polynomial (Clenshaw's algorithm)
 */
function evaluateChebyshev(array $coeffs, float $x): float
{
    $n = count($coeffs);
    if ($n === 0) return 0.0;
    if ($n === 1) return $coeffs[0];

    $b_k1 = 0.0;
    $b_k2 = 0.0;

    for ($k = $n - 1; $k >= 1; $k--) {
        $b_k = 2.0 * $x * $b_k1 - $b_k2 + $coeffs[$k];
        $b_k2 = $b_k1;
        $b_k1 = $b_k;
    }

    return $x * $b_k1 - $b_k2 + $coeffs[0];
}
