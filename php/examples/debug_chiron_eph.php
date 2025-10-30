<?php

/**
 * Debug Chiron .eph file structure
 */

$file = __DIR__ . '/../../data/chiron/chiron_jpl.eph';

if (!file_exists($file)) {
    die("File not found: $file\n");
}

$fp = fopen($file, 'rb');

// Read header (512 bytes)
$data = fread($fp, 512);
$header = unpack(
    'a4magic/Vversion/VnumBodies/VnumIntervals/' .
    'dintervalDays/dstartJD/dendJD/VcoeffDegree',
    $data
);

echo "HEADER:\n";
print_r($header);
echo "\n";

// Read body table
echo "BODY TABLE:\n";
fseek($fp, 512);
for ($i = 0; $i < $header['numBodies']; $i++) {
    $data = fread($fp, 36);

    // Try different formats for dataOffset
    $entry_Q = unpack('lbodyId/a24name/QdataOffset', $data);
    $entry_P = unpack('lbodyId/a24name/PdataOffset', $data);

    echo "Body $i:\n";
    echo "  ID: {$entry_Q['bodyId']}, name: {$entry_Q['name']}\n";
    echo "  Offset (Q): {$entry_Q['dataOffset']}\n";
    echo "  Offset (P): {$entry_P['dataOffset']}\n";

    // Show last 8 bytes hex
    $last8 = substr($data, 28, 8);
    echo "  Last 8 bytes hex: " . bin2hex($last8) . "\n";
}
echo "\n";

// Calculate intervals offset
$bodyEntrySize = 36;
$intervalsOffset = 512 + $header['numBodies'] * $bodyEntrySize;
echo "Intervals offset: $intervalsOffset (0x" . dechex($intervalsOffset) . ")\n";
echo "Current position: " . ftell($fp) . "\n\n";
fseek($fp, $intervalsOffset);

// Read first 3 intervals
echo "FIRST 3 INTERVALS:\n";
for ($i = 0; $i < min(3, $header['numIntervals']); $i++) {
    $pos = ftell($fp);
    $data = fread($fp, 16);

    // Try different unpack formats
    $interval_d = unpack('dstart/dend', $data);
    $interval_e = unpack('estart/eend', $data);

    echo "Interval $i (offset $pos):\n";
    echo "  'd' (machine): start={$interval_d['start']}, end={$interval_d['end']}\n";
    echo "  'e' (LE):      start={$interval_e['start']}, end={$interval_e['end']}\n";

    // Also show raw hex
    $hex = bin2hex($data);
    echo "  Raw hex: $hex\n";
}

fclose($fp);
